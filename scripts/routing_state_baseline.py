"""CI / replay baseline: parse spec artifacts the same way Phase 11 collectors did.

Analyzer (LLM) follows routing_conditions.yaml. This module is the etalon for
--golden and routing_state_parity --replay. Live spec overlay uses
`deferred_gap_ids` so «Отложено» rows do not re-queue resolve-gaps.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

INLINE_GAP_RE = re.compile(r"\[GAP-[A-Z0-9-]+\]")
TABLE_GAP_RE = re.compile(r"^\|\s*(GAP-[A-Z0-9-]+)\s*\|", re.MULTILINE)
DECISION_ROW_RE = re.compile(
    r"^\|\s*D-\d+\s*\|([^|\n]*)\|(?:[^|\n]*\|){3}\s*([^|]+)\|",
    re.MULTILINE,
)
ALIGNMENT_RELATES_RE = re.compile(r"\b[FICTKAM]-\d+\b")
CLOSED_GAP_MARKERS = ("закрыт", "closed", "отложено", "deferred")
QUESTION_ID_RE = re.compile(r"\bQ-\d+\b")
CHALLENGE_ROW_RE = re.compile(
    r"^\|\s*(CH-\d+)\s*\|(?:[^|\n]*\|){3}\s*([^|]+)\|\s*([^|]+)\|",
    re.MULTILINE,
)
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
MISMATCH_ROW_RE = re.compile(r"^\|((?:[^|\n]*\|)+)\s*$", re.MULTILINE)
SUMMARY_ROW_RE = re.compile(r"\b(?:critical|major|minor|total)\s+mismatch\b", re.IGNORECASE)
OPEN_QUESTIONS_HEADING = re.compile(r"^##\s+Открытые вопросы.*$", re.MULTILINE)
CLOSED_QUESTIONS_HEADING = re.compile(r"^##\s+Закрытые вопросы.*$", re.MULTILINE)
NEXT_HEADING = re.compile(r"^##\s+", re.MULTILINE)
CRITICAL_MAJOR = ("critical", "major")
CH_OPEN = "open"
CH_NEEDS_ANSWER = "needs-answer"
CH_ANSWERED_LEGACY = "answered"
CH_DEFERRED = "deferred"
CH_RESOLVED = "resolved"
CH_COVERED = "covered"
CH_UNRESOLVED = (CH_OPEN, CH_NEEDS_ANSWER, CH_ANSWERED_LEGACY)


@dataclass
class ChallengeCounts:
    open: int = 0
    deferred: int = 0
    resolved: int = 0
    covered: int = 0
    open_critical: int = 0
    open_major: int = 0


def _section_after(text: str, heading_re: re.Pattern[str]) -> str:
    match = heading_re.search(text)
    if not match:
        return ""
    rest = text[match.end() :]
    next_match = NEXT_HEADING.search(rest)
    return rest[: next_match.start()] if next_match else rest


def deferred_gap_ids(spec_text: str) -> set[str]:
    """GAP ids whose table row is closed / deferred — not dispatch-open."""
    found: set[str] = set()
    for match in TABLE_GAP_RE.finditer(spec_text):
        line_start = spec_text.rfind("\n", 0, match.start()) + 1
        line_end = spec_text.find("\n", match.start())
        row = spec_text[line_start : line_end if line_end != -1 else None].lower()
        if any(marker in row for marker in CLOSED_GAP_MARKERS):
            found.add(match.group(1))
    return found


def collect_open_gaps(spec_text: str) -> list[str]:
    """Open gaps: inline [GAP-ID] + table rows, minus closed/deferred ids."""
    deferred = deferred_gap_ids(spec_text)
    table_open: list[str] = []
    for match in TABLE_GAP_RE.finditer(spec_text):
        gap_id = match.group(1)
        if gap_id not in deferred:
            table_open.append(gap_id)
    inline = [match.group(0)[1:-1] for match in INLINE_GAP_RE.finditer(spec_text)]
    return sorted({gap_id for gap_id in inline + table_open if gap_id not in deferred})


def collect_open_questions(context_text: str) -> list[str]:
    open_ids = set(QUESTION_ID_RE.findall(_section_after(context_text, OPEN_QUESTIONS_HEADING)))
    closed_ids = set(QUESTION_ID_RE.findall(_section_after(context_text, CLOSED_QUESTIONS_HEADING)))
    return sorted(open_ids - closed_ids)


def collect_challenges(challenges_text: str) -> ChallengeCounts:
    counts = ChallengeCounts()
    for match in CHALLENGE_ROW_RE.finditer(challenges_text):
        severity = match.group(2).strip().lower()
        status = match.group(3).strip().lower()
        if status in CH_UNRESOLVED:
            counts.open += 1
            if severity == "critical":
                counts.open_critical += 1
            elif severity == "major":
                counts.open_major += 1
        elif status == CH_DEFERRED:
            counts.deferred += 1
        elif status == CH_RESOLVED:
            counts.resolved += 1
        elif status == CH_COVERED:
            counts.covered += 1
    return counts


def parse_alignment(alignment_text: str) -> tuple[str, int, int]:
    match = FRONTMATTER_RE.match(alignment_text)
    verdict = ""
    iteration = 0
    if match:
        for raw_line in match.group(1).splitlines():
            if raw_line.startswith("verdict:"):
                verdict = raw_line.split(":", 1)[1].strip()
            elif raw_line.startswith("alignment_iteration:"):
                digits = re.sub(r"[^0-9]", "", raw_line.split(":", 1)[1])
                iteration = int(digits) if digits else 0
    mismatch = 0
    for row_match in MISMATCH_ROW_RE.finditer(alignment_text):
        cells = [cell.strip() for cell in row_match.group(1).split("|")]
        cells = [cell for cell in cells if cell]
        if len(cells) < 3:
            continue
        joined = " ".join(cell.lower() for cell in cells)
        if SUMMARY_ROW_RE.search(joined):
            continue
        if not any("mismatch" in cell.lower() for cell in cells):
            continue
        if any(level in joined for level in CRITICAL_MAJOR):
            mismatch += 1
    return verdict, iteration, mismatch


def _artifact(paths: dict[str, Path] | None, key: str) -> Path | None:
    if not paths:
        return None
    path = paths.get(key)
    return path if isinstance(path, Path) else None


def apply_decisions_table(status, paths: dict[str, Path]) -> None:
    path = paths.get("decisions")
    if path is None or not path.is_file():
        return
    status.decisions_needs_answer = 0
    status.decisions_pending_apply = 0
    status.decisions_needs_answer_alignment = 0
    status.decisions_pending_apply_alignment = 0
    for match in DECISION_ROW_RE.finditer(path.read_text(encoding="utf-8")):
        relates = match.group(1)
        flag = match.group(2).strip().lower()
        from_alignment = bool(ALIGNMENT_RELATES_RE.search(relates))
        if flag == "needs-answer":
            status.decisions_needs_answer += 1
            if from_alignment:
                status.decisions_needs_answer_alignment += 1
        elif flag == "pending-apply":
            status.decisions_pending_apply += 1
            if from_alignment:
                status.decisions_pending_apply_alignment += 1


def apply_spec_gaps(status, paths: dict[str, Path]) -> None:
    path = paths.get("spec")
    if path is not None and path.is_file():
        status.open_gaps = collect_open_gaps(path.read_text(encoding="utf-8"))
    else:
        status.open_gaps = []


def apply_context_questions(status, paths: dict[str, Path]) -> None:
    path = paths.get("context")
    if path is not None and path.is_file():
        status.open_questions = collect_open_questions(path.read_text(encoding="utf-8"))
    else:
        status.open_questions = []


def apply_challenges_table(status, paths: dict[str, Path]) -> None:
    path = paths.get("challenges")
    if path is not None and path.is_file():
        status.challenges = collect_challenges(path.read_text(encoding="utf-8"))
    else:
        status.challenges = ChallengeCounts()


def apply_alignment_frontmatter(status, paths: dict[str, Path]) -> None:
    path = paths.get("alignment")
    if path is None or not path.is_file():
        status.verdict = ""
        status.alignment_iteration = 0
        status.critical_major_mismatch = 0
        return
    verdict, iteration, mismatch = parse_alignment(path.read_text(encoding="utf-8"))
    status.verdict = verdict
    status.alignment_iteration = iteration
    status.critical_major_mismatch = mismatch


def parse_routing_snapshot_ts(iso: str | None) -> float | None:
    """Parse ISO Z timestamps from routing-state JSON metadata."""
    if not iso or not str(iso).strip():
        return None
    from pipeline_common import parse_run_log_ts

    try:
        return parse_run_log_ts(str(iso).strip())
    except ValueError:
        return None


def needs_check_feature_from_completion(
    status,
    paths: dict[str, Path],
    step_completion: dict[str, str] | None,
    *,
    satisfied_by_step: str | None = "check-feature",
) -> tuple[bool, str]:
    """Artifact mtimes + pack-config step in routing-state `step_completion`."""
    spec = _artifact(paths, "spec")
    if spec is None or not spec.is_file():
        return False, ""

    spec_mtime = spec.stat().st_mtime
    gaps_map = _artifact(paths, "gaps_map")
    challenges_map = _artifact(paths, "challenges_map")

    if satisfied_by_step and step_completion:
        last_check = parse_routing_snapshot_ts(step_completion.get(satisfied_by_step))
        if last_check is not None and last_check >= spec_mtime - 2:
            return False, ""

    if gaps_map is not None and gaps_map.is_file() and spec_mtime > gaps_map.stat().st_mtime + 1:
        return True, "SPEC новее GAPS_MAP — перепроверка после resolve-gaps"

    if (
        challenges_map is not None
        and challenges_map.is_file()
        and spec_mtime > challenges_map.stat().st_mtime + 1
    ):
        return True, "SPEC новее CHALLENGES_MAP — перепроверка после resolve-challenges"

    if getattr(status, "has_challenges", False) or getattr(status, "has_alignment", False):
        challenges = _artifact(paths, "challenges")
        if challenges is not None and challenges.is_file() and spec_mtime <= challenges.stat().st_mtime + 1:
            return False, ""
        if gaps_map is not None and gaps_map.is_file() and spec_mtime <= gaps_map.stat().st_mtime + 1:
            return False, ""

    if (
        not getattr(status, "has_gaps_map", False)
        and not getattr(status, "has_challenges", False)
        and not getattr(status, "has_alignment", False)
    ):
        return True, "spec не проходила check-feature"

    return True, "нет check-feature после последней правки SPEC"


def needs_check_feature(
    root: Path,
    slug: str,
    status,
    paths: dict[str, Path] | None = None,
) -> tuple[bool, str]:
    """CI / golden etalon (includes run-log when replaying fixtures)."""
    if paths is None:
        from pipeline_status import resolve_artifact_paths

        pid = getattr(status, "pipeline_id", None) or "spec"
        paths = resolve_artifact_paths(root, slug, pid)
    spec = _artifact(paths, "spec")
    if spec is None or not spec.is_file():
        return False, ""

    spec_mtime = spec.stat().st_mtime
    from pipeline_common import last_successful_step_ts

    last_check = last_successful_step_ts(root, slug, "check-feature")
    if last_check is not None and last_check >= spec_mtime - 2:
        return False, ""

    gaps_map = _artifact(paths, "gaps_map")
    challenges_map = _artifact(paths, "challenges_map")

    if gaps_map is not None and gaps_map.is_file() and spec_mtime > gaps_map.stat().st_mtime + 1:
        return True, "SPEC новее GAPS_MAP — перепроверка после resolve-gaps"

    if (
        challenges_map is not None
        and challenges_map.is_file()
        and spec_mtime > challenges_map.stat().st_mtime + 1
    ):
        return True, "SPEC новее CHALLENGES_MAP — перепроверка после resolve-challenges"

    if getattr(status, "has_challenges", False) or getattr(status, "has_alignment", False):
        challenges = _artifact(paths, "challenges")
        if challenges is not None and challenges.is_file() and spec_mtime <= challenges.stat().st_mtime + 1:
            return False, ""
        if gaps_map is not None and gaps_map.is_file() and spec_mtime <= gaps_map.stat().st_mtime + 1:
            return False, ""

    if (
        not getattr(status, "has_gaps_map", False)
        and not getattr(status, "has_challenges", False)
        and not getattr(status, "has_alignment", False)
    ):
        return True, "spec не проходила check-feature"

    return True, "нет check-feature после последней правки SPEC"


def apply_baseline_domain(status, root: Path, slug: str, paths: dict[str, Path] | None = None) -> None:
    """Fill overlay-owned domain fields from files. Engine mtime stale[] stays as-is."""
    if paths is None:
        from pipeline_status import resolve_artifact_paths

        pid = getattr(status, "pipeline_id", None) or "spec"
        paths = resolve_artifact_paths(root, slug, pid)
    apply_decisions_table(status, paths)
    apply_spec_gaps(status, paths)
    apply_context_questions(status, paths)
    apply_challenges_table(status, paths)
    apply_alignment_frontmatter(status, paths)
    needed, reason = needs_check_feature(root, slug, status, paths)
    status.needs_check_feature = needed
    status.needs_check_feature_reason = reason

"""Spec-pack collectors and invariant: GAP/CH/Q, DECISIONS, alignment."""

from __future__ import annotations

import re
from pathlib import Path

from artifact_paths import (
    challenges_map_path,
    challenges_path,
    gaps_map_path,
    spec_path,
)

INLINE_GAP_RE = re.compile(r"\[GAP-[A-Z0-9-]+\]")
TABLE_GAP_RE = re.compile(r"^\|\s*(GAP-[A-Z0-9-]+)\s*\|", re.MULTILINE)
DECISION_ROW_RE = re.compile(
    r"^\|\s*D-\d+\s*\|([^|\n]*)\|(?:[^|\n]*\|){3}\s*([^|]+)\|",
    re.MULTILINE,
)
ALIGNMENT_RELATES_RE = re.compile(r"\b[FICTKAM]-\d+\b")
CLOSED_GAP_MARKERS = ("закрыт", "closed")
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


def _section_after(text: str, heading_re: re.Pattern[str]) -> str:
    match = heading_re.search(text)
    if not match:
        return ""
    rest = text[match.end() :]
    next_match = NEXT_HEADING.search(rest)
    return rest[: next_match.start()] if next_match else rest


def collect_open_gaps(spec_text: str) -> list[str]:
    found = [match.group(0)[1:-1] for match in INLINE_GAP_RE.finditer(spec_text)]
    for match in TABLE_GAP_RE.finditer(spec_text):
        line_start = spec_text.rfind("\n", 0, match.start()) + 1
        line_end = spec_text.find("\n", match.start())
        row = spec_text[line_start:line_end if line_end != -1 else None].lower()
        if not any(marker in row for marker in CLOSED_GAP_MARKERS):
            found.append(match.group(1))
    return sorted(set(found))


def collect_open_questions(context_text: str) -> list[str]:
    open_ids = set(QUESTION_ID_RE.findall(_section_after(context_text, OPEN_QUESTIONS_HEADING)))
    closed_ids = set(QUESTION_ID_RE.findall(_section_after(context_text, CLOSED_QUESTIONS_HEADING)))
    return sorted(open_ids - closed_ids)


def collect_challenges(challenges_text: str):
    from feature_status import ChallengeCounts

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


def collect_decisions_table(_root: Path, _task_id: str, status, paths: dict[str, Path]) -> None:
    path = paths.get("decisions")
    if path is None or not path.is_file():
        return
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


def collect_spec_gaps(_root: Path, _task_id: str, status, paths: dict[str, Path]) -> None:
    path = paths.get("spec")
    if path is not None and path.is_file():
        status.open_gaps = collect_open_gaps(path.read_text(encoding="utf-8"))


def collect_context_questions(_root: Path, _task_id: str, status, paths: dict[str, Path]) -> None:
    path = paths.get("context")
    if path is not None and path.is_file():
        status.open_questions = collect_open_questions(path.read_text(encoding="utf-8"))


def collect_challenges_table(_root: Path, _task_id: str, status, paths: dict[str, Path]) -> None:
    path = paths.get("challenges")
    if path is not None and path.is_file():
        status.challenges = collect_challenges(path.read_text(encoding="utf-8"))


def collect_alignment_frontmatter(_root: Path, _task_id: str, status, paths: dict[str, Path]) -> None:
    path = paths.get("alignment")
    if path is None or not path.is_file():
        return
    verdict, iteration, mismatch = parse_alignment(path.read_text(encoding="utf-8"))
    status.verdict = verdict
    status.alignment_iteration = iteration
    status.critical_major_mismatch = mismatch


COLLECTORS = {
    "decisions_table": collect_decisions_table,
    "spec_gaps": collect_spec_gaps,
    "context_questions": collect_context_questions,
    "challenges_table": collect_challenges_table,
    "alignment_frontmatter": collect_alignment_frontmatter,
}


def needs_check_feature(root: Path, slug: str, status) -> tuple[bool, str]:
    spec = spec_path(root, slug)
    if not spec.is_file():
        return False, ""

    spec_mtime = spec.stat().st_mtime
    gaps_map = gaps_map_path(root, slug)
    challenges_map = challenges_map_path(root, slug)

    from pipeline_common import last_successful_step_ts

    last_check = last_successful_step_ts(root, slug, "check-feature")
    if last_check is not None and last_check >= spec_mtime - 2:
        return False, ""

    if gaps_map.is_file() and spec_mtime > gaps_map.stat().st_mtime + 1:
        return True, "SPEC новее GAPS_MAP — перепроверка после resolve-gaps"

    if challenges_map.is_file() and spec_mtime > challenges_map.stat().st_mtime + 1:
        return True, "SPEC новее CHALLENGES_MAP — перепроверка после resolve-challenges"

    if status.has_challenges or status.has_alignment:
        challenges = challenges_path(root, slug)
        if challenges.is_file() and spec_mtime <= challenges.stat().st_mtime + 1:
            return False, ""
        if gaps_map.is_file() and spec_mtime <= gaps_map.stat().st_mtime + 1:
            return False, ""

    if not status.has_gaps_map and not status.has_challenges and not status.has_alignment:
        return True, "spec не проходила check-feature"

    return True, "нет check-feature после последней правки SPEC"

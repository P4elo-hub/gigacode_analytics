#!/usr/bin/env python3
"""Детерминированный дашборд фичи: артефакты, GAP/CH/Q, verdict, stale, next step."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from artifact_paths import (
    ALIGNMENT_MAX_ITERATIONS,
    VERDICT_FAIL,
    VERDICT_PASS,
    VERDICT_PASS_WITH_GAPS,
    alignment_path,
    challenges_map_path,
    challenges_path,
    context_doc_path,
    decisions_path,
    gaps_map_path,
    list_feature_slugs,
    resolve_slug,
    spec_path,
    workspace_root,
)
INLINE_GAP_RE = re.compile(r"\[GAP-[A-Z0-9-]+\]")
TABLE_GAP_RE = re.compile(r"^\|\s*(GAP-[A-Z0-9-]+)\s*\|", re.MULTILINE)
DECISION_ROW_RE = re.compile(
    r"^\|\s*D-\d+\s*\|([^|\n]*)\|(?:[^|\n]*\|){3}\s*([^|]+)\|",
    re.MULTILINE,
)
# A decision row whose Relates are alignment finding ids belongs to the
# code-alignment loop, whatever the gap/challenge counters say.
ALIGNMENT_RELATES_RE = re.compile(r"\b[FICTKAM]-\d+\b")
CLOSED_GAP_MARKERS = ("закрыт", "closed")
QUESTION_ID_RE = re.compile(r"\bQ-\d+\b")
CHALLENGE_ROW_RE = re.compile(
    r"^\|\s*(CH-\d+)\s*\|(?:[^|\n]*\|){3}\s*([^|]+)\|\s*([^|]+)\|",
    re.MULTILINE,
)
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
MISMATCH_ROW_RE = re.compile(
    r"^\|((?:[^|\n]*\|)+)\s*$",
    re.MULTILINE,
)
SUMMARY_ROW_RE = re.compile(r"\b(?:critical|major|minor|total)\s+mismatch\b", re.IGNORECASE)
OPEN_QUESTIONS_HEADING = re.compile(r"^##\s+Открытые вопросы.*$", re.MULTILINE)
CLOSED_QUESTIONS_HEADING = re.compile(r"^##\s+Закрытые вопросы.*$", re.MULTILINE)
NEXT_HEADING = re.compile(r"^##\s+", re.MULTILINE)
CRITICAL_MAJOR = ("critical", "major")
CH_OPEN = "open"
CH_NEEDS_ANSWER = "needs-answer"
CH_ANSWERED_LEGACY = "answered"  # non-canonical; treat as open until resolved via DECISIONS
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


@dataclass
class FeatureStatus:
    slug: str
    has_context: bool = False
    has_spec: bool = False
    has_decisions: bool = False
    has_gaps_map: bool = False
    decisions_needs_answer: int = 0
    decisions_pending_apply: int = 0
    decisions_needs_answer_alignment: int = 0
    decisions_pending_apply_alignment: int = 0
    has_challenges: bool = False
    has_challenges_map: bool = False
    has_alignment: bool = False
    spec_lines: int = 0
    context_lines: int = 0
    open_gaps: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    challenges: ChallengeCounts = field(default_factory=ChallengeCounts)
    verdict: str = ""
    alignment_iteration: int = 0
    critical_major_mismatch: int = 0
    alignment_stale: bool = False
    stale: list[str] = field(default_factory=list)
    next_command: str = ""
    next_step: str = ""
    next_subagent: str = ""
    next_reason: str = ""
    orchestrator_mode: str = ""
    must_continue: bool = False
    ready: bool = False


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines()) if path.is_file() else 0


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
        # Finding rows carry a severity column plus a claim/evidence pair;
        # two-cell rows are aggregate counters ("MISMATCH (Major) | 2") and
        # aggregate labels ("Major MISMATCH | **2**") — not findings.
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


def needs_check_feature(root: Path, slug: str, status: FeatureStatus) -> tuple[bool, str]:
    """True when check-feature must run before gaps/challenge/code phases."""
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


def detect_stale(root: Path, slug: str) -> list[str]:
    spec = spec_path(root, slug)
    if not spec.is_file():
        return []
    spec_mtime = spec.stat().st_mtime
    stale: list[str] = []
    alignment = alignment_path(root, slug)
    if alignment.is_file() and alignment.stat().st_mtime < spec_mtime:
        stale.append("alignment")
    challenges = challenges_path(root, slug)
    if challenges.is_file() and challenges.stat().st_mtime < spec_mtime:
        stale.append("challenges")
    context = context_doc_path(root, slug)
    if context.is_file() and spec.is_file() and context.stat().st_mtime > spec_mtime:
        stale.append("context-newer-than-spec")
    return stale


def _finalize_orchestrator_mode(status: FeatureStatus) -> None:
    if status.ready:
        status.orchestrator_mode = "ready"
        status.must_continue = False
        return
    if not status.next_step:
        status.orchestrator_mode = "stopped"
        status.must_continue = False
        return
    if status.next_step == "write-feature":
        status.orchestrator_mode = "write_feature_cycle"
        status.must_continue = True
        return
    if status.decisions_needs_answer:
        status.orchestrator_mode = "ask_user"
        status.must_continue = False
        return
    status.orchestrator_mode = "delegate"
    status.must_continue = True


def choose_next_step(status: FeatureStatus, *, root: Path | None = None) -> None:
    if root is None:
        root = workspace_root(Path("."))
    from pipeline_router import apply_router_decision

    apply_router_decision(status, root, status.slug)


def build_status_fields(root: Path, slug: str) -> FeatureStatus:
    """Collect artifact-derived fields without dispatch routing."""
    status = FeatureStatus(slug=slug)
    context = context_doc_path(root, slug)
    spec = spec_path(root, slug)
    status.has_context = context.is_file()
    status.has_spec = spec.is_file()
    decisions = decisions_path(root, slug)
    status.has_decisions = decisions.is_file()
    if status.has_decisions:
        for match in DECISION_ROW_RE.finditer(decisions.read_text(encoding="utf-8")):
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
    status.has_gaps_map = gaps_map_path(root, slug).is_file()
    status.has_challenges = challenges_path(root, slug).is_file()
    status.has_challenges_map = challenges_map_path(root, slug).is_file()
    status.has_alignment = alignment_path(root, slug).is_file()
    status.context_lines = _line_count(context)
    status.spec_lines = _line_count(spec)
    if spec.is_file():
        status.open_gaps = collect_open_gaps(spec.read_text(encoding="utf-8"))
    if context.is_file():
        status.open_questions = collect_open_questions(context.read_text(encoding="utf-8"))
    if status.has_challenges:
        status.challenges = collect_challenges(challenges_path(root, slug).read_text(encoding="utf-8"))
    if status.has_alignment:
        alignment = alignment_path(root, slug)
        verdict, iteration, mismatch = parse_alignment(alignment.read_text(encoding="utf-8"))
        status.verdict = verdict
        status.alignment_iteration = iteration
        status.critical_major_mismatch = mismatch
        # An alignment report written before the latest SPEC edit describes
        # superseded text: its unresolvable FAIL must not re-nominate the
        # resolve step, which would spin the alignment loop forever.
        status.alignment_stale = (
            spec.is_file() and alignment.stat().st_mtime < spec.stat().st_mtime
        )
    status.stale = detect_stale(root, slug)
    return status


def build_status(root: Path, slug: str) -> FeatureStatus:
    status = build_status_fields(root, slug)
    choose_next_step(status, root=root)
    return status


def render_markdown(status: FeatureStatus) -> str:
    mark = lambda present: "✅" if present else "❌"
    alignment = (
        f"✅ итерация {status.alignment_iteration}/{ALIGNMENT_MAX_ITERATIONS}"
        if status.has_alignment
        else "❌"
    )
    if status.ready:
        next_line = f"**Next:** spec готов — {status.next_reason}"
    elif status.next_command:
        agent = f" → `{status.next_subagent}`" if status.next_subagent else ""
        next_line = (
            f"**Next:** `{status.next_command}`{agent} — {status.next_reason}\n"
            f"**Orchestrator:** `{status.orchestrator_mode}`"
            + (" · **продолжай без паузы**" if status.must_continue else "")
            + (
                " · **опроси пользователя по DECISIONS (needs-answer)**"
                if status.orchestrator_mode == "ask_user"
                else ""
            )
        )
    else:
        next_line = f"**Next:** стоп — {status.next_reason}"
    return (
        f"## Фича: {status.slug}\n\n"
        "| Артефакт | Статус |\n|----------|--------|\n"
        f"| CONTEXT_DOC | {mark(status.has_context)} {status.context_lines} строк |\n"
        f"| SPEC | {mark(status.has_spec)} {status.spec_lines} строк |\n"
        f"| DECISIONS | {mark(status.has_decisions)} "
        f"ask {status.decisions_needs_answer} · apply {status.decisions_pending_apply} |\n"
        f"| GAPS_MAP | {mark(status.has_gaps_map)} |\n"
        f"| CHALLENGES | {mark(status.has_challenges)} open {status.challenges.open} |\n"
        f"| CHALLENGES_MAP | {mark(status.has_challenges_map)} |\n"
        f"| ALIGNMENT | {alignment} |\n\n"
        f"**Открыто:** GAP: {len(status.open_gaps)} · CH open: {status.challenges.open} "
        f"(Critical {status.challenges.open_critical}) · Q: {len(status.open_questions)}\n"
        f"**Alignment:** {status.verdict or '—'} "
        f"(итерация {status.alignment_iteration}/{ALIGNMENT_MAX_ITERATIONS}), "
        f"Critical/Major MISMATCH: {status.critical_major_mismatch}\n"
        f"**Устарело:** {', '.join(status.stale) if status.stale else '—'}\n\n"
        f"{next_line}\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="feature-status")
    parser.add_argument("slug", nargs="?")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    root = workspace_root(Path(args.root))
    if not args.slug:
        slugs = list_feature_slugs(root)
        print("Доступные фичи:\n" + "\n".join(f"- {name}" for name in slugs) if slugs else "Фич нет.")
        return 0
    slug = resolve_slug(args.slug, root)
    if slug is None:
        parser.error("не удалось определить slug")
    status = build_status(root, slug)
    print(json.dumps(asdict(status), ensure_ascii=False, indent=2) if args.json else render_markdown(status), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

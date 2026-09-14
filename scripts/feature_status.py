#!/usr/bin/env python3
"""Детерминированный дашборд фичи. Spec-pack wrapper над generic pipeline_status."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from artifact_paths import (
    ALIGNMENT_MAX_ITERATIONS,
    list_feature_slugs,
    resolve_slug,
    workspace_root,
)
from pipeline_pack import DEFAULT_PIPELINE_ID, load_pack_module
from pipeline_status import populate_status

_spec_collectors = load_pack_module("spec", "collectors")
INLINE_GAP_RE = _spec_collectors.INLINE_GAP_RE
TABLE_GAP_RE = _spec_collectors.TABLE_GAP_RE
DECISION_ROW_RE = _spec_collectors.DECISION_ROW_RE
ALIGNMENT_RELATES_RE = _spec_collectors.ALIGNMENT_RELATES_RE
collect_open_gaps = _spec_collectors.collect_open_gaps
collect_open_questions = _spec_collectors.collect_open_questions
collect_challenges = _spec_collectors.collect_challenges
parse_alignment = _spec_collectors.parse_alignment
needs_check_feature = _spec_collectors.needs_check_feature


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
    pipeline_id: str = DEFAULT_PIPELINE_ID
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


def detect_stale(root: Path, slug: str, pipeline_id: str = DEFAULT_PIPELINE_ID) -> list[str]:
    status = FeatureStatus(slug=slug, pipeline_id=pipeline_id)
    populate_status(status, root, slug, pipeline_id)
    return list(status.stale)


def _finalize_orchestrator_mode(status: FeatureStatus, pipeline_id: str | None = None) -> None:
    from pipeline_status import finalize_orchestrator_mode

    finalize_orchestrator_mode(status, pipeline_id or status.pipeline_id)


def choose_next_step(
    status: FeatureStatus,
    *,
    root: Path | None = None,
    pipeline_id: str | None = None,
) -> None:
    if root is None:
        root = workspace_root(Path("."))
    from pipeline_router import apply_router_decision

    apply_router_decision(status, root, status.slug, pipeline_id=pipeline_id or status.pipeline_id)


def build_status_fields(
    root: Path,
    slug: str,
    pipeline_id: str = DEFAULT_PIPELINE_ID,
) -> FeatureStatus:
    status = FeatureStatus(slug=slug, pipeline_id=pipeline_id)
    populate_status(status, root, slug, pipeline_id)
    return status


def build_status(root: Path, slug: str, pipeline_id: str = DEFAULT_PIPELINE_ID) -> FeatureStatus:
    status = build_status_fields(root, slug, pipeline_id)
    choose_next_step(status, root=root, pipeline_id=pipeline_id)
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
    parser.add_argument("--pipeline", default=DEFAULT_PIPELINE_ID)
    args = parser.parse_args(argv)
    root = workspace_root(Path(args.root))
    if not args.slug:
        slugs = list_feature_slugs(root)
        print("Доступные фичи:\n" + "\n".join(f"- {name}" for name in slugs) if slugs else "Фич нет.")
        return 0
    slug = resolve_slug(args.slug, root)
    if slug is None:
        parser.error("не удалось определить slug")
    status = build_status(root, slug, args.pipeline)
    print(json.dumps(asdict(status), ensure_ascii=False, indent=2) if args.json else render_markdown(status), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

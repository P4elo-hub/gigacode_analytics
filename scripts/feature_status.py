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
from pipeline_pack import DEFAULT_PIPELINE_ID
from pipeline_status import load_status_spec, populate_status
from routing_state_baseline import ChallengeCounts


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
    decisions_needs_answer_gaps: int = 0
    decisions_pending_apply_gaps: int = 0
    decisions_needs_answer_challenges: int = 0
    decisions_pending_apply_challenges: int = 0
    has_challenges: bool = False
    has_challenges_map: bool = False
    has_alignment: bool = False
    has_routing_state: bool = False
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
    needs_check_feature: bool = False
    needs_check_feature_reason: str = ""
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


def _format_ctx(status: FeatureStatus, spec: dict) -> dict:
    constants = spec.get("constants") or {}
    max_iter = constants.get("alignment_max_iterations", ALIGNMENT_MAX_ITERATIONS)
    challenges = status.challenges
    return {
        "slug": status.slug,
        "context_lines": status.context_lines,
        "spec_lines": status.spec_lines,
        "decisions_needs_answer": status.decisions_needs_answer,
        "decisions_pending_apply": status.decisions_pending_apply,
        "challenges_open": challenges.open,
        "challenges_open_critical": challenges.open_critical,
        "alignment_iteration": status.alignment_iteration,
        "alignment_max_iterations": max_iter,
        "open_gaps_count": len(status.open_gaps),
        "open_questions_count": len(status.open_questions),
        "verdict": status.verdict or "—",
        "critical_major_mismatch": status.critical_major_mismatch,
        "stale_list": ", ".join(status.stale) if status.stale else "—",
        "next_reason": status.next_reason,
        "next_command": status.next_command,
        "next_subagent": status.next_subagent,
        "orchestrator_mode": status.orchestrator_mode,
    }


def _render_table(status: FeatureStatus, spec: dict, ctx: dict) -> str:
    mark = lambda present: "✅" if present else "❌"
    display = spec.get("display") or {}
    rows = display.get("rows")
    lines = ["| Артефакт | Статус |", "|----------|--------|"]
    if isinstance(rows, list) and rows:
        for row in rows:
            if not isinstance(row, dict):
                continue
            present = bool(getattr(status, str(row.get("exists") or ""), False))
            if present and row.get("present_format"):
                cell = str(row["present_format"]).format(**ctx)
            elif not present and row.get("absent_format"):
                cell = str(row["absent_format"]).format(**ctx)
            else:
                suffix = str(row.get("suffix") or "").format(**ctx).strip()
                cell = f"{mark(present)} {suffix}".rstrip()
            lines.append(f"| {row.get('label', '')} | {cell} |")
        return "\n".join(lines)
    artifacts = spec.get("artifacts") or {}
    for art_id, art in artifacts.items():
        if not isinstance(art, dict):
            continue
        exists_as = art.get("exists_as") or f"has_{art_id}"
        present = bool(getattr(status, exists_as, False))
        lines_as = art.get("lines_as")
        extra = f" {getattr(status, lines_as, 0)} строк" if lines_as else ""
        lines.append(f"| {art_id} | {mark(present)}{extra} |")
    return "\n".join(lines)


def render_markdown(status: FeatureStatus) -> str:
    spec = load_status_spec(status.pipeline_id)
    ctx = _format_ctx(status, spec)
    display = spec.get("display") or {}
    heading = str(display.get("heading") or "Фича: {slug}").format(**ctx)
    table = _render_table(status, spec, ctx)
    max_iter = ctx["alignment_max_iterations"]
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
        f"## {heading}\n\n"
        f"{table}\n\n"
        f"**Открыто:** GAP: {len(status.open_gaps)} · CH open: {status.challenges.open} "
        f"(Critical {status.challenges.open_critical}) · Q: {len(status.open_questions)}\n"
        f"**Alignment:** {status.verdict or '—'} "
        f"(итерация {status.alignment_iteration}/{max_iter}), "
        f"Critical/Major MISMATCH: {status.critical_major_mismatch}\n"
        f"**Устарело:** {', '.join(status.stale) if status.stale else '—'}\n\n"
        f"{next_line}\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="feature-status")
    parser.add_argument("slug", nargs="?")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--root", default=".")
    parser.add_argument("--pipeline", default=None, help="Pipeline id (required when slug is provided)")
    args = parser.parse_args(argv)
    root = workspace_root(Path(args.root))
    if not args.slug:
        slugs = list_feature_slugs(root)
        print("Доступные фичи:\n" + "\n".join(f"- {name}" for name in slugs) if slugs else "Фич нет.")
        return 0
    slug = resolve_slug(args.slug, root)
    if slug is None:
        parser.error("не удалось определить slug")
    if not args.pipeline:
        parser.error("--pipeline <id> is required")
    status = build_status(root, slug, args.pipeline)
    print(json.dumps(asdict(status), ensure_ascii=False, indent=2) if args.json else render_markdown(status), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

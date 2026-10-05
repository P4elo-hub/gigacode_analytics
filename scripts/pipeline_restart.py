#!/usr/bin/env python3
"""Plan and apply pipeline restart from a given step (rollback downstream artifacts)."""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from artifact_paths import (
    alignment_path,
    challenges_map_path,
    challenges_path,
    context_doc_path,
    decisions_path,
    feature_dir,
    gaps_map_path,
    resolve_slug,
    spec_path,
    workspace_root,
)
from pipeline_common import (
    known_pipeline_ids,
    pipeline_restartable_steps,
    pipeline_step_order,
    step_to_command,
    subagent_for_step,
)
from pipeline_pack import DEFAULT_PIPELINE_ID

# Spec-pack snapshots for callers that still import module-level aliases.
RESTARTABLE_STEPS = pipeline_restartable_steps(DEFAULT_PIPELINE_ID)
STEP_ORDER = pipeline_step_order(DEFAULT_PIPELINE_ID)

REPORT_SUFFIXES = (
    "-decisions.md",
    "-code-alignment.md",
    "-gaps-resolved.md",
    "-challenges.md",
    "-challenges-resolved.md",
)


@dataclass
class RestartPlan:
    slug: str
    from_step: str
    from_seq: int | None = None
    next_step: str = ""
    next_command: str = ""
    next_subagent: str = ""
    remove_paths: list[str] = field(default_factory=list)
    keep_paths: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    marker_path: str = ""
    pipeline_id: str = DEFAULT_PIPELINE_ID


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_cli_commands(slug: str, step: str, *, subagent: str = "", pipeline_id: str = DEFAULT_PIPELINE_ID) -> dict:
    """Copy-paste commands for Qwen/GigaCode after rollback."""
    resolved_subagent = subagent or subagent_for_step(step, pipeline_id)
    slash = step_to_command(step, slug)
    return {
        "slug": slug,
        "next_step": step,
        "next_subagent": resolved_subagent,
        "slash_command": slash,
        "orchestrator_command": f"продолжи {slug}",
    }


def format_cli_block(commands: dict) -> str:
    lines = [
        f"Фича: {commands['slug']}",
        "",
        commands["slash_command"],
        "",
        commands["orchestrator_command"],
    ]
    if commands.get("next_subagent"):
        lines.extend(["", f"→ {commands['next_subagent']}"])
    return "\n".join(lines)


def refresh_plan_from_dispatch(root: Path, plan: RestartPlan, pipeline_id: str = DEFAULT_PIPELINE_ID) -> dict:
    """Set plan.next_* from pipeline_dispatch after artifacts changed."""
    from pipeline_dispatch import build_dispatch

    restartable = pipeline_restartable_steps(pipeline_id)
    order = pipeline_step_order(pipeline_id)
    dispatch = build_dispatch(root, plan.slug, pipeline_id=pipeline_id)
    step = dispatch.get("next_step") or plan.from_step
    if step not in restartable:
        step = plan.from_step
    elif order.get(step, 0) < order.get(plan.from_step, 0):
        step = plan.from_step

    plan.next_step = step
    plan.next_command = dispatch.get("next_command") or step_to_command(step, plan.slug)
    plan.next_subagent = dispatch.get("next_subagent") or subagent_for_step(step, pipeline_id)
    return build_cli_commands(plan.slug, step, subagent=plan.next_subagent, pipeline_id=pipeline_id)


def _discovery_path(root: Path, slug: str) -> Path:
    return root / "Feature-context" / f"{slug}-discovery.md"


def _marker_path(root: Path, slug: str, pipeline_id: str = DEFAULT_PIPELINE_ID) -> Path:
    if pipeline_id == DEFAULT_PIPELINE_ID:
        return feature_dir(root, slug) / ".pipeline-restart.json"
    from calibration_paths import calibration_slug_dir

    return calibration_slug_dir(root, slug) / ".pipeline-restart.json"


def load_restart_marker(root: Path, slug: str, pipeline_id: str = DEFAULT_PIPELINE_ID) -> dict | None:
    path = _marker_path(root, slug, pipeline_id)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return payload if isinstance(payload, dict) else None


def clear_restart_marker_if_ready(root: Path, slug: str) -> bool:
    """Drop stale restart marker once dispatch reports spec ready."""
    path = _marker_path(root, slug, DEFAULT_PIPELINE_ID)
    if not path.is_file():
        return False
    from feature_status import build_status

    if not build_status(root, slug).ready:
        return False
    path.unlink(missing_ok=True)
    return True


def redo_steps_from(from_step: str, pipeline_id: str = DEFAULT_PIPELINE_ID) -> list[str]:
    order = pipeline_step_order(pipeline_id)
    restartable = pipeline_restartable_steps(pipeline_id)
    if from_step not in order:
        return []
    from_index = order[from_step]
    return [name for name in restartable if order[name] >= from_index]


def _rel(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def _collect_feature_dir_extras(root: Path, slug: str) -> list[Path]:
    fd = feature_dir(root, slug)
    if not fd.is_dir():
        return []
    found: list[Path] = []
    for child in fd.iterdir():
        name = child.name
        if name == ".pipeline-restart.json":
            continue
        if name.startswith(f"{slug}.part-") and name.endswith(".md"):
            found.append(child)
        elif name == f"{slug}.context.md":
            found.append(child)
    return found


def _paths_from_step_index(
    root: Path,
    slug: str,
    from_index: int,
    step_order: dict[str, int],
) -> tuple[list[Path], list[Path]]:
    remove: list[Path] = []
    keep: list[Path] = []

    ctx = context_doc_path(root, slug)
    spec = spec_path(root, slug)
    fd = feature_dir(root, slug)

    if from_index <= step_order["find-context"]:
        if fd.is_dir():
            for child in fd.iterdir():
                if child.name != ".pipeline-restart.json":
                    remove.append(child)
        for path in (ctx, _discovery_path(root, slug)):
            if path.is_file():
                remove.append(path)
        keep = []
        return remove, keep

    if ctx.is_file():
        keep.append(ctx)

    if from_index <= step_order["write-feature"]:
        if fd.is_dir():
            for child in fd.iterdir():
                if child.name != ".pipeline-restart.json":
                    remove.append(child)
        return remove, keep

    if spec.is_file():
        keep.append(spec)

    if from_index <= step_order["check-feature"]:
        for path in (
            decisions_path(root, slug),
            gaps_map_path(root, slug),
            challenges_path(root, slug),
            challenges_map_path(root, slug),
            alignment_path(root, slug),
        ):
            if path.is_file():
                remove.append(path)
        remove.extend(_collect_feature_dir_extras(root, slug))
        return remove, keep

    if from_index <= step_order["resolve-gaps"]:
        for path in (
            decisions_path(root, slug),
            gaps_map_path(root, slug),
            challenges_path(root, slug),
            challenges_map_path(root, slug),
            alignment_path(root, slug),
        ):
            if path.is_file():
                remove.append(path)
        return remove, keep

    if from_index <= step_order["challenge-feature"]:
        for path in (
            decisions_path(root, slug),
            challenges_path(root, slug),
            challenges_map_path(root, slug),
            alignment_path(root, slug),
        ):
            if path.is_file():
                remove.append(path)
        return remove, keep

    if from_index <= step_order["resolve-challenges"]:
        for path in (
            decisions_path(root, slug),
            challenges_map_path(root, slug),
            alignment_path(root, slug),
        ):
            if path.is_file():
                remove.append(path)
        return remove, keep

    if from_index <= step_order["check-feature-code"]:
        if alignment_path(root, slug).is_file():
            remove.append(alignment_path(root, slug))
        return remove, keep

    if from_index <= step_order["resolve-code-alignment"]:
        for path in (alignment_path(root, slug), decisions_path(root, slug)):
            if path.is_file():
                remove.append(path)
        return remove, keep

    return remove, keep


def _add_existing(paths: list[Path], path: Path) -> None:
    if path.exists():
        paths.append(path)


def _paths_from_calibration(
    root: Path,
    slug: str,
    from_index: int,
    step_order: dict[str, int],
) -> tuple[list[Path], list[Path]]:
    """Rollback Calibration/<slug>/runs/<current> from from_index onward. Never Feature-writing."""
    from agent_logs import load_manifest, run_dir
    from calibration_paths import (
        baseline_dir,
        calibration_run_dir,
        context_gaps_json_path,
        context_gaps_path,
        delta_analysis_path,
        delta_summary_path,
        gold_dir,
        human_review_path,
        inputs_lock_path,
        load_calibration_manifest,
        proposals_dir,
        rerun_dir,
        review_dir,
        scorecard_path,
    )

    remove: list[Path] = []
    keep: list[Path] = []
    run_id = load_calibration_manifest(root, slug).get("current_run")
    if not run_id:
        return remove, keep

    def at_or_before(step: str) -> bool:
        return from_index <= step_order.get(step, 999)

    run = calibration_run_dir(root, slug, run_id)
    if at_or_before("snapshot-baseline"):
        if run.is_dir():
            for child in run.iterdir():
                remove.append(child)
        return remove, keep

    _add_existing(keep, baseline_dir(root, slug, run_id))
    _add_existing(keep, inputs_lock_path(root, slug, run_id))

    if at_or_before("capture-review"):
        _add_existing(remove, gold_dir(root, slug, run_id))
        _add_existing(remove, review_dir(root, slug, run_id))
        _add_existing(remove, proposals_dir(root, slug, run_id))
        _add_existing(remove, rerun_dir(root, slug, run_id))
        _add_existing(remove, scorecard_path(root, slug, run_id))
        return remove, keep

    _add_existing(keep, gold_dir(root, slug, run_id))
    _add_existing(keep, human_review_path(root, slug, run_id))

    if at_or_before("analyze-delta"):
        _add_existing(remove, delta_analysis_path(root, slug, run_id))
        _add_existing(remove, delta_summary_path(root, slug, run_id))
        _add_existing(remove, context_gaps_path(root, slug, run_id))
        _add_existing(remove, context_gaps_json_path(root, slug, run_id))
        _add_existing(remove, proposals_dir(root, slug, run_id))
        _add_existing(remove, rerun_dir(root, slug, run_id))
        _add_existing(remove, scorecard_path(root, slug, run_id))
        return remove, keep

    _add_existing(keep, delta_analysis_path(root, slug, run_id))
    _add_existing(keep, context_gaps_path(root, slug, run_id))

    if at_or_before("analyze-telemetry"):
        agent_run = load_manifest(root, slug).get("current_run")
        if agent_run:
            _add_existing(remove, run_dir(root, slug, agent_run) / "telemetry-analysis.md")
        _add_existing(remove, proposals_dir(root, slug, run_id))
        _add_existing(remove, rerun_dir(root, slug, run_id))
        _add_existing(remove, scorecard_path(root, slug, run_id))
        return remove, keep

    if at_or_before("propose-calibration"):
        _add_existing(remove, proposals_dir(root, slug, run_id))
        _add_existing(remove, rerun_dir(root, slug, run_id))
        _add_existing(remove, scorecard_path(root, slug, run_id))
        return remove, keep

    _add_existing(keep, proposals_dir(root, slug, run_id))

    if at_or_before("apply-calibration"):
        _add_existing(remove, rerun_dir(root, slug, run_id))
        _add_existing(remove, scorecard_path(root, slug, run_id))
        return remove, keep

    if at_or_before("benchmark-rerun"):
        _add_existing(remove, rerun_dir(root, slug, run_id))
        _add_existing(remove, scorecard_path(root, slug, run_id))
        return remove, keep

    return remove, keep


def build_restart_plan(
    root: Path,
    slug: str,
    from_step: str,
    *,
    from_seq: int | None = None,
    pipeline_id: str = DEFAULT_PIPELINE_ID,
) -> RestartPlan:
    restartable = pipeline_restartable_steps(pipeline_id)
    order = pipeline_step_order(pipeline_id)
    if from_step not in restartable:
        raise ValueError(f"Шаг «{from_step}» нельзя использовать для перезапуска")

    from_index = order[from_step]
    if pipeline_id == DEFAULT_PIPELINE_ID:
        remove, keep = _paths_from_step_index(root, slug, from_index, order)
        warnings = [
            "SPEC и CONTEXT_DOC не откатываются по snapshot — остаются как есть. "
            "При необходимости восстановите из git вручную.",
            "Телеметрия agent-logs не удаляется (история сохраняется).",
        ]
        if from_step == "find-context":
            warnings.append("Будет очищена папка Feature-writing/<slug>/ и context-doc.")
    elif pipeline_id == "calibration":
        remove, keep = _paths_from_calibration(root, slug, from_index, order)
        warnings = [
            "Feature-writing / SPEC не трогаются — только Calibration/<slug>/ текущего run.",
            "events.jsonl и run-log не удаляются. telemetry-analysis.md текущего agent-run "
            "снимается, если откат с analyze-telemetry или раньше.",
            "Патчи скиллов после apply-calibration git не откатывает — restore вручную.",
        ]
        if from_step == "snapshot-baseline":
            warnings.append("Будет очищен текущий Calibration run (baseline/gold/review/…).")
    else:
        remove, keep = [], []
        warnings = [
            f"Откат файлов для pipeline `{pipeline_id}` не задан — только маркер restart.",
        ]

    if from_seq is not None:
        warnings.insert(
            0,
            f"Перезапуск по проходу #{from_seq}: откат по фазе «{from_step}», "
            "не по состоянию файлов на момент прохода.",
        )

    commands = build_cli_commands(slug, from_step, pipeline_id=pipeline_id)
    plan = RestartPlan(
        slug=slug,
        from_step=from_step,
        from_seq=from_seq,
        next_step=commands["next_step"],
        next_command=commands["slash_command"],
        next_subagent=commands["next_subagent"],
        remove_paths=sorted({_rel(root, p) for p in remove}),
        keep_paths=sorted({_rel(root, p) for p in keep}),
        warnings=warnings,
        marker_path=_rel(root, _marker_path(root, slug, pipeline_id)),
        pipeline_id=pipeline_id,
    )
    return plan


def apply_restart_plan(root: Path, plan: RestartPlan) -> dict:
    removed: list[str] = []
    errors: list[str] = []

    for rel in plan.remove_paths:
        path = (root / rel).resolve()
        if not path.exists():
            continue
        try:
            _assert_safe_path(root, path)
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            removed.append(rel)
        except OSError as exc:
            errors.append(f"{rel}: {exc}")

    cli_commands = refresh_plan_from_dispatch(root, plan, pipeline_id=plan.pipeline_id)
    cli_block = format_cli_block(cli_commands)

    marker = root / plan.marker_path
    marker.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "slug": plan.slug,
        "from_step": plan.from_step,
        "from_seq": plan.from_seq,
        "created_at": _iso_now(),
        "next_step": plan.next_step,
        "next_command": plan.next_command,
        "next_subagent": plan.next_subagent,
        "cli_commands": cli_commands,
        "cli_block": cli_block,
        "pipeline_id": plan.pipeline_id,
        "removed": removed,
    }
    marker.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "ok": not errors,
        "removed": removed,
        "errors": errors,
        "marker": plan.marker_path,
        "next_command": plan.next_command,
        "cli_commands": cli_commands,
        "cli_block": cli_block,
    }


def _assert_safe_path(root: Path, path: Path) -> None:
    root = root.resolve()
    path = path.resolve()
    if not str(path).startswith(str(root)):
        raise ValueError(f"Path outside workspace: {path}")
    rel = path.relative_to(root)
    parts = rel.parts
    if parts[0] == "Feature-writing" and len(parts) >= 2:
        return
    if parts[0] == "Feature-context" and len(parts) >= 2:
        return
    if parts[0] == "Calibration" and len(parts) >= 2:
        return
    if parts[0] == "agent-logs" and parts[-1] == "telemetry-analysis.md":
        return
    raise ValueError(f"Refusing to delete outside feature paths: {rel}")


def plan_to_dict(plan: RestartPlan) -> dict:
    cli_commands = build_cli_commands(
        plan.slug,
        plan.next_step or plan.from_step,
        subagent=plan.next_subagent,
        pipeline_id=plan.pipeline_id,
    )
    cli_block = format_cli_block(cli_commands)
    return {
        "slug": plan.slug,
        "pipeline_id": plan.pipeline_id,
        "from_step": plan.from_step,
        "from_seq": plan.from_seq,
        "next_step": plan.next_step,
        "next_command": plan.next_command,
        "next_subagent": plan.next_subagent,
        "cli_commands": cli_commands,
        "cli_block": cli_block,
        "remove_paths": plan.remove_paths,
        "keep_paths": plan.keep_paths,
        "warnings": plan.warnings,
        "marker_path": plan.marker_path,
        "remove_count": len(plan.remove_paths),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slug")
    parser.add_argument("--from-step", required=True, dest="from_step")
    parser.add_argument("--from-seq", type=int, default=None)
    parser.add_argument("--apply", action="store_true", help="Delete files (default: dry-run plan)")
    parser.add_argument("--root", default=".", type=Path)
    parser.add_argument(
        "--pipeline",
        required=True,
        help=f"Pipeline id. Known: {', '.join(known_pipeline_ids())}",
    )
    args = parser.parse_args(argv)

    root = workspace_root(args.root)
    slug = resolve_slug(args.slug, root)
    if slug is None:
        raise SystemExit("slug not found")
    if args.pipeline not in known_pipeline_ids():
        raise SystemExit(f"unknown pipeline: {args.pipeline}")

    plan = build_restart_plan(
        root, slug, args.from_step, from_seq=args.from_seq, pipeline_id=args.pipeline
    )
    if args.apply:
        result = apply_restart_plan(root, plan)
        print(json.dumps({"plan": plan_to_dict(plan), "result": result}, ensure_ascii=False, indent=2))
        return 0 if result.get("ok") else 1

    print(json.dumps(plan_to_dict(plan), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

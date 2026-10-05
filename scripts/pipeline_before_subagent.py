#!/usr/bin/env python3
"""PreToolUse hook: block `task` when subagent_type ≠ pipeline_delegate active-task."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from artifact_paths import list_feature_slugs
from build_pipeline_graph import subagent_to_step
from pipeline_active_task import SKIP_SUBAGENTS, load_active_task_for_slug, load_active_task_latest
from inner_cycle import is_cycle_mode
from pipeline_common import delegate_mode_for_subagent, pipeline_gated_subagents, write_cycle_config
from pipeline_dispatch import build_dispatch
from pipeline_divergence import is_allowed_transition, last_ok_pipeline_step
from pipeline_pack import add_pack_dir_argument, apply_pack_dir_from_args, workspace_root_for_run
from pipeline_position import resolve_position
from pipeline_runtime import load_pipeline_schema, resolve_pipeline_id

DELEGATE_CMD = "python3 scripts/pipeline_delegate.py <slug> --pipeline <id>"


def parse_hook_input(raw: str) -> dict:
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def extract_proposed_subagent(tool_name: str, tool_input: dict) -> str:
    if not isinstance(tool_input, dict):
        return ""
    if tool_name == "task":
        return str(tool_input.get("subagent_type") or tool_input.get("subagent") or "").strip()
    if tool_name.lower() in {"agent", "delegate"}:
        for key in ("subagent_type", "subagent", "agent", "name", "agent_type"):
            value = tool_input.get(key)
            if value:
                return str(value).strip()
    return ""


def allow_output(reason: str) -> dict:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": reason,
        }
    }


def deny_output(reason: str) -> dict:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def write_feature_allowed(root: Path, slug: str, active: dict | None, pipeline_id: str) -> bool:
    cycle = write_cycle_config(pipeline_id)
    if not cycle:
        return False
    step = cycle.get("step")
    subagent = cycle.get("subagent")
    if active and active.get("step") == step and active.get("subagent") == subagent:
        return True
    if not slug:
        return False
    dispatch = build_dispatch(root, slug, pipeline_id=pipeline_id)
    return is_cycle_mode(dispatch.get("orchestrator_mode"))


def validate_task(
    root: Path,
    proposed: str,
    *,
    slug_hint: str = "",
    pipeline_arg: str | None = None,
) -> dict:
    if not proposed:
        return deny_output("task без subagent_type — укажи subagent_type из pipeline_delegate JSON.")

    if proposed in SKIP_SUBAGENTS:
        return allow_output(f"subagent {proposed} вне spec-pipeline gate")

    active = load_active_task_latest(root)
    slug = (active or {}).get("slug") or slug_hint
    try:
        pipeline_id = resolve_pipeline_id(pipeline_arg, active)
    except ValueError as exc:
        return deny_output(str(exc))
    gated = pipeline_gated_subagents(pipeline_id)

    if proposed not in gated:
        return allow_output(f"subagent {proposed} не требует pipeline delegate")

    cycle_mode = delegate_mode_for_subagent(pipeline_id, proposed)
    if cycle_mode:
        mode_name, _block = cycle_mode
        if write_feature_allowed(root, slug, active, pipeline_id):
            return allow_output(f"{mode_name}: {proposed} разрешён в цикле клетки")
        return deny_output(
            f"{proposed} только внутри {mode_name}. "
            f"Сначала {DELEGATE_CMD.replace('<slug>', slug or '<slug>')}."
        )

    if not active:
        return deny_output(
            "Нет .pipeline-active-task.json — `task` без delegate запрещён. "
            f"Сначала {DELEGATE_CMD.replace('<slug>', slug or '<slug>')}."
        )

    schema = load_pipeline_schema(pipeline_id)
    proposed_step = subagent_to_step(schema, proposed) or ""
    if proposed_step and slug:
        # Unlike delegate, the hook has no slug argument: `slug` comes from the
        # workspace-wide marker, which any concurrent session or test helper can
        # overwrite with its own feature. Prefer the per-feature marker matching the
        # step being requested — that is the calling session's own reservation.
        active = load_active_task_for_slug(root, slug)
        if not active or (active.get("step") or "") != proposed_step:
            for candidate in list_feature_slugs(root):
                task = load_active_task_for_slug(root, candidate)
                if (task or {}).get("step") == proposed_step:
                    active, slug = task, candidate
                    break

        standing = resolve_position(root, slug, pipeline_id)
        last = last_ok_pipeline_step(root, slug, pipeline_id)
        from_step = (
            (standing.get("step") if standing else None)
            or (last.get("step") if last else None)
            or schema.get("orchestrator")
        )
        if not is_allowed_transition(schema, from_step, proposed_step):
            allowed = [
                e.get("to")
                for e in schema.get("edges", [])
                if e.get("from") == from_step
            ]
            return deny_output(
                f"Граф запрещает `{from_step}` → `{proposed_step}` (subagent `{proposed}`). "
                f"Допустимо: {', '.join(allowed) or '—'}. "
                f"Сначала {DELEGATE_CMD.replace('<slug>', slug)}."
            )

    expected = str(active.get("subagent") or "").strip()
    if proposed != expected:
        step = active.get("step") or "?"
        return deny_output(
            f"Subagent `{proposed}` ≠ delegate `{expected}` (step `{step}`). "
            f"Не improvising: {DELEGATE_CMD.replace('<slug>', slug or active.get('slug', '<slug>'))} "
            "и `task` только на task.subagent_type из JSON."
        )

    return allow_output(f"subagent `{proposed}` совпадает с active-task delegate")


def before_subagent_hook(root: Path, hook_input: dict, pipeline_arg: str | None = None) -> dict:
    tool_name = str(hook_input.get("tool_name") or "").strip()
    tool_input = hook_input.get("tool_input")
    if not isinstance(tool_input, dict):
        tool_input = {}

    proposed = extract_proposed_subagent(tool_name, tool_input)
    return validate_task(root, proposed, pipeline_arg=pipeline_arg)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", choices=("qwen", "gigacode", "opencode"), default="qwen")
    parser.add_argument(
        "--pipeline",
        default=None,
        help="Override pipeline id (default: value from .pipeline-active-task.json)",
    )
    parser.add_argument("--workspace", type=Path, default=None)
    add_pack_dir_argument(parser)
    parser.add_argument("--stdin-file", type=Path, help="Hook input file (default: stdin)")
    parser.add_argument("--proposed-subagent", help="Dry-run: subagent_type to validate")
    parser.add_argument("--slug", help="Dry-run: slug hint when active-task missing")
    args = parser.parse_args(argv)

    try:
        apply_pack_dir_from_args(args)
    except (FileNotFoundError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), ensure_ascii=False)
        return 1

    root = (args.workspace or workspace_root_for_run()).resolve()

    if args.proposed_subagent is not None:
        payload = validate_task(
            root,
            args.proposed_subagent.strip(),
            slug_hint=args.slug or "",
            pipeline_arg=args.pipeline,
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        decision = payload["hookSpecificOutput"]["permissionDecision"]
        return 0 if decision == "allow" else 1

    if args.stdin_file:
        raw = args.stdin_file.read_text(encoding="utf-8")
    else:
        raw = sys.stdin.read()

    payload = before_subagent_hook(root, parse_hook_input(raw), pipeline_arg=args.pipeline)
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

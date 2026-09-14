#!/usr/bin/env python3
"""PreToolUse hook: block `task` when subagent_type ≠ pipeline_delegate active-task."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from artifact_paths import list_feature_slugs, workspace_root
from build_pipeline_graph import subagent_to_step
from pipeline_active_task import SKIP_SUBAGENTS, load_active_task_for_slug, load_active_task_latest
from pipeline_common import pipeline_gated_subagents
from pipeline_dispatch import build_dispatch
from pipeline_divergence import is_allowed_transition, last_ok_pipeline_step
from pipeline_runtime import DEFAULT_PIPELINE_ID, load_pipeline_schema, resolve_pipeline_id

PIPELINE_GATED_SUBAGENTS = pipeline_gated_subagents()

DELEGATE_CMD = "python3 scripts/pipeline_delegate.py <slug> --cli qwen"


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


def write_feature_allowed(root: Path, slug: str, active: dict | None) -> bool:
    if active and active.get("step") == "write-feature" and active.get("subagent") == "spec-writer":
        return True
    if not slug:
        return False
    dispatch = build_dispatch(root, slug)
    return dispatch.get("orchestrator_mode") == "write_feature_cycle"


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

    if proposed not in PIPELINE_GATED_SUBAGENTS:
        return allow_output(f"subagent {proposed} не требует pipeline delegate")

    active = load_active_task_latest(root)
    slug = (active or {}).get("slug") or slug_hint

    if proposed == "spec-writer":
        if write_feature_allowed(root, slug, active):
            return allow_output("write-feature: spec-writer разрешён в write_feature_cycle")
        return deny_output(
            "spec-writer только внутри write_feature_cycle. "
            f"Сначала {DELEGATE_CMD.replace('<slug>', slug or '<slug>')}."
        )

    if not active:
        return deny_output(
            "Нет .pipeline-active-task.json — `task` без delegate запрещён. "
            f"Сначала {DELEGATE_CMD.replace('<slug>', slug or '<slug>')}."
        )

    pipeline_id = resolve_pipeline_id(pipeline_arg, active, default=DEFAULT_PIPELINE_ID)
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

        last = last_ok_pipeline_step(root, slug)
        from_step = (last.get("step") if last else None) or schema.get("orchestrator")
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


def before_subagent_hook(root: Path, hook_input: dict) -> dict:
    tool_name = str(hook_input.get("tool_name") or "").strip()
    tool_input = hook_input.get("tool_input")
    if not isinstance(tool_input, dict):
        tool_input = {}

    proposed = extract_proposed_subagent(tool_name, tool_input)
    return validate_task(root, proposed)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", choices=("qwen", "gigacode", "opencode"), default="qwen")
    parser.add_argument(
        "--pipeline",
        default=None,
        help="Override pipeline id (default: value from .pipeline-active-task.json)",
    )
    parser.add_argument("--workspace", type=Path, default=None)
    parser.add_argument("--stdin-file", type=Path, help="Hook input file (default: stdin)")
    parser.add_argument("--proposed-subagent", help="Dry-run: subagent_type to validate")
    parser.add_argument("--slug", help="Dry-run: slug hint when active-task missing")
    args = parser.parse_args(argv)

    root = (args.workspace or workspace_root()).resolve()

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

    payload = before_subagent_hook(root, parse_hook_input(raw))
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

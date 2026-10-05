#!/usr/bin/env python3
"""Deterministic next pipeline step for the spec orchestrator."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from artifact_paths import resolve_slug, workspace_root
from feature_status import build_status
from pipeline_common import pipeline_step_to_subagent, subagent_for_step
from pipeline_runtime import (
    DEFAULT_PIPELINE_ID,
    dispatch_supported,
    known_pipeline_ids,
    normalize_pipeline_id,
)


def _unsupported_dispatch(slug: str, pipeline_id: str) -> dict:
    return {
        "pipeline_id": pipeline_id,
        "slug": slug,
        "dispatch": None,
        "dispatch_supported": False,
        "ready": False,
        "next_step": "",
        "next_command": "",
        "next_subagent": "",
        "next_reason": "dispatch not configured; orchestrator follows markdown/graph order",
        "orchestrator_mode": "orchestrator_only",
        "must_continue": False,
        "exit_policy": {
            "stop_when": ["orchestrator_only"],
            "continue_on_subagent_fail": True,
            "continue_on_pending_apply": True,
        },
        "allowed_subagents": [],
        "step_to_subagent": {},
    }


def build_dispatch(root: Path, slug: str, pipeline_id: str = DEFAULT_PIPELINE_ID) -> dict:
    pipe_id = normalize_pipeline_id(pipeline_id)
    if not dispatch_supported(pipe_id):
        return _unsupported_dispatch(slug, pipe_id)

    status = build_status(root, slug, pipe_id)
    step_map = pipeline_step_to_subagent(pipe_id)
    payload = {
        "pipeline_id": pipe_id,
        "slug": status.slug,
        "dispatch_supported": True,
        "ready": status.ready,
        "next_step": status.next_step,
        "next_command": status.next_command,
        "next_subagent": status.next_subagent,
        "next_reason": status.next_reason,
        "orchestrator_mode": status.orchestrator_mode,
        "must_continue": status.must_continue,
        "exit_policy": {
            "stop_when": [
                "ready",
                "ask_user_needs_answer",
                "stopped_hard",
            ],
            "continue_on_subagent_fail": True,
            "continue_on_pending_apply": True,
        },
        "allowed_subagents": sorted(set(step_map.values())),
        "step_to_subagent": step_map,
    }
    if status.orchestrator_mode == "delegate" and status.next_subagent:
        payload["task"] = {
            "subagent_type": status.next_subagent,
            "run_in_background": False,
            "step": status.next_step,
        }
    return payload


def validate_step(
    root: Path,
    slug: str,
    proposed_step: str,
    *,
    pipeline_id: str = DEFAULT_PIPELINE_ID,
) -> tuple[bool, dict]:
    dispatch = build_dispatch(root, slug, pipeline_id=pipeline_id)
    expected = dispatch["next_step"]
    ok = expected == proposed_step
    return ok, {
        "ok": ok,
        "expected_step": expected,
        "expected_subagent": dispatch.get("next_subagent", ""),
        "proposed_step": proposed_step,
        "proposed_subagent": subagent_for_step(proposed_step, pipeline_id),
        "reason": dispatch.get("next_reason", ""),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pipeline-dispatch")
    parser.add_argument("slug", nargs="?")
    parser.add_argument("--json", action="store_true", help="JSON output (default)")
    parser.add_argument("--root", default=".", type=Path)
    parser.add_argument(
        "--validate",
        metavar="STEP",
        help="Exit 0 only if STEP matches the canonical next step",
    )
    parser.add_argument(
        "--validate-subagent",
        metavar="SUBAGENT",
        help="Exit 0 only if SUBAGENT matches the canonical next subagent",
    )
    parser.add_argument(
        "--pipeline",
        required=True,
        help=f"Pipeline id. Known: {', '.join(known_pipeline_ids())}",
    )
    args = parser.parse_args(argv)
    root = workspace_root(args.root)
    if not args.slug:
        parser.error("slug is required")
    slug = resolve_slug(args.slug, root)
    if slug is None:
        parser.error("не удалось определить slug")
    try:
        pipeline_id = normalize_pipeline_id(args.pipeline)
    except ValueError as exc:
        parser.error(str(exc))

    if args.validate:
        ok, detail = validate_step(root, slug, args.validate, pipeline_id=pipeline_id)
        print(json.dumps(detail, ensure_ascii=False, indent=2))
        return 0 if ok else 1

    dispatch = build_dispatch(root, slug, pipeline_id=pipeline_id)
    if args.validate_subagent:
        expected = dispatch.get("next_subagent", "")
        ok = expected == args.validate_subagent
        print(
            json.dumps(
                {
                    "ok": ok,
                    "expected_subagent": expected,
                    "proposed_subagent": args.validate_subagent,
                    "next_step": dispatch.get("next_step", ""),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0 if ok else 1

    if args.validate is None and not args.json:
        # Human-readable one-liner for orchestrator preflight.
        if dispatch["ready"]:
            print(f"{slug}: ready — {dispatch['next_reason']}")
            return 0
        if not dispatch["next_step"]:
            print(f"{slug}: stopped — {dispatch['next_reason']}")
            return 2
        agent = dispatch["next_subagent"] or "(orchestrator)"
        cont = "continue" if dispatch["must_continue"] else "pause"
        print(
            f"{slug}: {dispatch['next_step']} → {agent} "
            f"[{dispatch['orchestrator_mode']}, {cont}] — {dispatch['next_reason']}"
        )
        return 0

    print(json.dumps(dispatch, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

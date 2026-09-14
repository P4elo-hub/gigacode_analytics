#!/usr/bin/env python3
"""Append one orchestrator step line to agent-logs/<slug>/runs/<run-id>/run-log.jsonl."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from agent_logs import resolve_run_id, resolve_slug_arg, run_log_path, utc_now_iso
from artifact_paths import workspace_root as ws_root


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slug", required=True, help="Feature slug")
    parser.add_argument("--step", required=True, help="Pipeline step, e.g. check-feature")
    parser.add_argument("--subagent", default="", help="Subagent name")
    parser.add_argument("--result", default="ok", help="ok | fail | retry")
    parser.add_argument("--block-id", default="", help="write-feature block_id if applicable")
    parser.add_argument("--attempt", type=int, default=1, help="Retry attempt number")
    parser.add_argument("--session", default="", help="CLI session id if known")
    parser.add_argument("--run-id", default="auto", help="run-NNN or auto")
    parser.add_argument("--new-run", action="store_true", help="Start new run before append")
    parser.add_argument("--note", default="", help="Optional short note")
    parser.add_argument("--workspace", type=Path, help="Workspace root")
    parser.add_argument("--pipeline", default="", help="Active pipeline id (spec, calibration, …)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = (args.workspace or ws_root()).resolve()
    slug = resolve_slug_arg(args.slug, root)
    run_id = resolve_run_id(root, slug, args.run_id, args.new_run)

    record = {
        "ts": utc_now_iso(),
        "step": args.step,
        "subagent": args.subagent or None,
        "result": args.result,
        "block_id": args.block_id or None,
        "attempt": args.attempt,
        "session": args.session or None,
        "note": args.note or None,
        "pipeline": args.pipeline or None,
    }
    record = {k: v for k, v in record.items() if v is not None}

    path = run_log_path(root, slug, run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(json.dumps({"slug": slug, "run_id": run_id, "appended": record}, ensure_ascii=False))


if __name__ == "__main__":
    main()

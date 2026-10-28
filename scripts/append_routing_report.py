#!/usr/bin/env python3
"""Persist a ROUTING_REPORT when a CLI has no SubagentStop hook."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pipeline_active_task import load_active_task_latest
from pipeline_pack import add_pack_dir_argument, apply_pack_dir_from_args, workspace_root_for_run
from routing_reports import append_report, extract_report, normalize_report, reports_index_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", default="opencode")
    parser.add_argument("--report-json", default="", help="JSON object; stdin when omitted")
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--pipeline", default=None)
    add_pack_dir_argument(parser)
    args = parser.parse_args(argv)
    apply_pack_dir_from_args(args)

    root = (args.workspace or workspace_root_for_run()).resolve()
    active = load_active_task_latest(root) or {}
    slug = str(active.get("slug") or "")
    step = str(active.get("step") or "")
    subagent = str(active.get("subagent") or step)
    pipeline_id = str(args.pipeline or active.get("pipeline") or "")
    if not slug or not step or not pipeline_id:
        raise SystemExit("active pipeline task with slug, step and pipeline is required")

    raw = args.report_json or sys.stdin.read()
    payload, extract_error = extract_report(raw)
    if payload is None:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"invalid report JSON: {extract_error or exc}") from exc
        if not isinstance(parsed, dict):
            raise SystemExit("report must be a JSON object")
        payload = parsed

    event_key = "|".join(
        (pipeline_id, slug, step, subagent, str(active.get("started_at") or ""))
    )
    report = normalize_report(
        payload,
        slug=slug,
        pipeline_id=pipeline_id,
        step=step,
        subagent=subagent,
        result=str(payload.get("result") or "ok"),
        cli=args.cli,
        event_key=event_key,
    )
    stored, appended = append_report(
        reports_index_path(root, slug, pipeline_id),
        report,
    )
    print(json.dumps({"appended": appended, "report": stored}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

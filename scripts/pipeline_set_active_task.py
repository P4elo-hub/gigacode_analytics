#!/usr/bin/env python3
"""Mark the pipeline step about to run — read by SubagentStop hook."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from artifact_paths import resolve_slug, workspace_root
from pipeline_active_task import save_active_task
from pipeline_runtime import DEFAULT_PIPELINE_ID, known_pipeline_ids, normalize_pipeline_id


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--step", required=True)
    parser.add_argument("--subagent", required=True)
    parser.add_argument("--cli", choices=("qwen", "gigacode", "opencode"), default="qwen")
    parser.add_argument(
        "--pipeline",
        default=DEFAULT_PIPELINE_ID,
        help=f"Pipeline id (default {DEFAULT_PIPELINE_ID}). Known: {', '.join(known_pipeline_ids())}",
    )
    parser.add_argument("--session", default="")
    parser.add_argument("--workspace", type=Path, default=None)
    args = parser.parse_args()

    root = (args.workspace or workspace_root()).resolve()
    slug = resolve_slug(args.slug, root)
    if slug is None:
        raise SystemExit(f"Unknown slug: {args.slug}")
    pipeline = normalize_pipeline_id(args.pipeline)

    payload = save_active_task(
        root,
        slug=slug,
        step=args.step,
        subagent=args.subagent,
        cli=args.cli,
        pipeline=pipeline,
        session=args.session,
    )
    print(json.dumps({"saved": payload}, ensure_ascii=False))


if __name__ == "__main__":
    main()

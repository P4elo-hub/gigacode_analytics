#!/usr/bin/env python3
"""Mark the pipeline step about to run — read by SubagentStop hook."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from artifact_paths import resolve_slug, workspace_root
from pipeline_active_task import save_active_task


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--step", required=True)
    parser.add_argument("--subagent", required=True)
    parser.add_argument("--cli", choices=("qwen", "gigacode", "opencode"), default="qwen")
    parser.add_argument("--pipeline", choices=("spec", "calibration"), default="spec")
    parser.add_argument("--session", default="")
    parser.add_argument("--workspace", type=Path, default=None)
    args = parser.parse_args()

    root = (args.workspace or workspace_root()).resolve()
    slug = resolve_slug(args.slug, root)
    if slug is None:
        raise SystemExit(f"Unknown slug: {args.slug}")

    payload = save_active_task(
        root,
        slug=slug,
        step=args.step,
        subagent=args.subagent,
        cli=args.cli,
        pipeline=args.pipeline,
        session=args.session,
    )
    print(json.dumps({"saved": payload}, ensure_ascii=False))


if __name__ == "__main__":
    main()

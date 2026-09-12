#!/usr/bin/env python3
"""Prepare isolated rerun workspace from inputs.lock + context snapshot."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from artifact_paths import context_doc_path, workspace_root
from calibration_paths import (
    inputs_lock_path,
    load_calibration_manifest,
    rerun_dir,
    rerun_feature_dir,
    resolve_calibration_run_id,
    resolve_slug_arg,
    save_calibration_manifest,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slug")
    parser.add_argument("--run-id", default="auto")
    parser.add_argument("--new-cal-run", action="store_true", help="Start new calibration run")
    parser.add_argument("--workspace", type=Path)
    args = parser.parse_args()

    root = (args.workspace or workspace_root()).resolve()
    slug = resolve_slug_arg(args.slug, root)
    run_id = resolve_calibration_run_id(root, slug, args.run_id, new_run=args.new_cal_run)

    lock_path = inputs_lock_path(root, slug, run_id)
    if not lock_path.is_file():
        raise SystemExit(f"inputs.lock.json missing: {lock_path}. Run snapshot_baseline first.")

    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    rerun = rerun_dir(root, slug, run_id)
    feat = rerun_feature_dir(root, slug, run_id)
    ctx_dest = rerun / "Feature-context"
    feat.mkdir(parents=True, exist_ok=True)
    ctx_dest.mkdir(parents=True, exist_ok=True)

    ctx_src = context_doc_path(root, slug)
    if ctx_src.is_file():
        shutil.copy2(ctx_src, ctx_dest / f"{slug}.md")

    brief_path = rerun / "brief.txt"
    brief_path.write_text(lock.get("brief") or f"Benchmark rerun for {slug}\n", encoding="utf-8")

    manifest = load_calibration_manifest(root, slug)
    manifest["benchmark_prepared"] = run_id
    save_calibration_manifest(root, slug, manifest)

    print(
        json.dumps(
            {
                "slug": slug,
                "run_id": run_id,
                "rerun_feature_dir": str(feat),
                "brief": str(brief_path),
                "profile": lock.get("profile"),
                "sections": lock.get("sections"),
                "next": f"/write-feature with --part-dir {feat.parent} and brief from {brief_path}",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

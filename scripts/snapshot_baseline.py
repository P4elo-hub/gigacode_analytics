#!/usr/bin/env python3
"""Snapshot SPEC and pipeline artifacts before human review → Calibration/ baseline/."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from artifact_paths import context_doc_path, spec_path, workspace_root
from calibration_paths import (
    baseline_dir,
    baseline_spec_path,
    inputs_lock_path,
    link_agent_logs_run,
    resolve_calibration_run_id,
    resolve_slug_arg,
    save_calibration_manifest,
    SNAPSHOT_FILES,
    load_calibration_manifest,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slug")
    parser.add_argument("--run-id", default="auto")
    parser.add_argument("--new-run", action="store_true")
    parser.add_argument("--brief", default="", help="Brief text for inputs.lock (optional)")
    parser.add_argument("--profile", default="sihist")
    parser.add_argument("--sections", default="", help="Comma-separated section ids")
    parser.add_argument("--workspace", type=Path)
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> None:
    args = parse_args()
    root = (args.workspace or workspace_root()).resolve()
    slug = resolve_slug_arg(args.slug, root)
    spec = spec_path(root, slug)
    if not spec.is_file():
        raise SystemExit(f"SPEC not found: {spec}")

    run_id = resolve_calibration_run_id(root, slug, args.run_id, args.new_run)
    base = baseline_dir(root, slug, run_id)
    base.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    for label, fn in SNAPSHOT_FILES:
        src = fn(root, slug)
        if src.is_file():
            dest = base / src.name
            shutil.copy2(src, dest)
            copied.append(src.name)

    ctx = context_doc_path(root, slug)
    lock = {
        "slug": slug,
        "calibration_run_id": run_id,
        "snapshotted_at": utc_now(),
        "brief": args.brief.strip() or None,
        "profile": args.profile,
        "sections": [s.strip() for s in args.sections.split(",") if s.strip()] or None,
        "context_doc": str(ctx.relative_to(root)) if ctx.is_file() else None,
        "spec_baseline": str(baseline_spec_path(root, slug, run_id).relative_to(root)),
        **link_agent_logs_run(root, slug),
    }
    inputs_lock_path(root, slug, run_id).write_text(
        json.dumps(lock, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    manifest = load_calibration_manifest(root, slug)
    manifest["slug"] = slug
    manifest["current_run"] = run_id
    manifest["last_snapshot"] = utc_now()
    save_calibration_manifest(root, slug, manifest)

    print(
        json.dumps(
            {"slug": slug, "run_id": run_id, "baseline_dir": str(base), "copied": copied},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Copy current SPEC to Calibration gold/ (after human review)."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from artifact_paths import spec_path, workspace_root
from calibration_paths import (
    gold_dir,
    gold_spec_path,
    load_calibration_manifest,
    resolve_calibration_run_id,
    resolve_slug_arg,
    save_calibration_manifest,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slug")
    parser.add_argument("--run-id", default="auto")
    parser.add_argument("--workspace", type=Path)
    args = parser.parse_args()

    root = (args.workspace or workspace_root()).resolve()
    slug = resolve_slug_arg(args.slug, root)
    spec = spec_path(root, slug)
    if not spec.is_file():
        raise SystemExit(f"SPEC not found: {spec}")

    run_id = resolve_calibration_run_id(root, slug, args.run_id, new_run=False)
    dest_dir = gold_dir(root, slug, run_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = gold_spec_path(root, slug, run_id)
    shutil.copy2(spec, dest)

    manifest = load_calibration_manifest(root, slug)
    manifest["last_gold_sync"] = utc_now()
    save_calibration_manifest(root, slug, manifest)

    print(json.dumps({"slug": slug, "run_id": run_id, "gold": str(dest)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

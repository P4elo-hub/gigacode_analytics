#!/usr/bin/env python3
"""Serialize spec-v2 artifact parsing into a routing-state replay / golden fixture.

  PYTHONPATH=scripts python3 scripts/routing_state_replay_from_collectors.py <slug>
  PYTHONPATH=scripts python3 scripts/routing_state_replay_from_collectors.py --all
  PYTHONPATH=scripts python3 scripts/routing_state_replay_from_collectors.py --golden

`--all` writes scripts/fixtures/routing_state_replay/<slug>.json (baseline parser, no LLM).
`--golden` snapshots each spec-v2 dispatch golden case into case['routing_state'] (option B).
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from artifact_paths import list_feature_slugs, resolve_slug, workspace_root  # noqa: E402
from feature_status import FeatureStatus  # noqa: E402
from pipeline_routing_state import (  # noqa: E402
    SCHEMA_VERSION,
    default_replay_path,
    overlay_context,
    serialize_status_fields,
)
from pipeline_status import populate_status  # noqa: E402
from routing_state_baseline import apply_baseline_domain  # noqa: E402

DEFAULT_SLUGS = (
    "pipeline-viewer-smoke",
    "bph-moex-tax",
    "composite-active-order-commission",
    "og-trading-order-yield",
)
GOLDEN_SLUG = "dispatch-golden"


def snapshot(root: Path, slug: str) -> dict:
    """Etalon fields: engine exists/stale + baseline domain parse (overlay off)."""
    status = FeatureStatus(slug=slug, pipeline_id="spec-v2")
    with overlay_context(mode="off"):
        populate_status(status, root, slug, "spec-v2")
    apply_baseline_domain(status, root, slug)
    return {
        "schema_version": SCHEMA_VERSION,
        "slug": slug,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fields": serialize_status_fields(status),
    }


def write_fixture(root: Path, slug: str) -> Path:
    path = default_replay_path(root, slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot(root, slug), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def write_golden(root: Path) -> Path:
    from pipeline_dispatch_golden_test import _materialize_case

    path = root / "scripts" / "fixtures" / "dispatch_golden" / "spec-v2" / "cases.json"
    cases = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(cases, list):
        raise SystemExit(f"expected list in {path}")
    for case in cases:
        if not isinstance(case, dict):
            continue
        slug = case.get("slug") or GOLDEN_SLUG
        tmp = Path(tempfile.mkdtemp(prefix="rs-golden-"))
        try:
            _materialize_case(tmp, case)
            case["routing_state"] = snapshot(tmp, slug)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    path.write_text(json.dumps(cases, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="routing-state-replay-from-collectors")
    parser.add_argument("slug", nargs="?")
    parser.add_argument("--all", action="store_true", help="default replay slugs")
    parser.add_argument(
        "--golden",
        action="store_true",
        help="write routing_state into fixtures/dispatch_golden/spec-v2/cases.json",
    )
    parser.add_argument("--root", default=".", type=Path)
    args = parser.parse_args(argv)
    root = workspace_root(args.root)
    if args.golden:
        path = write_golden(root)
        print(path.relative_to(root))
        return 0
    if args.all:
        slugs = [item for item in DEFAULT_SLUGS if resolve_slug(item, root)]
    elif args.slug:
        slug = resolve_slug(args.slug, root)
        if slug is None:
            print("не удалось определить slug", file=sys.stderr)
            return 2
        slugs = [slug]
    else:
        parser.error("pass a slug, --all, or --golden")
        return 2
    known = set(list_feature_slugs(root))
    for slug in slugs:
        if known and slug not in known:
            print(f"skip unknown slug: {slug}", file=sys.stderr)
            continue
        path = write_fixture(root, slug)
        print(path.relative_to(root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

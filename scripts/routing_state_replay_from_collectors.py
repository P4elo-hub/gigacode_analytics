#!/usr/bin/env python3
"""Serialize spec collector status fields into a routing-state replay fixture.

  PYTHONPATH=scripts python3 scripts/routing_state_replay_from_collectors.py <slug>
  PYTHONPATH=scripts python3 scripts/routing_state_replay_from_collectors.py --all

Writes scripts/fixtures/routing_state_replay/<slug>.json (collectors-first, no LLM).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from artifact_paths import list_feature_slugs, resolve_slug, workspace_root  # noqa: E402
from feature_status import build_status_fields  # noqa: E402
from pipeline_routing_state import (  # noqa: E402
    SCHEMA_VERSION,
    default_replay_path,
    overlay_context,
    serialize_status_fields,
)

DEFAULT_SLUGS = (
    "pipeline-viewer-smoke",
    "bph-moex-tax",
    "composite-active-order-commission",
    "og-trading-order-yield",
)


def snapshot(root: Path, slug: str) -> dict:
    with overlay_context(mode="off"):
        status = build_status_fields(root, slug, "spec")
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="routing-state-replay-from-collectors")
    parser.add_argument("slug", nargs="?")
    parser.add_argument("--all", action="store_true", help="default Phase 11 slugs")
    parser.add_argument("--root", default=".", type=Path)
    args = parser.parse_args(argv)
    root = workspace_root(args.root)
    if args.all:
        slugs = [item for item in DEFAULT_SLUGS if resolve_slug(item, root)]
    elif args.slug:
        slug = resolve_slug(args.slug, root)
        if slug is None:
            print("не удалось определить slug", file=sys.stderr)
            return 2
        slugs = [slug]
    else:
        parser.error("pass a slug or --all")
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

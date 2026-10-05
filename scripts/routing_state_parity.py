#!/usr/bin/env python3
"""Compare spec baseline parse (A) vs routing-state overlay (B).

Live spec dispatch is overlay (Phase 12). Mode A collectors are gone.
`--replay` remains the CI drift check vs scripts/routing_state_baseline.py.

  PYTHONPATH=scripts python3 scripts/routing_state_parity.py <slug>
  PYTHONPATH=scripts python3 scripts/routing_state_parity.py <slug> --json
  PYTHONPATH=scripts python3 scripts/routing_state_parity.py <slug> --strict
  PYTHONPATH=scripts python3 scripts/routing_state_parity.py <slug> --replay path.json
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from artifact_paths import resolve_slug, workspace_root  # noqa: E402
from feature_status import FeatureStatus  # noqa: E402
from pipeline_dispatch import build_dispatch  # noqa: E402
from pipeline_routing_state import (  # noqa: E402
    CHALLENGES_KEYS,
    SCHEMA_VERSION,
    STATUS_OVERLAY_FIELDS,
    default_replay_path,
    overlay_context,
    routing_state_path,
    serialize_status_fields,
)
from pipeline_status import populate_status  # noqa: E402
from routing_state_baseline import apply_baseline_domain  # noqa: E402

DISPATCH_KEYS = (
    "next_step",
    "next_subagent",
    "orchestrator_mode",
    "ready",
    "must_continue",
)


def _challenges_dict(status) -> dict:
    ch = getattr(status, "challenges", None)
    return {key: int(getattr(ch, key, 0) or 0) if ch is not None else 0 for key in CHALLENGES_KEYS}


def _field_value(status, field: str):
    if field == "challenges":
        return _challenges_dict(status)
    value = getattr(status, field, None)
    if isinstance(value, list):
        return list(value)
    return value


def _equal(left, right) -> bool:
    return json.dumps(left, sort_keys=True, default=str) == json.dumps(right, sort_keys=True, default=str)


def _resolve_replay(root: Path, slug: str, replay: Path | None) -> Path | None:
    if replay is not None:
        return replay
    fixture = default_replay_path(root, slug)
    if fixture.is_file():
        return fixture
    live = routing_state_path(root, slug)
    if live.is_file():
        return live
    return None


def _baseline_status(root: Path, slug: str):
    status = FeatureStatus(slug=slug, pipeline_id="spec-v2")
    with overlay_context(mode="off"):
        populate_status(status, root, slug, "spec-v2")
    apply_baseline_domain(status, root, slug)
    return status


def _dispatch_from_payload(root: Path, slug: str, payload: dict) -> dict:
    tmp = Path(tempfile.mkdtemp(prefix="rs-parity-"))
    path = tmp / "replay.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    try:
        with overlay_context(mode="on", replay=path):
            return build_dispatch(root, slug, "spec-v2")
    finally:
        path.unlink(missing_ok=True)
        tmp.rmdir()


def compare(root: Path, slug: str, *, replay: Path | None = None) -> dict:
    analyzer_path = _resolve_replay(root, slug, replay)
    status_a = _baseline_status(root, slug)
    payload_a = {
        "schema_version": SCHEMA_VERSION,
        "slug": slug,
        "fields": serialize_status_fields(status_a),
    }
    dispatch_a = _dispatch_from_payload(root, slug, payload_a)

    if analyzer_path is not None and analyzer_path.is_file():
        with overlay_context(mode="on", replay=analyzer_path):
            status_b = FeatureStatus(slug=slug, pipeline_id="spec-v2")
            populate_status(status_b, root, slug, "spec-v2")
            dispatch_b = build_dispatch(root, slug, "spec-v2")
        load_error = None
    else:
        status_b = status_a
        dispatch_b = dispatch_a
        load_error = "missing"

    field_rows = []
    fields_match = load_error is None
    for field in STATUS_OVERLAY_FIELDS:
        left = _field_value(status_a, field)
        right = _field_value(status_b, field) if load_error is None else None
        ok = load_error is None and _equal(left, right)
        if not ok:
            fields_match = False
        field_rows.append({"field": field, "collector": left, "analyzer": right, "match": ok})

    dispatch_diff = {}
    dispatch_match = True
    for key in DISPATCH_KEYS:
        left = dispatch_a.get(key)
        right = dispatch_b.get(key) if load_error is None else None
        same = load_error is None and left == right
        if not same:
            dispatch_match = False
            dispatch_diff[key] = {"collector": left, "analyzer": right}
    match = fields_match and dispatch_match and load_error is None
    rel = None
    if analyzer_path is not None and analyzer_path.is_file():
        try:
            rel = str(analyzer_path.resolve().relative_to(root.resolve()))
        except ValueError:
            rel = str(analyzer_path)
    return {
        "slug": slug,
        "routing_state": rel,
        "load_error": load_error,
        "match": match,
        "fields_match": fields_match,
        "dispatch_match": dispatch_match,
        "collector_dispatch": {key: dispatch_a.get(key) for key in DISPATCH_KEYS},
        "analyzer_dispatch": {key: dispatch_b.get(key) for key in DISPATCH_KEYS} if load_error is None else None,
        "dispatch_diff": dispatch_diff,
        "fields": field_rows,
    }


def format_report(report: dict) -> str:
    lines = [
        f"slug: {report['slug']}",
        f"routing-state: {report['routing_state'] or 'ABSENT'}",
        f"match: {'PASS' if report['match'] else 'DIFF'}",
        "",
    ]
    if report.get("load_error"):
        lines.append(f"load: {report['load_error']}")
        lines.append("Нет JSON — analyze-routing или --replay scripts/fixtures/routing_state_replay/<slug>.json")
        lines.append("")
    col = report["collector_dispatch"]
    ana = report.get("analyzer_dispatch") or {}
    lines.append("dispatch A (baseline parse) vs B (overlay):")
    for key in DISPATCH_KEYS:
        mark = "ok" if key not in report["dispatch_diff"] else "DIFF"
        right = ana.get(key, "—") if ana else "—"
        lines.append(f"  {key}: collector={col.get(key)!r} analyzer={right!r}  [{mark}]")
    lines.append("")
    lines.append("fields:")
    for row in report["fields"]:
        mark = "ok" if row["match"] else "DIFF"
        lines.append(
            f"  {row['field']}: collector={row['collector']!r} analyzer={row['analyzer']!r}  [{mark}]"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="routing-state-parity")
    parser.add_argument("slug")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true", help="exit 1 on mismatch")
    parser.add_argument("--replay", type=Path, help="routing-state JSON (CI, no LLM)")
    parser.add_argument("--root", default=".", type=Path)
    args = parser.parse_args(argv)
    root = workspace_root(args.root)
    slug = resolve_slug(args.slug, root)
    if slug is None:
        print("не удалось определить slug", file=sys.stderr)
        return 2
    replay = args.replay.expanduser().resolve() if args.replay else None
    report = compare(root, slug, replay=replay)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    else:
        print(format_report(report))
    if args.strict and not report["match"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

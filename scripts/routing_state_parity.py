#!/usr/bin/env python3
"""Compare spec collectors vs routing-state.json fields.

Phase 10 stub: prints a field report. Spec dispatch still uses collectors.
Phase 11: overlay JSON into spec populate_status and diff next_step.

  PYTHONPATH=scripts python3 scripts/routing_state_parity.py <slug>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from artifact_paths import resolve_slug, workspace_root  # noqa: E402
from feature_status import build_status_fields  # noqa: E402
from pipeline_dispatch import build_dispatch  # noqa: E402
from pipeline_routing_state import (  # noqa: E402
    STATUS_OVERLAY_FIELDS,
    load_routing_state,
    routing_state_path,
)

PHASE11_TODO = (
    "TODO Phase 11: wire overlay into spec populate_status and diff "
    "collector vs analyzer next_step"
)


def _flag(value) -> str:
    if isinstance(value, list):
        return "true" if value else "false"
    if isinstance(value, bool):
        return "true" if value else "false"
    if value in (None, "", 0):
        return "false" if not value else str(value)
    return "true" if value else "false"


def _collector_value(status, field: str):
    if field == "challenges":
        ch = getattr(status, "challenges", None)
        return getattr(ch, "open", 0) if ch is not None else 0
    return getattr(status, field, None)


def _analyzer_value(fields: dict, field: str):
    if field == "challenges":
        raw = fields.get("challenges") or {}
        if isinstance(raw, dict):
            return raw.get("open", 0)
        return raw
    return fields.get(field)


def compare(root: Path, slug: str) -> dict:
    collector_status = build_status_fields(root, slug, "spec")
    collector_dispatch = build_dispatch(root, slug, "spec")
    path = routing_state_path(root, slug)
    payload, error = load_routing_state(path, slug=slug)
    fields = (payload or {}).get("fields") if payload else None
    rows: list[dict] = []
    for field in STATUS_OVERLAY_FIELDS:
        left = _collector_value(collector_status, field)
        right = _analyzer_value(fields or {}, field) if isinstance(fields, dict) else None
        rows.append(
            {
                "field": field,
                "collector": _flag(left),
                "analyzer": _flag(right) if fields is not None else "missing",
                "match": fields is not None and _flag(left) == _flag(right),
            }
        )
    return {
        "slug": slug,
        "routing_state": str(path.relative_to(root)) if path.is_file() else None,
        "load_error": error or None,
        "collector_next_step": collector_dispatch.get("next_step") or "",
        "analyzer_next_step": None,
        "todo": PHASE11_TODO,
        "fields": rows,
    }


def format_report(report: dict) -> str:
    lines = [
        f"slug: {report['slug']}",
        f"routing-state: {report['routing_state'] or 'ABSENT'}",
        f"collector next_step: {report['collector_next_step'] or '—'}",
        f"analyzer next_step: n/a ({report['todo']})",
        "",
    ]
    if not report.get("routing_state"):
        lines.append("Нет JSON — сначала analyze-routing, затем сравни поля.")
        return "\n".join(lines) + "\n"
    if report.get("load_error") and report["load_error"] != "missing":
        lines.append(f"load: {report['load_error']}")
        lines.append("")
    for row in report["fields"]:
        mark = "ok" if row["match"] else "DIFF"
        lines.append(
            f"{row['field']}: collector={row['collector']} analyzer={row['analyzer']}  [{mark}]"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="routing-state-parity")
    parser.add_argument("slug")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--root", default=".", type=Path)
    args = parser.parse_args(argv)
    root = workspace_root(args.root)
    slug = resolve_slug(args.slug, root)
    if slug is None:
        print("не удалось определить slug", file=sys.stderr)
        return 2
    report = compare(root, slug)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

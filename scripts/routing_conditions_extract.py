#!/usr/bin/env python3
"""One-shot / check: backfill coverage of dispatch when: vs edge_conditions.

Phase 13 bootstrap. After the spec pack has edge_conditions, use --check.
Do not overwrite hand-patched status_fields. New missing when: get stub expr.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pipeline_edge_conditions import edge_conditions_map
from pipeline_pack import load_pack, repo_root
from pipeline_predicates import core_predicate_names
from pipeline_routing_codegen import apply_plan, planned_changes


def missing_when(pipeline_id: str, root: Path | None = None) -> list[str]:
    pack = load_pack(pipeline_id, root)
    conditions = edge_conditions_map(pipeline_id, root)
    core = core_predicate_names(pipeline_id)
    missing: list[str] = []
    for rule in (pack.get("dispatch") or {}).get("rules") or []:
        if not isinstance(rule, dict):
            continue
        when = rule.get("when")
        if when and when not in conditions and when not in core:
            missing.append(str(when))
    return missing


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pipeline", required=True)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write", action="store_true", help="Append stub edge_conditions for missing when:")
    parser.add_argument("--root", type=Path, default=None)
    args = parser.parse_args(argv)
    root = args.root or repo_root()
    gaps = missing_when(args.pipeline, root)
    if args.check or not args.write:
        if gaps:
            print(f"{args.pipeline}: missing edge_conditions for {gaps}", file=sys.stderr)
            return 1
        print(f"{args.pipeline}: dispatch when: covered by edge_conditions or core")
        return 0
    pack = load_pack(args.pipeline, root)
    fake_edges = []
    for rule in (pack.get("dispatch") or {}).get("rules") or []:
        if not isinstance(rule, dict) or not rule.get("when"):
            continue
        if rule["when"] in edge_conditions_map(args.pipeline, root):
            continue
        fake_edges.append({"from": "_", "to": rule.get("next") or "done", "condition": rule["when"]})
    plan = planned_changes(args.pipeline, root, fake_edges)
    for name, spec in plan["new_conditions"].items():
        match = next(
            (rule for rule in (pack.get("dispatch") or {}).get("rules") or [] if rule.get("when") == name),
            None,
        )
        if match:
            spec["dispatch"] = {
                "priority": int(match["priority"]),
                "next": match.get("next"),
            }
            if match.get("outcome"):
                spec["dispatch"]["outcome"] = match["outcome"]
    notes = apply_plan(plan, write=True)
    for note in notes:
        print(note)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

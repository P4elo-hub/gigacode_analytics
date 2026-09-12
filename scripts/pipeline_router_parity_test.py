#!/usr/bin/env python3
"""Dual-run parity: legacy choose_next_step vs compiled pipeline_router."""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

import pipeline_dispatch_golden_test as golden  # noqa: E402
from feature_status import FeatureStatus, _choose_next_step_legacy, build_status_fields  # noqa: E402
from pipeline_router import apply_router_decision  # noqa: E402

COMPARE_KEYS = (
    "ready",
    "next_step",
    "next_subagent",
    "orchestrator_mode",
    "must_continue",
)


def _status_subset(status: FeatureStatus) -> dict:
    data = asdict(status)
    return {key: data[key] for key in COMPARE_KEYS}


def run_case(case: dict) -> tuple[bool, str]:
    case_id = case.get("id") or "unnamed"
    slug = case.get("slug") or golden.SLUG
    tmp = Path(tempfile.mkdtemp(prefix="router-parity-"))
    try:
        golden._write_tree(tmp, case.get("files") or {})
        golden._apply_post_setup(tmp, case)

        legacy = build_status_fields(tmp, slug)
        _choose_next_step_legacy(legacy, root=tmp)

        routed = build_status_fields(tmp, slug)
        apply_router_decision(routed, tmp, slug)

        legacy_view = _status_subset(legacy)
        routed_view = _status_subset(routed)
        mismatches: list[str] = []
        for key in COMPARE_KEYS:
            if legacy_view.get(key) != routed_view.get(key):
                mismatches.append(
                    f"{key}: legacy={legacy_view.get(key)!r} router={routed_view.get(key)!r}"
                )
        if case.get("expect_reason_contains"):
            needle = case["expect_reason_contains"]
            if needle not in (routed.next_reason or ""):
                mismatches.append(f"router next_reason missing {needle!r}: {routed.next_reason!r}")
            if needle not in (legacy.next_reason or ""):
                mismatches.append(f"legacy next_reason missing {needle!r}: {legacy.next_reason!r}")
        if mismatches:
            return False, "; ".join(mismatches)
        return True, "parity ok"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pipeline-router-parity-test")
    parser.add_argument("--case", metavar="ID", help="Run single golden case id")
    parser.add_argument("--list", action="store_true", help="List case ids")
    args = parser.parse_args(argv)

    cases = golden._load_cases()
    if args.list:
        for case in cases:
            print(case.get("id", "?"))
        return 0

    if args.case:
        cases = [c for c in cases if c.get("id") == args.case]
        if not cases:
            print(f"Unknown case: {args.case}", file=sys.stderr)
            return 2

    if not cases:
        print("No golden fixtures", file=sys.stderr)
        return 2

    failed: list[str] = []
    for case in cases:
        case_id = case.get("id") or "unnamed"
        try:
            ok, detail = run_case(case)
        except Exception as exc:
            ok, detail = False, str(exc)
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {case_id}" + (f" — {detail}" if detail else ""))
        if not ok:
            failed.append(case_id)

    print("-" * 60)
    print(f"Result: {len(cases) - len(failed)}/{len(cases)} passed")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())

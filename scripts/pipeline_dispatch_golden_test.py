#!/usr/bin/env python3
"""Golden tests: build_dispatch() on isolated artifact fixtures (compiled router contract)."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

from pipeline_common import parse_run_log_ts  # noqa: E402
from pipeline_dispatch import build_dispatch  # noqa: E402
from pipeline_golden_coverage import (  # noqa: E402
    coverage_detail,
    live_golden_coverage_problems,
)
from pipeline_pack import discover_pipeline_ids, repo_root  # noqa: E402

FIXTURES_DIR = SCRIPTS / "fixtures" / "dispatch_golden"
SLUG = "dispatch-golden"
DEFAULT_PIPELINE = "spec"

DISPATCH_KEYS = (
    "ready",
    "next_step",
    "next_subagent",
    "orchestrator_mode",
    "must_continue",
)
OPTIONAL_EXPECT_KEYS = (
    "dispatch_supported",
    "pipeline_id",
)


@dataclass
class Check:
    case_id: str
    ok: bool
    detail: str = ""


@dataclass
class Report:
    checks: list[Check] = field(default_factory=list)

    def add(self, case_id: str, ok: bool, detail: str = "") -> None:
        self.checks.append(Check(case_id, ok, detail))

    @property
    def passed(self) -> bool:
        return all(c.ok for c in self.checks)

    def print_report(self) -> None:
        print("=" * 60)
        print("Pipeline dispatch golden tests (per-pipeline packs)")
        print("=" * 60)
        for c in self.checks:
            mark = "PASS" if c.ok else "FAIL"
            line = f"[{mark}] {c.case_id}"
            if c.detail:
                line += f"\n       {c.detail}"
            print(line)
        print("-" * 60)
        n_ok = sum(1 for c in self.checks if c.ok)
        print(f"Result: {n_ok}/{len(self.checks)} passed")
        print("=" * 60)


def _write_tree(root: Path, files: dict[str, str]) -> None:
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _touch_pair(
    root: Path,
    older: str,
    newer: str,
    *,
    base: float,
    delta_sec: float = 120.0,
) -> None:
    """Set `older` mtime to base and `newer` mtime = base + delta."""
    older_path = root / older
    newer_path = root / newer
    if not older_path.is_file() or not newer_path.is_file():
        raise FileNotFoundError(f"touch_pair missing: {older!r} or {newer!r}")
    os.utime(older_path, (base, base))
    os.utime(newer_path, (base + delta_sec, base + delta_sec))


def _write_run_log(root: Path, slug: str, entries: list[dict]) -> None:
    run_id = "run-001"
    logs = root / "agent-logs" / slug
    run_dir = logs / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "slug": slug,
        "current_run": run_id,
        "runs": [run_id],
        "cli": "golden-test",
    }
    (logs / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    lines = [json.dumps(row, ensure_ascii=False) for row in entries]
    (run_dir / "run-log.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _align_spec_before_run_log(root: Path, slug: str, run_log: list[dict]) -> None:
    spec_rel = f"Feature-writing/{slug}/{slug}.md"
    spec_file = root / spec_rel
    if not spec_file.is_file() or not run_log:
        return
    ts = run_log[0].get("ts")
    if not ts:
        return
    before = parse_run_log_ts(ts) - 120.0
    os.utime(spec_file, (before, before))


def _apply_post_setup(root: Path, case: dict) -> None:
    slug = case.get("slug") or SLUG
    touch_base = time.time() - 7200
    for pair in case.get("touch_after") or []:
        if len(pair) != 2:
            raise ValueError(f"touch_after must be [older, newer]: {pair!r}")
        _touch_pair(root, pair[0], pair[1], base=touch_base)
    if case.get("run_log"):
        _write_run_log(root, slug, case["run_log"])
        if case.get("align_spec_before_run_log", True):
            _align_spec_before_run_log(root, slug, case["run_log"])


def _dispatch_subset(dispatch: dict) -> dict:
    out = {key: dispatch.get(key) for key in DISPATCH_KEYS}
    out["ready"] = bool(dispatch.get("ready"))
    out["must_continue"] = bool(dispatch.get("must_continue"))
    return out


def _load_cases() -> list[dict]:
    cases: list[dict] = []
    if not FIXTURES_DIR.is_dir():
        return cases
    for pipe_dir in sorted(p for p in FIXTURES_DIR.iterdir() if p.is_dir()):
        path = pipe_dir / "cases.json"
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        rows = data if isinstance(data, list) else [data]
        for row in rows:
            if not isinstance(row, dict):
                continue
            row.setdefault("pipeline_id", pipe_dir.name)
            cases.append(row)
    legacy = FIXTURES_DIR / "cases.json"
    if legacy.is_file():
        data = json.loads(legacy.read_text(encoding="utf-8"))
        rows = data if isinstance(data, list) else [data]
        for row in rows:
            if isinstance(row, dict):
                row.setdefault("pipeline_id", DEFAULT_PIPELINE)
                cases.append(row)
    return cases


def _inject_routing_state(root: Path, case: dict) -> None:
    """Option B: write case['routing_state'] after files/mtimes so JSON is newest."""
    payload = case.get("routing_state")
    if payload is None:
        return
    slug = case.get("slug") or SLUG
    rel = f"Feature-writing/{slug}/{slug}-routing-state.json"
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, (dict, list)):
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        path.write_text(str(payload), encoding="utf-8")
    newest = time.time() + 60
    os.utime(path, (newest, newest))


def _materialize_case(root: Path, case: dict) -> None:
    _write_tree(root, case.get("files") or {})
    _apply_post_setup(root, case)


def run_case(case: dict) -> tuple[bool, str]:
    case_id = case.get("id") or "unnamed"
    slug = case.get("slug") or SLUG
    expect = case.get("expect") or {}
    tmp = Path(tempfile.mkdtemp(prefix="dispatch-golden-"))
    try:
        _materialize_case(tmp, case)
        _inject_routing_state(tmp, case)
        dispatch = build_dispatch(tmp, slug, case.get("pipeline_id") or DEFAULT_PIPELINE)
        actual = _dispatch_subset(dispatch)
        mismatches: list[str] = []
        for key, expected in expect.items():
            if key in DISPATCH_KEYS:
                if actual.get(key) != expected:
                    mismatches.append(f"{key}: expected {expected!r}, got {actual.get(key)!r}")
            elif key in OPTIONAL_EXPECT_KEYS:
                if dispatch.get(key) != expected:
                    mismatches.append(f"{key}: expected {expected!r}, got {dispatch.get(key)!r}")
        if case.get("expect_reason_contains"):
            reason = dispatch.get("next_reason") or ""
            needle = case["expect_reason_contains"]
            if needle not in reason:
                mismatches.append(f"next_reason missing {needle!r}: {reason!r}")
        if mismatches:
            return False, "; ".join(mismatches)
        return True, json.dumps(actual, ensure_ascii=False)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pipeline-dispatch-golden-test")
    parser.add_argument("--case", metavar="ID", help="Run single case id")
    parser.add_argument("--list", action="store_true", help="List case ids")
    args = parser.parse_args(argv)

    cases = _load_cases()
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
        print(f"No fixtures in {FIXTURES_DIR}", file=sys.stderr)
        return 2

    report = Report()
    for case in cases:
        case_id = case.get("id") or "unnamed"
        try:
            ok, detail = run_case(case)
        except Exception as exc:
            ok, detail = False, str(exc)
        report.add(case_id, ok, detail)

    if not args.case:
        try:
            pipeline_ids = discover_pipeline_ids(repo_root())
            problems = live_golden_coverage_problems()
            report.add("coverage:packs", not problems, coverage_detail(pipeline_ids, problems))
        except Exception as exc:
            report.add("coverage:packs", False, str(exc))

    report.print_report()
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

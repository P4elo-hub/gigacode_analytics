#!/usr/bin/env python3
"""Pack ↔ dispatch-golden coverage (Phase 9). Isolated + live workspace."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from pipeline_golden_coverage import (  # noqa: E402
    SPEC_MIN_CASES,
    SPEC_PIPELINE_ID,
    SPEC_REQUIRED_CASE_IDS,
    golden_coverage_problems,
    live_golden_coverage_problems,
)
from pipeline_pack import discover_pipeline_ids, repo_root  # noqa: E402
from pipeline_pack_authoring import init_pack_golden_hints  # noqa: E402


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _cases(folder: Path, pipeline_id: str, ids: list[str]) -> None:
    payload = [{"id": case_id} for case_id in ids]
    _write(folder / pipeline_id / "cases.json", json.dumps(payload) + "\n")


class GoldenCoveragePolicyTest(unittest.TestCase):
    def test_live_packs_are_covered(self) -> None:
        pipeline_ids = discover_pipeline_ids(repo_root())
        problems = live_golden_coverage_problems()
        self.assertEqual(problems, [], problems)
        self.assertIn("spec", pipeline_ids)
        self.assertIn("calibration", pipeline_ids)

    def test_missing_pack_fails_without_waiver(self) -> None:
        with tempfile.TemporaryDirectory(prefix="golden-cov-") as tmp:
            fixtures = Path(tmp) / "golden"
            fixtures.mkdir()
            problems = golden_coverage_problems(
                pipeline_ids=["demo-orch"],
                fixtures_dir=fixtures,
                dispatch_supported_ids=set(),
            )
        self.assertTrue(any("demo-orch" in item and "WAIVER.md" in item for item in problems), problems)

    def test_waiver_ok_for_no_dispatch(self) -> None:
        with tempfile.TemporaryDirectory(prefix="golden-cov-") as tmp:
            fixtures = Path(tmp) / "golden"
            _write(fixtures / "demo-orch" / "WAIVER.md", "orchestrator_only — no router\n")
            problems = golden_coverage_problems(
                pipeline_ids=["demo-orch"],
                fixtures_dir=fixtures,
                dispatch_supported_ids=set(),
            )
        self.assertEqual(problems, [])

    def test_waiver_rejected_for_dispatch_supported(self) -> None:
        with tempfile.TemporaryDirectory(prefix="golden-cov-") as tmp:
            fixtures = Path(tmp) / "golden"
            _write(fixtures / "demo-dispatch" / "WAIVER.md", "should not count\n")
            problems = golden_coverage_problems(
                pipeline_ids=["demo-dispatch"],
                fixtures_dir=fixtures,
                dispatch_supported_ids={"demo-dispatch"},
            )
        self.assertTrue(any("WAIVER.md is only for no-dispatch" in item for item in problems), problems)

    def test_orphan_golden_dir_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="golden-cov-") as tmp:
            fixtures = Path(tmp) / "golden"
            _cases(fixtures, "ghost", ["01-orphan"])
            problems = golden_coverage_problems(
                pipeline_ids=["spec"],
                fixtures_dir=fixtures,
                dispatch_supported_ids={"spec"},
            )
        self.assertTrue(any("ghost" in item and "no pack" in item for item in problems), problems)

    def test_dispatch_supported_needs_one_case(self) -> None:
        with tempfile.TemporaryDirectory(prefix="golden-cov-") as tmp:
            fixtures = Path(tmp) / "golden"
            fixtures.mkdir()
            problems = golden_coverage_problems(
                pipeline_ids=["demo-dispatch"],
                fixtures_dir=fixtures,
                dispatch_supported_ids={"demo-dispatch"},
            )
        self.assertTrue(any("dispatch_supported requires" in item for item in problems), problems)

        with tempfile.TemporaryDirectory(prefix="golden-cov-") as tmp:
            fixtures = Path(tmp) / "golden"
            _cases(fixtures, "demo-dispatch", ["01-not-has-main"])
            problems = golden_coverage_problems(
                pipeline_ids=["demo-dispatch"],
                fixtures_dir=fixtures,
                dispatch_supported_ids={"demo-dispatch"},
            )
        self.assertEqual(problems, [])

    def test_spec_floor_keeps_required_ids(self) -> None:
        with tempfile.TemporaryDirectory(prefix="golden-cov-") as tmp:
            fixtures = Path(tmp) / "golden"
            _cases(fixtures, SPEC_PIPELINE_ID, sorted(SPEC_REQUIRED_CASE_IDS)[: SPEC_MIN_CASES - 1])
            problems = golden_coverage_problems(
                pipeline_ids=[SPEC_PIPELINE_ID],
                fixtures_dir=fixtures,
                dispatch_supported_ids={SPEC_PIPELINE_ID},
            )
        self.assertTrue(any("do not shrink" in item or "missing required" in item for item in problems), problems)

    def test_spec_waiver_not_allowed_even_without_dispatch(self) -> None:
        with tempfile.TemporaryDirectory(prefix="golden-cov-") as tmp:
            fixtures = Path(tmp) / "golden"
            _write(fixtures / SPEC_PIPELINE_ID / "WAIVER.md", "should not cover spec\n")
            problems = golden_coverage_problems(
                pipeline_ids=[SPEC_PIPELINE_ID],
                fixtures_dir=fixtures,
                dispatch_supported_ids=set(),
            )
        self.assertTrue(
            any("WAIVER.md is not allowed" in item for item in problems),
            problems,
        )

    def test_invalid_cases_json_is_problem_not_crash(self) -> None:
        with tempfile.TemporaryDirectory(prefix="golden-cov-") as tmp:
            fixtures = Path(tmp) / "golden"
            _write(fixtures / "demo-dispatch" / "cases.json", "{not json")
            problems = golden_coverage_problems(
                pipeline_ids=["demo-dispatch"],
                fixtures_dir=fixtures,
                dispatch_supported_ids={"demo-dispatch"},
            )
        self.assertTrue(any("cannot read" in item for item in problems), problems)

    def test_full_dispatch_init_hints_golden(self) -> None:
        hints = init_pack_golden_hints("demo-dispatch", "full-dispatch")
        joined = "\n".join(hints)
        self.assertIn("demo-dispatch", joined)
        self.assertIn("cases.json", joined)
        self.assertIn("COVERAGE.md", joined)

    def test_no_dispatch_init_hints_waiver(self) -> None:
        hints = init_pack_golden_hints("demo-orch", "orchestrator-only")
        joined = "\n".join(hints)
        self.assertIn("WAIVER.md", joined)


if __name__ == "__main__":
    unittest.main()

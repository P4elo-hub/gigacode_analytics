#!/usr/bin/env python3
"""Live helpers: prepare → tick → apply_fixture (no --variant) → tick matches expect."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

LAB = Path(__file__).resolve().parent
sys.path.insert(0, str(LAB))
sys.path.insert(0, str(LAB.parent / "scripts"))

from apply_fixture import apply_fixture, cursor_file, hook_input_for  # noqa: E402
from pipeline_after_subagent import after_subagent  # noqa: E402
from pipeline_pack import reset_pack_dir, set_pack_dir  # noqa: E402
from run import PACK_DIR, PIPELINE_ID, compare_scenario, live_tick, prepare_scenario  # noqa: E402

LIVE_IDS = (
    "lab-01-retry-same-step",
    "lab-03-challenge-not-check",
    "lab-06-pending-apply-beats-check",
    "lab-08-ch-apply-leftover-gaps",
)


class LiveTickCriterionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="lab-live-"))
        (self.tmp / "Feature-writing").mkdir()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _drive(self, scenario_id: str) -> dict:
        prepare_scenario(scenario_id, workspace=self.tmp)
        for _ in range(8):
            tick = live_tick(scenario_id, workspace=self.tmp)
            if tick["gate"] != "task":
                return tick
            launch = tick["launch"]
            applied = apply_fixture(
                scenario_id,
                launch["step"],
                workspace=self.tmp,
            )
            self.assertEqual(applied["step"], launch["step"])
            set_pack_dir(PACK_DIR, PIPELINE_ID)
            try:
                after_subagent(
                    self.tmp,
                    hook_input_for(
                        applied["step"],
                        applied["variant"],
                        last_message=applied.get("last_message") or "",
                        subagent=applied["subagent"],
                    ),
                    cli="qwen",
                    pipeline_arg=PIPELINE_ID,
                )
            finally:
                reset_pack_dir()
        self.fail(f"{scenario_id}: did not stop")

    def test_three_graph_scenarios_match_expect(self) -> None:
        for scenario_id in LIVE_IDS:
            with self.subTest(scenario_id=scenario_id):
                last = self._drive(scenario_id)
                self.assertEqual(last["gate"], "stop")
                compared = compare_scenario(scenario_id, workspace=self.tmp)
                self.assertTrue(compared["matched_expect_path"])

    def test_lab_03_last_task_is_challenge_resolver(self) -> None:
        last = self._drive("lab-03-challenge-not-check")
        path = last["path"]
        self.assertEqual(path[-1]["step"], "resolve-challenges")
        self.assertNotIn("check-feature", [row["step"] for row in path])

    def test_lab_01_ask_parent_text_goes_to_analyze_routing(self) -> None:
        last = self._drive("lab-01-retry-same-step")
        steps = [row["step"] for row in last["path"]]
        self.assertEqual(steps[-2], "challenge-feature")
        self.assertEqual(steps[-1], "analyze-routing")

    def test_lab_08_leftover_gap_does_not_steal_to_resolve_gaps(self) -> None:
        last = self._drive("lab-08-ch-apply-leftover-gaps")
        steps = [row["step"] for row in last["path"]]
        self.assertNotIn("resolve-gaps", steps)
        self.assertIn("resolve-challenges", steps)

    def test_cursor_advances_only_when_variant_omitted(self) -> None:
        prepare_scenario("lab-06-pending-apply-beats-check", workspace=self.tmp)
        first = live_tick("lab-06-pending-apply-beats-check", workspace=self.tmp)
        apply_fixture(
            "lab-06-pending-apply-beats-check",
            first["launch"]["step"],
            workspace=self.tmp,
        )
        cursor = json.loads(
            cursor_file(self.tmp, "lab-06-pending-apply-beats-check").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(cursor["tick"], 1)


if __name__ == "__main__":
    unittest.main()

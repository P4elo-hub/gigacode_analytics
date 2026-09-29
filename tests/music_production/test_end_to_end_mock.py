#!/usr/bin/env python3
"""Prompt 6 acceptance scenarios over the deterministic mock orchestration."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from music_production.orchestration import Outcome
from tests.music_production.test_orchestration import Harness, fixture, knowledge_case


class Prompt6EndToEndMockTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def comparison(harness: Harness, attempt: dict) -> dict:
        value = fixture("sample-version-comparison.json", harness.track_id)
        value["edit_attempt_id"] = attempt["edit_attempt_id"]
        value["parent_version_id"] = attempt["parent_version_id"]
        value["child_version_id"] = attempt["child_version_id"]
        return value

    def test_fix_is_accepted(self) -> None:
        harness = Harness(self.root)
        _base_id, attempt = harness.reach_edit()
        harness._set("compare-versions", self.comparison(harness, attempt))

        outcome = harness.engine.run_one_step()

        self.assertEqual(outcome.outcome, Outcome.PROGRESSED)
        self.assertEqual(
            harness.engine.handlers.versions.current_version_id,
            attempt["child_version_id"],
        )

    def test_regression_is_rejected_without_switching_current(self) -> None:
        harness = Harness(self.root)
        base_id, attempt = harness.reach_edit()
        comparison = self.comparison(harness, attempt)
        comparison["outcome"] = "REJECTED"
        comparison["target_defect_resolved"] = False
        comparison["recommended_current_version_id"] = base_id
        comparison["regressions"] = [
            {
                "code": "REGRESSION",
                "severity": "MAJOR",
                "message": "mock regression",
            }
        ]
        harness._set("compare-versions", comparison)

        outcome = harness.engine.run_one_step()

        self.assertEqual(outcome.next_step, "plan-revision")
        self.assertEqual(
            harness.engine.handlers.versions.current_version_id,
            base_id,
        )

    def test_exhaustion_escalates_then_stop_pauses(self) -> None:
        harness = Harness(self.root)
        harness.reach_package_gate()
        harness.approve_package()
        harness.reach_base_gate()
        base_id = harness.select_base()
        for index in range(3):
            harness.engine.state_store.transition(
                "EDIT_COMPLETED",
                event_id=f"consume:{index}",
            )

        waiting = harness.engine.run_one_step()

        self.assertEqual(waiting.outcome, Outcome.WAITING_FOR_HUMAN)
        self.assertEqual(waiting.next_step, "revision-escalation")
        self.assertEqual(waiting.state, "REVISING")
        self.assertNotEqual(waiting.state, "PAUSED")

        stop = harness.decision(
            "decision-stop-after-exhaustion",
            "REVISION_ESCALATION",
            "STOP",
            version_id=base_id,
        )
        harness.engine.record_decision(stop)
        self.assertEqual(harness.engine.state_store.load()["state"], "REVISING")
        harness._set("capture-knowledge", knowledge_case(stop))
        paused = harness.engine.run_one_step()
        self.assertEqual(paused.executed_step, "capture-knowledge")
        self.assertEqual(paused.state, "PAUSED")
        self.assertEqual(paused.outcome, Outcome.BLOCKED)

    def test_wrong_parent_is_controlled_blocked(self) -> None:
        harness = Harness(self.root)
        base_id, attempt = harness.reach_edit()
        comparison = self.comparison(harness, attempt)
        comparison["parent_version_id"] = "foreign-parent"
        harness._set("compare-versions", comparison)

        blocked = harness.engine.run_one_step()

        self.assertEqual(blocked.outcome, Outcome.BLOCKED)
        self.assertEqual(blocked.error_code, "INVALID_VERSION_LINEAGE")
        self.assertEqual(
            harness.engine.handlers.versions.current_version_id,
            base_id,
        )
        self.assertFalse(
            harness.engine.artifacts.exists("version-comparison")
        )

    def test_closing_blocking_defects_routes_to_final_qc(self) -> None:
        harness = Harness(self.root)
        _base_id, attempt = harness.reach_edit()
        comparison = self.comparison(harness, attempt)
        comparison["remaining_defects"] = []
        harness._set("compare-versions", comparison)

        compared = harness.engine.run_one_step()
        qc = harness.engine.run_one_step()

        self.assertEqual(compared.next_step, "final-qc")
        self.assertEqual(qc.executed_step, "final-qc")
        self.assertEqual(qc.next_step, "final-approval")


if __name__ == "__main__":
    unittest.main()

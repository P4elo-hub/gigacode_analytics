"""View-model coverage for the local music track screen."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from music_production.orchestration.state_store import StateStore
from music_production.services.version_store import VersionRecord, VersionStore
from music_production.ui.engine_factory import list_track_ids, open_engine
from music_production.ui.view_model import GATE_ACTIONS, MOCK_QC_NOTICE, build_view_model
from tests.music_production.test_orchestration import NOW, Harness, fixture


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _strings(child)


class ViewModelTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_empty_runs_root(self) -> None:
        missing = self.root / "missing-runs"
        self.assertEqual(list_track_ids(missing), [])
        empty = self.root / "empty-runs"
        empty.mkdir()
        self.assertEqual(list_track_ids(empty), [])

    def test_track_snapshot_gates_and_lineage(self) -> None:
        harness = Harness(self.root)
        harness.reach_package_gate()
        package = build_view_model(open_engine(self.root, harness.track_id))
        self.assertEqual(
            set(GATE_ACTIONS),
            {
                "PACKAGE_APPROVAL",
                "BASE_SELECTION",
                "REVISION_ESCALATION",
                "FINAL_APPROVAL",
            },
        )
        self.assertEqual(package["gate"], "PACKAGE_APPROVAL")
        self.assertEqual(package["outcome"], "WAITING_FOR_HUMAN")
        self.assertEqual(
            [item["verdict"] for item in package["actions"]],
            [item[0] for item in GATE_ACTIONS["PACKAGE_APPROVAL"]],
        )
        self.assertIsNone(package["pending_status"])
        self.assertNotIn("/", json.dumps(package["references"]))

        harness.approve_package()
        harness.reach_base_gate()
        base = build_view_model(open_engine(self.root, harness.track_id))
        self.assertEqual(base["gate"], "BASE_SELECTION")
        self.assertEqual(
            [item["verdict"] for item in base["actions"]],
            [item[0] for item in GATE_ACTIONS["BASE_SELECTION"]],
        )
        self.assertTrue(base["candidates"])
        self.assertFalse(base["candidates"][0]["audio_available"])
        self.assertEqual(base["candidates"][0]["audio_block_reason"], "mock_uri")
        self.assertTrue(base["generation"]["prompt_id"])
        self.assertTrue(base["generation"]["operation"])
        self.assertIn("idempotency_key", base["generation"]["parameters"])

        base_id = harness.select_base()
        defect = fixture("sample-defect.json", harness.track_id)
        defect["version_id"] = base_id
        harness._set("diagnose-defects", defect)
        plan = fixture("sample-revision-plan.json", harness.track_id)
        plan["source_version_id"] = base_id
        harness._set("plan-revision", plan)
        self.assertEqual(harness.engine.run_one_step().executed_step, "diagnose-defects")
        self.assertEqual(harness.engine.run_one_step().executed_step, "plan-revision")
        self.assertEqual(harness.engine.run_one_step().executed_step, "execute-edit")
        revising = build_view_model(open_engine(self.root, harness.track_id))
        defect = revising["defects"][0]
        self.assertEqual(defect["start_seconds"], 125.75)
        self.assertEqual(defect["end_seconds"], 140)
        self.assertTrue(defect["diagnosis"])
        self.assertTrue(defect["preserve"])
        self.assertTrue(defect["desired_change"])
        self.assertTrue(revising["revision_plan"])
        self.assertTrue(revising["edit_attempt"])
        self.assertIn(base_id, revising["lineage"] or revising["versions"][0]["version_id"])
        child = revising["edit_attempt"]["child_version_id"]
        parent = revising["edit_attempt"]["parent_version_id"]
        by_id = {item["version_id"]: item for item in revising["versions"]}
        self.assertEqual(by_id[child]["parent_version_id"], parent)

        harness._set(
            "compare-versions",
            _comparison(harness, revising["edit_attempt"]),
        )
        self.assertEqual(harness.engine.run_one_step().executed_step, "compare-versions")
        compared = build_view_model(open_engine(self.root, harness.track_id))
        self.assertEqual(
            compared["ab"]["left_version_id"],
            compared["version_comparison"]["parent_version_id"],
        )
        self.assertEqual(
            compared["ab"]["right_version_id"],
            compared["version_comparison"]["child_version_id"],
        )

        qc = harness.engine.run_one_step()
        self.assertEqual(qc.next_step, "final-approval")
        final = build_view_model(open_engine(self.root, harness.track_id))
        self.assertEqual(final["gate"], "FINAL_APPROVAL")
        self.assertEqual(final["technical_qc"]["analyzer"], "mock")
        self.assertEqual(final["technical_qc"]["mock_notice"], MOCK_QC_NOTICE)
        self.assertEqual(
            [item["verdict"] for item in final["actions"]],
            [item[0] for item in GATE_ACTIONS["FINAL_APPROVAL"]],
        )
        blob = json.dumps(final)
        self.assertNotIn(str(self.root), blob)
        self.assertNotIn("csrf", blob.lower())
        for value in _strings(final):
            self.assertFalse(value.startswith("/"), value)

        final_decision = harness.decision(
            "decision-final-view",
            "FINAL_APPROVAL",
            "APPROVE_FINAL",
            version_id=final["current_version_id"],
            comment="заметка",
        )
        harness.capture(final_decision)
        captured = build_view_model(open_engine(self.root, harness.track_id))
        self.assertIn("decision-final-view", captured["captured_decision_ids"])
        self.assertEqual(captured["pending_status"], None)
        self.assertTrue(captured["knowledge_cases"])
        self.assertEqual(captured["knowledge_cases"][0]["rule_status"], "candidate_rule")

    def test_mock_audio_unavailable_without_absolute_paths(self) -> None:
        store_root = self.root / "runs"
        StateStore(store_root, "track-audio", clock=lambda: NOW)
        versions = VersionStore(
            store_root / "track-audio" / "versions.json",
            track_id="track-audio",
            clock=lambda: NOW,
        )
        versions.add(
            VersionRecord(
                version_id="ver-mock",
                parent_version_id=None,
                operation="generate-batch",
                prompt_id="prompt-001",
                audio_uri="mock://audio/job.wav",
                checksum="checksum-mock",
                status="candidate",
            )
        )
        versions.set_current("ver-mock")
        view = build_view_model(open_engine(store_root, "track-audio"))
        self.assertFalse(view["versions"][0]["audio_available"])
        self.assertEqual(view["versions"][0]["audio_block_reason"], "mock_uri")
        self.assertNotIn(str(store_root), json.dumps(view))

    def test_revision_escalation_verdicts(self) -> None:
        harness = Harness(self.root, track_id="track-escalation")
        harness.reach_package_gate()
        harness.approve_package()
        harness.reach_base_gate()
        harness.select_base()
        for index in range(3):
            harness.engine.state_store.transition(
                "EDIT_COMPLETED",
                event_id=f"consume:{index}",
            )
        outcome = harness.engine.run_one_step()
        self.assertEqual(outcome.next_step, "revision-escalation")
        view = build_view_model(open_engine(self.root, harness.track_id))
        self.assertEqual(view["gate"], "REVISION_ESCALATION")
        self.assertEqual(view["outcome"], "WAITING_FOR_HUMAN")
        self.assertEqual(
            [item["verdict"] for item in view["actions"]],
            [item[0] for item in GATE_ACTIONS["REVISION_ESCALATION"]],
        )
        current = view["current_version_id"]
        parent = next(
            item["parent_version_id"]
            for item in view["versions"]
            if item["version_id"] == current
        )
        self.assertEqual(
            view["references"]["rollback_version_ids"],
            [parent] if isinstance(parent, str) and parent else [],
        )


def _comparison(harness: Harness, pending: dict) -> dict:
    comparison = fixture("sample-version-comparison.json", harness.track_id)
    comparison["edit_attempt_id"] = pending["edit_attempt_id"]
    comparison["parent_version_id"] = pending["parent_version_id"]
    comparison["child_version_id"] = pending["child_version_id"]
    return comparison


if __name__ == "__main__":
    unittest.main()

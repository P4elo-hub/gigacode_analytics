"""Knowledge-case journal: four gates, idempotency, and crash recovery."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import ValidationError

from music_production.orchestration import Outcome
from music_production.orchestration.errors import DecisionConflictError
from music_production.orchestration.state_store import read_jsonl, validate_document
from tests.music_production.test_orchestration import (
    NOW,
    ROOT,
    Harness,
    fixture,
    knowledge_case,
)

AGENTS = ROOT / ".gigacode" / "agents"
SKILLS = ROOT / ".gigacode" / "skills"


def tree_digest(path: Path) -> str:
    digest = hashlib.sha256()
    for file in sorted(item for item in path.rglob("*") if item.is_file()):
        digest.update(file.relative_to(path).as_posix().encode())
        digest.update(b"\0")
        digest.update(file.read_bytes())
    return digest.hexdigest()


def journal_cases(root: Path, track_id: str) -> list[dict]:
    return read_jsonl(root / track_id / "expert-cases.jsonl")


def snapshot_cases(root: Path, track_id: str) -> dict:
    return json.loads(
        (root / track_id / "knowledge.json").read_text(encoding="utf-8")
    )


class ExpertKnowledgeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.agents_digest = tree_digest(AGENTS)
        cls.skills_digest = tree_digest(SKILLS)

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.assertEqual(tree_digest(AGENTS), self.agents_digest)
        self.assertEqual(tree_digest(SKILLS), self.skills_digest)
        self.temporary.cleanup()

    def test_unicode_comment_survives_restart(self) -> None:
        comment = "Решение: оставить куплет\nбез смены мелодии — ё"
        harness = Harness(self.root)
        harness.reach_package_gate()
        decision = harness.decision(
            "decision-unicode",
            "PACKAGE_APPROVAL",
            "APPROVE_PACKAGE",
            song_package_version_id="package-001",
            comment=comment,
        )
        harness.capture(decision)

        raw = (self.root / harness.track_id / "expert-cases.jsonl").read_text(
            encoding="utf-8"
        )
        self.assertIn("Решение", raw)
        self.assertNotIn("\\u", raw)
        self.assertEqual(journal_cases(self.root, harness.track_id)[0]["comment"], comment)

        harness.new_engine()
        self.assertEqual(
            journal_cases(self.root, harness.track_id)[0]["comment"],
            comment,
        )
        self.assertEqual(
            snapshot_cases(self.root, harness.track_id)["cases"][0]["comment"],
            comment,
        )

    def test_repeat_capture_does_not_append_journal_line(self) -> None:
        harness = self._crash_before_snapshot()
        path = self.root / harness.track_id / "expert-cases.jsonl"
        self.assertEqual(len(path.read_text(encoding="utf-8").splitlines()), 1)

        restarted = harness.new_engine()
        outcome = restarted.run_one_step()

        self.assertEqual(outcome.executed_step, "capture-knowledge")
        self.assertEqual(len(journal_cases(self.root, harness.track_id)), 1)
        restarted.handlers._remember_expert_case(
            journal_cases(self.root, harness.track_id)[0]
        )
        self.assertEqual(len(journal_cases(self.root, harness.track_id)), 1)

    def test_conflicting_case_for_same_decision_is_rejected(self) -> None:
        harness = Harness(self.root)
        harness.reach_package_gate()
        decision = harness.decision(
            "decision-conflict",
            "PACKAGE_APPROVAL",
            "APPROVE_PACKAGE",
            song_package_version_id="package-001",
        )
        path = self.root / harness.track_id / "expert-cases.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {"decision_id": decision["decision_id"], "comment": "другой кейс"},
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        harness._set("capture-knowledge", knowledge_case(decision))
        harness.engine.record_decision(decision)

        with self.assertRaises(DecisionConflictError):
            harness.engine.run_one_step()

        self.assertEqual(len(path.read_text(encoding="utf-8").splitlines()), 1)
        self.assertFalse((self.root / harness.track_id / "knowledge.json").exists())
        self.assertEqual(harness.engine.state_store.load()["state"], "PACKAGE_READY")

    def test_crash_between_journal_and_snapshot_recovers_once(self) -> None:
        harness = self._crash_before_snapshot()
        track = harness.track_id
        self.assertEqual(len(journal_cases(self.root, track)), 1)
        self.assertFalse((self.root / track / "knowledge.json").exists())
        self.assertEqual(harness.engine.state_store.load()["state"], "PACKAGE_READY")

        restarted = harness.new_engine()
        self.assertEqual(restarted.dispatch().next_step, "capture-knowledge")
        outcome = restarted.run_one_step()

        self.assertEqual(outcome.state, "PACKAGE_APPROVED")
        recovered = journal_cases(self.root, track)
        self.assertEqual(len(recovered), 1)
        knowledge = snapshot_cases(self.root, track)
        self.assertEqual(knowledge["captured_decision_ids"], ["decision-crash"])
        self.assertEqual(knowledge["cases"][0]["decision_id"], recovered[0]["decision_id"])
        self.assertEqual(knowledge["cases"][0]["comment"], recovered[0]["comment"])

    def test_verdict_is_not_applied_before_journal_and_snapshot(self) -> None:
        harness = self._crash_before_snapshot()
        self.assertEqual(harness.engine.state_store.load()["state"], "PACKAGE_READY")
        self.assertTrue(harness.engine.decisions.current())
        self.assertFalse((self.root / harness.track_id / "knowledge.json").exists())

        restarted = harness.new_engine()
        self.assertEqual(restarted.dispatch().next_step, "capture-knowledge")
        outcome = restarted.run_one_step()
        self.assertEqual(outcome.state, "PACKAGE_APPROVED")
        self.assertTrue((self.root / harness.track_id / "knowledge.json").is_file())
        self.assertEqual(len(journal_cases(self.root, harness.track_id)), 1)

    def test_package_approval_case_uses_song_package_subject(self) -> None:
        harness = Harness(self.root)
        recorder = self._record_inputs(harness)
        harness.reach_package_gate()
        harness.approve_package()

        case = journal_cases(self.root, harness.track_id)[-1]
        validate_document("knowledge-case", case)
        self.assertEqual(case["subject_type"], "SONG_PACKAGE")
        self.assertEqual(case["subject_id"], "package-001")
        evidence = {item["artifact_type"] for item in case["evidence_refs"]}
        self.assertIn("brief", evidence)
        self.assertIn("package-review", evidence)
        names = [item.value for item in recorder.inputs[-1]]
        self.assertIn("brief", names)
        self.assertIn("package-review", names)
        self.assertEqual(case["rule_status"], "candidate_rule")

    def test_base_selection_case_uses_candidate_and_generation_evidence(self) -> None:
        harness = Harness(self.root)
        harness.reach_package_gate()
        harness.approve_package()
        recorder = self._record_inputs(harness)
        harness.reach_base_gate()
        version_id = harness.select_base()

        case = journal_cases(self.root, harness.track_id)[-1]
        validate_document("knowledge-case", case)
        candidate = harness.engine.artifacts.latest("candidates")["candidates"][0]
        self.assertEqual(case["subject_type"], "CANDIDATE")
        self.assertEqual(case["subject_id"], candidate["candidate_id"])
        self.assertEqual(case["result_version_id"], version_id)
        self.assertEqual(case["prompt_id"], "prompt-001")
        evidence = {item["artifact_type"] for item in case["evidence_refs"]}
        self.assertIn("generation-request", evidence)
        self.assertIn("candidate-review", evidence)
        names = [item.value for item in recorder.inputs[-1]]
        self.assertIn("generation-request", names)
        self.assertIn("candidate-review", names)

    def test_revision_escalation_copies_defect_and_comparison_facts(self) -> None:
        harness, base_id = self._wait_for_revision(with_comparison=True)
        comparison = harness.engine.artifacts.latest("version-comparison")
        decision = harness.decision(
            "decision-revision",
            "REVISION_ESCALATION",
            "ACCEPT_REVISION",
            version_id=base_id,
        )
        harness.capture(decision)

        case = journal_cases(self.root, harness.track_id)[-1]
        validate_document("knowledge-case", case)
        self.assertEqual(case["subject_type"], "REVISION")
        self.assertEqual(case["subject_id"], "revision-plan-001")
        self.assertEqual(case["defect_id"], "defect-001")
        self.assertEqual(case["prompt_id"], "prompt-001")
        self.assertEqual(case["result_version_id"], comparison["child_version_id"])
        self.assertEqual(case["proposed_action"], "replace-section")
        evidence = {item["artifact_type"] for item in case["evidence_refs"]}
        self.assertIn("defect", evidence)
        self.assertIn("revision-plan", evidence)
        self.assertIn("version-comparison", evidence)
        facts = {item["code"]: item for item in case["technical_facts"]}
        self.assertEqual(facts["comparison_outcome"]["value"], comparison["outcome"])
        self.assertIs(facts["target_defect_resolved"]["value"], True)
        self.assertEqual(facts["capability_required"]["value"], "replace-section")
        self.assertIs(facts["capability_available"]["value"], False)
        self.assertEqual(facts["revision_budget_remaining"]["unit"], "attempt")
        self.assertEqual(facts["max_defect_fix_attempts"]["value"], 3)

    def test_final_approval_keeps_current_version_and_qc_facts(self) -> None:
        harness = Harness(self.root)
        pending = harness.accept_edit_and_reach_final_gate()
        decision = harness.decision(
            "decision-final",
            "FINAL_APPROVAL",
            "APPROVE_FINAL",
            version_id=pending["child_version_id"],
        )
        harness.capture(decision)

        case = journal_cases(self.root, harness.track_id)[-1]
        validate_document("knowledge-case", case)
        self.assertEqual(case["subject_type"], "VERSION")
        self.assertEqual(case["subject_id"], pending["child_version_id"])
        self.assertEqual(case["result_version_id"], pending["child_version_id"])
        evidence = {item["artifact_type"] for item in case["evidence_refs"]}
        self.assertIn("technical-qc", evidence)
        self.assertIn("version-comparison", evidence)
        facts = {item["code"]: item["value"] for item in case["technical_facts"]}
        self.assertEqual(facts["qc_result"], "pass")
        self.assertEqual(facts["qc_waveform"], "not-analyzed")

    def test_available_ids_are_not_replaced_with_null(self) -> None:
        harness = Harness(self.root)
        pending = harness.accept_edit_and_reach_final_gate()
        decision = harness.decision(
            "decision-final-ids",
            "FINAL_APPROVAL",
            "APPROVE_FINAL",
            version_id=pending["child_version_id"],
        )
        harness.capture(decision)
        case = journal_cases(self.root, harness.track_id)[-1]
        self.assertEqual(case["defect_id"], "defect-001")
        self.assertEqual(case["prompt_id"], "prompt-001")
        self.assertEqual(case["result_version_id"], pending["child_version_id"])

    def test_missing_subject_is_blocked(self) -> None:
        harness = Harness(self.root)
        harness.reach_package_gate()
        harness.engine.artifacts.invalidate(
            ["song-package"],
            event_id="drop-song-package",
            reason="test",
            occurred_at=NOW,
        )
        decision = harness.decision(
            "decision-missing-subject",
            "PACKAGE_APPROVAL",
            "APPROVE_PACKAGE",
            song_package_version_id="package-001",
        )
        harness._set("capture-knowledge", knowledge_case(decision))
        harness.engine.record_decision(decision)
        outcome = harness.engine.run_one_step()

        self.assertEqual(outcome.outcome, Outcome.BLOCKED)
        self.assertIn("subject", outcome.reason)
        self.assertFalse((self.root / harness.track_id / "expert-cases.jsonl").exists())
        self.assertEqual(harness.engine.state_store.load()["state"], "PACKAGE_READY")

    def test_rule_status_stays_candidate_rule(self) -> None:
        harness = Harness(self.root)
        harness.reach_package_gate()
        harness.approve_package()
        case = journal_cases(self.root, harness.track_id)[0]
        self.assertEqual(case["rule_status"], "candidate_rule")
        schema = json.loads(
            (
                ROOT / "music_production" / "contracts" / "knowledge-case.schema.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(schema["properties"]["rule_status"]["const"], "candidate_rule")

    def test_active_rule_is_rejected_by_schema(self) -> None:
        case = json.loads(
            (
                ROOT / "music_production" / "fixtures" / "sample-knowledge-case.json"
            ).read_text(encoding="utf-8")
        )
        case["rule_status"] = "active_rule"
        with self.assertRaises(ValidationError):
            validate_document("knowledge-case", case)
        invalid = json.loads(
            (
                ROOT / "music_production" / "fixtures" / "invalid-knowledge-case.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(invalid["rule_status"], "active_rule")
        with self.assertRaises(ValidationError):
            validate_document("knowledge-case", invalid)

    def test_mock_trace_of_four_human_gates(self) -> None:
        """Four deterministic gate captures. Mock QC is not a listening verdict."""

        harness = Harness(self.root)
        base_id, pending = harness.reach_edit()
        for index in range(2):
            harness.engine.state_store.transition(
                "EDIT_COMPLETED",
                event_id=f"consume-trace:{index}",
            )
        harness.engine.state_store.transition(
            "COMPARISON_ACCEPTED",
            {"version_id": base_id, "critical": 0, "major": 0},
            event_id="trace-clear-defects",
        )
        self.assertEqual(harness.engine.dispatch().next_step, "revision-escalation")
        comparison = fixture("sample-version-comparison.json", harness.track_id)
        comparison["edit_attempt_id"] = pending["edit_attempt_id"]
        comparison["parent_version_id"] = pending["parent_version_id"]
        comparison["child_version_id"] = pending["child_version_id"]
        revision = harness.decision(
            "decision-revision",
            "REVISION_ESCALATION",
            "ACCEPT_REVISION",
            version_id=base_id,
            comment="mock revision gate",
        )
        harness._set("capture-knowledge", knowledge_case(revision))
        harness.engine.record_decision(revision)
        harness.engine.handlers._write_artifact("version-comparison", comparison)
        captured = harness.engine.run_one_step()
        self.assertEqual(captured.executed_step, "capture-knowledge")
        qc = harness.engine.run_one_step()
        self.assertEqual(qc.executed_step, "final-qc")
        final = harness.decision(
            "decision-final",
            "FINAL_APPROVAL",
            "APPROVE_FINAL",
            version_id=base_id,
            comment="mock final gate",
        )
        harness.capture(final)

        cases = journal_cases(self.root, harness.track_id)
        self.assertEqual(len(cases), 4)
        self.assertEqual(
            [item["gate"] for item in cases],
            [
                "PACKAGE_APPROVAL",
                "BASE_SELECTION",
                "REVISION_ESCALATION",
                "FINAL_APPROVAL",
            ],
        )
        self.assertEqual(
            [item["subject_type"] for item in cases],
            ["SONG_PACKAGE", "CANDIDATE", "REVISION", "VERSION"],
        )
        for case in cases:
            validate_document("knowledge-case", case)
            self.assertEqual(case["rule_status"], "candidate_rule")
        waveform = {
            item["code"]: item["value"] for item in cases[-1]["technical_facts"]
        }
        self.assertEqual(waveform["qc_waveform"], "not-analyzed")
        self.assertEqual(cases[-1]["result_version_id"], base_id)
        decisions = read_jsonl(self.root / harness.track_id / "decisions.jsonl")
        self.assertEqual(len(decisions), 4)
        self.assertTrue(
            all(item.get("payload", {}).get("decision_id") for item in decisions)
        )

    def _crash_before_snapshot(self) -> Harness:
        harness = Harness(self.root)
        harness.reach_package_gate()
        decision = harness.decision(
            "decision-crash",
            "PACKAGE_APPROVAL",
            "APPROVE_PACKAGE",
            song_package_version_id="package-001",
            comment="сбой между журналом и снимком",
        )
        harness._set("capture-knowledge", knowledge_case(decision))
        harness.engine.record_decision(decision)

        def fail_once() -> None:
            raise RuntimeError("snapshot write interrupted")

        harness.engine.handlers.before_knowledge_snapshot = fail_once
        with self.assertRaises(RuntimeError):
            harness.engine.run_one_step()
        return harness

    def _wait_for_revision(self, *, with_comparison: bool) -> tuple[Harness, str]:
        harness = Harness(self.root, capabilities=("generate-batch",))
        harness.reach_package_gate()
        harness.approve_package()
        harness.reach_base_gate()
        base_id = harness.select_base()
        defect = fixture("sample-defect.json", harness.track_id)
        defect["version_id"] = base_id
        harness._set("diagnose-defects", defect)
        plan = fixture("sample-revision-plan.json", harness.track_id)
        plan["source_version_id"] = base_id
        harness._set("plan-revision", plan)
        self.assertEqual(harness.engine.run_one_step().executed_step, "diagnose-defects")
        planned = harness.engine.run_one_step()
        self.assertEqual(planned.executed_step, "plan-revision")
        self.assertEqual(planned.next_step, "revision-escalation")
        if with_comparison:
            comparison = fixture("sample-version-comparison.json", harness.track_id)
            comparison["parent_version_id"] = base_id
            comparison["child_version_id"] = f"{base_id}-observed"
            comparison["recommended_current_version_id"] = base_id
            harness.engine.handlers._write_artifact("version-comparison", comparison)
        return harness, base_id

    @staticmethod
    def _record_inputs(harness: Harness):
        class RecordingRuntime:
            def __init__(self, inner) -> None:
                self.inner = inner
                self.inputs = []

            def run(self, **kwargs):
                self.inputs.append(list(kwargs["input_artifacts"]))
                return self.inner.run(**kwargs)

        recorder = RecordingRuntime(harness.runtime)
        harness.engine.handlers.runtime = recorder
        return recorder


if __name__ == "__main__":
    unittest.main()

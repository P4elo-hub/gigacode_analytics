"""End-to-end offline orchestration, recovery, and idempotency tests."""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

from music_production.adapters.base import JobStatus
from music_production.adapters.capabilities import CapabilityRegistry
from music_production.adapters.mock_suno import MockScenario, MockSunoAdapter
from music_production.orchestration import (
    MockTechnicalQC,
    OrchestrationEngine,
    Outcome,
)
from music_production.orchestration.artifact_store import ArtifactStore
from music_production.orchestration.errors import (
    DecisionConflictError,
    InvalidTrackIdError,
    StepLimitExceededError,
    UnknownArtifactTypeError,
    UnsafeArtifactPathError,
)
from music_production.orchestration.state_store import (
    StateStore,
    atomic_write_json,
    read_jsonl,
)
from music_production.runtime.mock import MockAgentRuntime
from music_production.services.version_store import VersionRecord

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from pipeline_status import build_status  # noqa: E402

FIXTURES = ROOT / "music_production" / "fixtures"
NOW = "2026-09-28T12:00:00Z"

STEP_AGENT = {
    "brief": "music-brief-analyst",
    "lyrics-write": "music-lyrics-writer",
    "lyrics-review": "music-lyrics-editor",
    "sound-design": "music-sound-director",
    "package-review": "music-package-reviewer",
    "prompt-compile": "music-suno-prompt-compiler",
    "candidate-review": "music-candidate-critic",
    "diagnose-defects": "music-defect-diagnostician",
    "plan-revision": "music-revision-planner",
    "compare-versions": "music-version-comparator",
    "capture-knowledge": "music-knowledge-capturer",
}

STEP_TYPE = {
    "brief": "brief",
    "lyrics-write": "lyrics",
    "lyrics-review": "lyrics-review",
    "sound-design": "sound-direction",
    "package-review": "package-review",
    "prompt-compile": "generation-request",
    "candidate-review": "candidate-review",
    "diagnose-defects": "defect",
    "plan-revision": "revision-plan",
    "compare-versions": "version-comparison",
    "capture-knowledge": "knowledge-case",
}


def fixture(name: str, track_id: str) -> dict:
    value = json.loads((FIXTURES / name).read_text(encoding="utf-8"))

    def replace(node):
        if isinstance(node, dict):
            for key, child in node.items():
                if key == "track_id":
                    node[key] = track_id
                else:
                    replace(child)
        elif isinstance(node, list):
            for child in node:
                replace(child)

    replace(value)
    return value


def envelope(step: str, track_id: str, artifact: dict, outcome: str = "PASS") -> dict:
    return {
        "schema_version": "1.0",
        "track_id": track_id,
        "created_at": NOW,
        "agent_id": STEP_AGENT[step],
        "step": step,
        "outcome": outcome,
        "artifact_type": STEP_TYPE[step],
        "artifact": artifact,
        "issues": [] if outcome == "PASS" else [
            {"code": "REVISION", "severity": "MAJOR", "message": "revise"}
        ],
        "blocked_reason": None,
    }


def blocked_envelope(step: str, track_id: str) -> dict:
    value = envelope(step, track_id, fixture("sample-lyrics.json", track_id))
    value["outcome"] = "BLOCKED"
    value["artifact"] = None
    value["blocked_reason"] = "fixture blocked"
    return value


def knowledge_case(decision: dict) -> dict:
    subject_type = {
        "PACKAGE_APPROVAL": "SONG_PACKAGE",
        "BASE_SELECTION": "CANDIDATE",
        "REVISION_ESCALATION": "REVISION",
        "FINAL_APPROVAL": "VERSION",
    }[decision["gate"]]
    subject_id = (
        decision.get("song_package_version_id")
        or decision.get("candidate_id")
        or decision.get("version_id")
        or "pending-subject"
    )
    return {
        "schema_version": "1.0",
        "track_id": decision["track_id"],
        "created_at": NOW,
        "case_id": f"case-{decision['decision_id']}",
        "decision_id": decision["decision_id"],
        "gate": decision["gate"],
        "subject_type": subject_type,
        "subject_id": subject_id,
        "version_before_id": decision.get("version_id"),
        "defect_id": None,
        "proposed_action": None,
        "prompt_id": None,
        "result_version_id": decision.get("version_id"),
        "verdict": decision["verdict"],
        "decided_by": decision["decided_by"],
        "comment": decision.get("comment"),
        "captured_at": NOW,
        "evidence_refs": [],
        "technical_facts": [],
        "rule_status": "candidate_rule",
    }


class Harness:
    def __init__(
        self,
        root: Path,
        track_id: str = "track-e2e",
        *,
        scenarios=None,
        capabilities=("generate-batch", "replace-section"),
    ) -> None:
        self.root = root
        self.track_id = track_id
        self.runtime = MockAgentRuntime()
        self.capabilities = CapabilityRegistry(capabilities)
        self.adapter = MockSunoAdapter(self.capabilities, scenarios=scenarios)
        self.qc = MockTechnicalQC({"result": "pass", "facts": {"waveform": "not-analyzed"}})
        self.engine = self.new_engine()
        self._set_static_results()

    def new_engine(self) -> OrchestrationEngine:
        return OrchestrationEngine(
            run_root=self.root,
            track_id=self.track_id,
            runtime=self.runtime,
            adapter=self.adapter,
            capabilities=self.capabilities,
            technical_qc=self.qc,
            clock=lambda: NOW,
            max_steps=40,
        )

    def _set(self, step: str, artifact: dict) -> None:
        self.runtime.set_result(envelope(step, self.track_id, artifact))

    def _set_static_results(self) -> None:
        self._set("brief", fixture("sample-brief.json", self.track_id))
        self._set("lyrics-write", fixture("sample-lyrics.json", self.track_id))
        self._set(
            "lyrics-review",
            fixture("sample-lyrics-review-pass.json", self.track_id),
        )
        self._set(
            "sound-design",
            fixture("sample-sound-direction.json", self.track_id),
        )
        self._set(
            "package-review",
            fixture("sample-package-review-pass.json", self.track_id),
        )
        self._set(
            "prompt-compile",
            fixture("sample-generation-request.json", self.track_id),
        )

    def decision(self, decision_id: str, gate: str, verdict: str, **references) -> dict:
        value = {
            "schema_version": "1.0",
            "track_id": self.track_id,
            "created_at": NOW,
            "decision_id": decision_id,
            "gate": gate,
            "verdict": verdict,
            "decided_by": "Alex",
            "comment": "fixture",
        }
        value.update(references)
        return value

    def capture(self, decision: dict) -> None:
        self._set("capture-knowledge", knowledge_case(decision))
        self.engine.record_decision(decision)
        outcome = self.engine.run_one_step()
        assert outcome.executed_step == "capture-knowledge", outcome

    def reach_package_gate(self):
        outcome = self.engine.run_until_blocked()
        assert outcome.outcome == Outcome.WAITING_FOR_HUMAN, outcome
        assert outcome.next_step == "package-approval", outcome
        return outcome

    def approve_package(self):
        decision = self.decision(
            "decision-package",
            "PACKAGE_APPROVAL",
            "APPROVE_PACKAGE",
            song_package_version_id="package-001",
        )
        self.capture(decision)

    def reach_base_gate(self):
        while True:
            decision = self.engine.dispatch()
            if decision.next_step == "candidate-review":
                candidates = self.engine.artifacts.latest("candidates")["candidates"]
                review = fixture("sample-candidate-review.json", self.track_id)
                review["candidates"][0]["candidate_id"] = candidates[0]["candidate_id"]
                review["shortlist_candidate_ids"] = [candidates[0]["candidate_id"]]
                self._set("candidate-review", review)
            outcome = self.engine.run_one_step()
            if outcome.outcome != Outcome.PROGRESSED:
                break
        assert outcome.next_step == "select-base", outcome
        return outcome

    def select_base(self):
        candidate = self.engine.artifacts.latest("candidates")["candidates"][0]
        decision = self.decision(
            "decision-base",
            "BASE_SELECTION",
            "SELECT_AS_BASE",
            candidate_id=candidate["candidate_id"],
        )
        self.capture(decision)
        return candidate["version_id"]

    def reach_edit(self):
        self.reach_package_gate()
        self.approve_package()
        self.reach_base_gate()
        base_id = self.select_base()
        defect = fixture("sample-defect.json", self.track_id)
        defect["version_id"] = base_id
        self._set("diagnose-defects", defect)
        plan = fixture("sample-revision-plan.json", self.track_id)
        plan["source_version_id"] = base_id
        self._set("plan-revision", plan)
        assert self.engine.run_one_step().executed_step == "diagnose-defects"
        assert self.engine.run_one_step().executed_step == "plan-revision"
        assert self.engine.run_one_step().executed_step == "execute-edit"
        return base_id, self.engine.artifacts.latest("edit-attempt")

    def accept_edit_and_reach_final_gate(self):
        _base_id, pending = self.reach_edit()
        comparison = fixture("sample-version-comparison.json", self.track_id)
        comparison["edit_attempt_id"] = pending["edit_attempt_id"]
        comparison["parent_version_id"] = pending["parent_version_id"]
        comparison["child_version_id"] = pending["child_version_id"]
        self._set("compare-versions", comparison)
        assert self.engine.run_one_step().executed_step == "compare-versions"
        outcome = self.engine.run_one_step()
        assert outcome.next_step == "final-approval", outcome
        return pending


class OrchestrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_happy_path_and_restart_idempotency(self) -> None:
        harness = Harness(self.root)
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
        self.assertEqual(harness.engine.run_one_step().executed_step, "plan-revision")
        self.assertEqual(harness.engine.run_one_step().executed_step, "execute-edit")
        pending = harness.engine.artifacts.latest("edit-attempt")

        comparison = fixture("sample-version-comparison.json", harness.track_id)
        comparison["edit_attempt_id"] = pending["edit_attempt_id"]
        comparison["parent_version_id"] = pending["parent_version_id"]
        comparison["child_version_id"] = pending["child_version_id"]
        harness._set("compare-versions", comparison)
        self.assertEqual(harness.engine.run_one_step().executed_step, "compare-versions")
        qc = harness.engine.run_one_step()
        self.assertEqual(qc.executed_step, "final-qc")
        self.assertEqual(qc.next_step, "final-approval")

        final = harness.decision(
            "decision-final",
            "FINAL_APPROVAL",
            "APPROVE_FINAL",
            version_id=pending["child_version_id"],
        )
        harness.capture(final)
        self.assertEqual(harness.engine.record_decision(final), final)
        done = harness.engine.run_one_step()
        self.assertEqual(done.outcome, Outcome.DONE)
        self.assertEqual(done.state, "APPROVED")

        jobs_before = json.loads(
            (self.root / harness.track_id / "jobs.json").read_text(encoding="utf-8")
        )
        versions_before = json.loads(
            (self.root / harness.track_id / "versions.json").read_text(encoding="utf-8")
        )
        events_before = read_jsonl(self.root / harness.track_id / "events.jsonl")
        restarted = harness.new_engine()
        self.assertEqual(restarted.run_one_step().outcome, Outcome.DONE)
        self.assertEqual(
            jobs_before,
            json.loads(
                (self.root / harness.track_id / "jobs.json").read_text(encoding="utf-8")
            ),
        )
        self.assertEqual(
            versions_before,
            json.loads(
                (self.root / harness.track_id / "versions.json").read_text(encoding="utf-8")
            ),
        )
        self.assertEqual(
            len(events_before),
            len(read_jsonl(self.root / harness.track_id / "events.jsonl")),
        )
        knowledge = json.loads(
            (self.root / harness.track_id / "knowledge.json").read_text(encoding="utf-8")
        )
        self.assertEqual(len(knowledge["captured_decision_ids"]), 3)
        self.assertEqual(len(set(knowledge["captured_decision_ids"])), 3)
        self.assertEqual(len(jobs_before["jobs"]), 2)
        self.assertEqual(
            restarted.handlers.versions.current_version_id,
            pending["child_version_id"],
        )

    def test_package_change_lyrics_routes_back(self) -> None:
        harness = Harness(self.root)
        harness.reach_package_gate()
        decision = harness.decision(
            "decision-change-lyrics",
            "PACKAGE_APPROVAL",
            "CHANGE_LYRICS",
            song_package_version_id="package-001",
        )
        harness.capture(decision)
        self.assertEqual(harness.engine.dispatch().next_step, "lyrics-write")

    def test_base_regenerate_and_change_production_routes(self) -> None:
        for verdict, expected in (
            ("REGENERATE_BATCH", "prompt-compile"),
            ("CHANGE_PRODUCTION", "sound-design"),
        ):
            with self.subTest(verdict=verdict):
                root = self.root / verdict.lower()
                harness = Harness(root, track_id=f"track-{verdict.lower()}")
                harness.reach_package_gate()
                harness.approve_package()
                harness.reach_base_gate()
                candidate = harness.engine.artifacts.latest("candidates")["candidates"][0]
                decision = harness.decision(
                    f"decision-{verdict.lower()}",
                    "BASE_SELECTION",
                    verdict,
                    candidate_id=candidate["candidate_id"],
                )
                harness.capture(decision)
                self.assertEqual(harness.engine.dispatch().next_step, expected)

    def test_agent_blocked_is_not_pass(self) -> None:
        harness = Harness(self.root)
        harness.runtime.set_result(blocked_envelope("lyrics-write", harness.track_id))
        self.assertEqual(harness.engine.run_one_step().outcome, Outcome.PROGRESSED)
        blocked = harness.engine.run_one_step()
        self.assertEqual(blocked.outcome, Outcome.BLOCKED)
        self.assertFalse(harness.engine.artifacts.exists("lyrics"))

    def test_provider_failed_and_timed_out(self) -> None:
        for status, expected in (
            (JobStatus.FAILED, "PROVIDER_FAILED"),
            (JobStatus.TIMED_OUT, "TIMED_OUT"),
        ):
            with self.subTest(status=status):
                key = "generate-batch-track-pilot-001"
                root = self.root / status.value.lower()
                harness = Harness(
                    root,
                    track_id=f"track-{status.value.lower()}",
                    scenarios={key: MockScenario(statuses=(status,))},
                )
                # Fixture key is stable even after track_id substitution.
                harness.reach_package_gate()
                harness.approve_package()
                harness.engine.run_one_step()  # prompt compile
                failed = harness.engine.run_one_step()
                self.assertEqual(failed.outcome, Outcome.FAILED)
                jobs = json.loads(
                    (root / harness.track_id / "jobs.json").read_text(encoding="utf-8")
                )
                self.assertEqual(jobs["jobs"][0]["outcome"], expected)

    def test_capability_unavailable_waits_for_revision_escalation(self) -> None:
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
        harness.engine.run_one_step()
        outcome = harness.engine.run_one_step()
        self.assertEqual(outcome.next_step, "revision-escalation")
        self.assertEqual(outcome.outcome, Outcome.WAITING_FOR_HUMAN)

    def test_revision_budget_exhausted_and_retry_after_replenishment(self) -> None:
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
        self.assertEqual(waiting.next_step, "revision-escalation")
        self.assertEqual(waiting.outcome, Outcome.WAITING_FOR_HUMAN)
        self.assertEqual(waiting.state, "REVISING")
        self.assertNotEqual(waiting.state, "PAUSED")

        harness.engine.replenish_revision_budget(1, event_id="budget:replenish")
        plan = fixture("sample-revision-plan.json", harness.track_id)
        plan["source_version_id"] = base_id
        harness.engine.handlers._write_artifact("revision-plan", plan)
        retry = harness.decision(
            "decision-retry",
            "REVISION_ESCALATION",
            "RETRY_REVISION",
            version_id=base_id,
        )
        harness.capture(retry)
        self.assertEqual(harness.engine.dispatch().next_step, "plan-revision")

    def test_comparison_rejected_keeps_parent_and_replans(self) -> None:
        harness = Harness(self.root)
        base_id, pending = harness.reach_edit()
        comparison = fixture("sample-version-comparison.json", harness.track_id)
        comparison["edit_attempt_id"] = pending["edit_attempt_id"]
        comparison["parent_version_id"] = pending["parent_version_id"]
        comparison["child_version_id"] = pending["child_version_id"]
        comparison["outcome"] = "REJECTED"
        comparison["target_defect_resolved"] = False
        comparison["recommended_current_version_id"] = base_id
        harness._set("compare-versions", comparison)
        outcome = harness.engine.run_one_step()
        self.assertEqual(outcome.next_step, "plan-revision")
        self.assertEqual(harness.engine.state_store.load()["current_version_id"], base_id)
        self.assertEqual(harness.engine.handlers.versions.current_version_id, base_id)

    def test_accepted_comparison_with_blocking_defect_returns_to_diagnosis(self) -> None:
        harness = Harness(self.root)
        _base_id, attempt = harness.reach_edit()
        comparison = fixture("sample-version-comparison.json", harness.track_id)
        comparison["edit_attempt_id"] = attempt["edit_attempt_id"]
        comparison["parent_version_id"] = attempt["parent_version_id"]
        comparison["child_version_id"] = attempt["child_version_id"]
        comparison["remaining_defects"] = [
            {"defect_id": "defect-remaining", "severity": "MAJOR"}
        ]
        harness._set("compare-versions", comparison)

        outcome = harness.engine.run_one_step()

        self.assertEqual(outcome.next_step, "diagnose-defects")
        self.assertEqual(
            harness.engine.handlers.versions.current_version_id,
            attempt["child_version_id"],
        )
        self.assertFalse(harness.engine.artifacts.exists("technical-qc"))

    def test_accepted_comparison_with_only_minor_defect_goes_to_final_qc(self) -> None:
        harness = Harness(self.root)
        _base_id, attempt = harness.reach_edit()
        comparison = fixture("sample-version-comparison.json", harness.track_id)
        comparison["edit_attempt_id"] = attempt["edit_attempt_id"]
        comparison["parent_version_id"] = attempt["parent_version_id"]
        comparison["child_version_id"] = attempt["child_version_id"]
        comparison["remaining_defects"] = [
            {"defect_id": "defect-minor", "severity": "MINOR"}
        ]
        harness._set("compare-versions", comparison)

        outcome = harness.engine.run_one_step()

        self.assertEqual(outcome.next_step, "final-qc")

    def test_invalid_plan_source_is_controlled_lineage_block(self) -> None:
        harness = Harness(self.root)
        harness.reach_package_gate()
        harness.approve_package()
        harness.reach_base_gate()
        base_id = harness.select_base()
        defect = fixture("sample-defect.json", harness.track_id)
        defect["version_id"] = base_id
        harness._set("diagnose-defects", defect)
        plan = fixture("sample-revision-plan.json", harness.track_id)
        plan["source_version_id"] = "foreign-version"
        harness._set("plan-revision", plan)
        harness.engine.run_one_step()
        harness.engine.run_one_step()
        versions_before = set(harness.engine.handlers.versions.versions)

        blocked = harness.engine.run_one_step()

        self.assertEqual(blocked.outcome, Outcome.BLOCKED)
        self.assertEqual(blocked.error_code, "INVALID_VERSION_LINEAGE")
        self.assertEqual(
            harness.engine.state_store.load()["current_version_id"],
            base_id,
        )
        self.assertEqual(
            set(harness.engine.handlers.versions.versions),
            versions_before,
        )
        jobs = harness.engine.handlers._jobs()["jobs"]
        self.assertFalse(any(item.get("kind") == "edit" for item in jobs))
        self.assertTrue(
            any(
                event.get("payload", {}).get("error_code")
                == "INVALID_VERSION_LINEAGE"
                for event in read_jsonl(
                    self.root / harness.track_id / "events.jsonl"
                )
            )
        )

    def test_comparison_lineage_checks_block_without_committing_artifact(self) -> None:
        cases = (
            ("parent", "foreign-parent"),
            ("child", "foreign-child"),
            ("attempt", "foreign-attempt"),
            ("track", "other-track"),
        )
        for field, value in cases:
            with self.subTest(field=field):
                root = self.root / field
                harness = Harness(root, track_id=f"track-{field}")
                base_id, attempt = harness.reach_edit()
                comparison = fixture(
                    "sample-version-comparison.json",
                    harness.track_id,
                )
                comparison["edit_attempt_id"] = attempt["edit_attempt_id"]
                comparison["parent_version_id"] = attempt["parent_version_id"]
                comparison["child_version_id"] = attempt["child_version_id"]
                if field == "parent":
                    comparison["parent_version_id"] = value
                elif field == "child":
                    comparison["child_version_id"] = value
                elif field == "attempt":
                    comparison["edit_attempt_id"] = value
                else:
                    comparison["track_id"] = value
                harness._set("compare-versions", comparison)
                charged_before = sum(
                    bool(item.get("charged"))
                    for item in harness.engine.handlers._jobs()["jobs"]
                )

                blocked = harness.engine.run_one_step()

                self.assertEqual(blocked.outcome, Outcome.BLOCKED)
                self.assertEqual(blocked.error_code, "INVALID_VERSION_LINEAGE")
                self.assertEqual(
                    harness.engine.state_store.load()["current_version_id"],
                    base_id,
                )
                self.assertFalse(
                    harness.engine.artifacts.exists("version-comparison")
                )
                self.assertEqual(
                    sum(
                        bool(item.get("charged"))
                        for item in harness.engine.handlers._jobs()["jobs"]
                    ),
                    charged_before,
                )

    def test_comparison_child_must_belong_to_attempt_parent(self) -> None:
        harness = Harness(self.root)
        base_id, attempt = harness.reach_edit()
        other_parent = VersionRecord(
            version_id="other-parent",
            parent_version_id=None,
            operation="generate-batch",
            provider_job_id="job-other-parent",
            prompt_id="prompt-other",
            audio_uri="mock://audio/other-parent.wav",
            checksum="checksum-other-parent",
            status="candidate",
        )
        harness.engine.handlers.versions.add(other_parent)
        wrong_child = VersionRecord(
            version_id="wrong-child",
            parent_version_id=other_parent.version_id,
            operation="replace-section",
            provider_job_id="job-wrong-child",
            prompt_id="revision-plan-001",
            audio_uri="mock://audio/wrong-child.wav",
            checksum="checksum-wrong-child",
            status="pending-comparison",
        )
        harness.engine.handlers.versions.add(wrong_child)
        harness.engine.handlers._invalidate(
            "edit-attempt",
            reason="test-wrong-parent",
        )
        wrong_attempt = dict(attempt)
        wrong_attempt["edit_attempt_id"] = "edit-attempt-wrong-parent"
        wrong_attempt["child_version_id"] = wrong_child.version_id
        harness.engine.handlers._write_artifact("edit-attempt", wrong_attempt)
        comparison = fixture("sample-version-comparison.json", harness.track_id)
        comparison["edit_attempt_id"] = wrong_attempt["edit_attempt_id"]
        comparison["parent_version_id"] = wrong_attempt["parent_version_id"]
        comparison["child_version_id"] = wrong_attempt["child_version_id"]
        harness._set("compare-versions", comparison)

        blocked = harness.engine.run_one_step()

        self.assertEqual(blocked.outcome, Outcome.BLOCKED)
        self.assertEqual(blocked.error_code, "INVALID_VERSION_LINEAGE")
        self.assertEqual(
            harness.engine.handlers.versions.current_version_id,
            base_id,
        )

    def test_comparison_resolution_is_idempotent_and_conflict_blocks(self) -> None:
        harness = Harness(self.root)
        _base_id, attempt = harness.reach_edit()
        comparison = fixture("sample-version-comparison.json", harness.track_id)
        comparison["edit_attempt_id"] = attempt["edit_attempt_id"]
        comparison["parent_version_id"] = attempt["parent_version_id"]
        comparison["child_version_id"] = attempt["child_version_id"]
        harness._set("compare-versions", comparison)
        harness.engine.run_one_step()
        events_after_first = read_jsonl(
            self.root / harness.track_id / "events.jsonl"
        )

        repeated = harness.engine.handlers._agent_step("compare-versions")

        self.assertEqual(repeated.kind, "PROGRESSED")
        self.assertEqual(
            len(
                read_jsonl(self.root / harness.track_id / "events.jsonl")
            ),
            len(events_after_first),
        )

        conflicting = dict(comparison)
        conflicting["comparison_id"] = "comparison-conflict"
        conflicting["outcome"] = "REJECTED"
        conflicting["target_defect_resolved"] = False
        conflicting["recommended_current_version_id"] = attempt[
            "parent_version_id"
        ]
        harness._set("compare-versions", conflicting)
        blocked = harness.engine.handlers._agent_step("compare-versions")
        self.assertEqual(blocked.kind, "BLOCKED")
        self.assertEqual(blocked.error_code, "INVALID_VERSION_LINEAGE")

    def test_production_collector_reads_only_committed_artifacts(self) -> None:
        run_root = self.root / "Music-runs"
        track_id = "track-layout"
        state = StateStore(run_root, track_id, clock=lambda: NOW)
        artifacts = ArtifactStore(state.track_dir, track_id)
        brief = fixture("sample-brief.json", track_id)
        artifact_id = artifacts.content_id(brief)
        artifacts.write("brief", brief, artifact_id=artifact_id)

        before_commit = build_status(
            self.root,
            track_id,
            "music-production",
        )
        self.assertEqual(before_commit.next_step, "brief")

        artifacts.commit("brief", artifact_id, occurred_at=NOW)
        after_commit = build_status(
            self.root,
            track_id,
            "music-production",
        )
        self.assertEqual(after_commit.next_step, "lyrics-write")

    def test_rollback_preserves_versions_and_events(self) -> None:
        harness = Harness(self.root)
        pending = harness.accept_edit_and_reach_final_gate()
        # Return to revisions, then force an escalation where rollback is valid.
        request = harness.decision(
            "decision-request",
            "FINAL_APPROVAL",
            "REQUEST_REVISION",
            version_id=pending["child_version_id"],
        )
        harness.capture(request)
        defect = fixture("sample-defect.json", harness.track_id)
        defect["version_id"] = pending["child_version_id"]
        harness._set("diagnose-defects", defect)
        harness.engine.run_one_step()
        for index in range(2):
            harness.engine.state_store.transition(
                "EDIT_COMPLETED",
                event_id=f"consume-extra:{index}",
            )
        self.assertEqual(
            harness.engine.run_one_step().next_step,
            "revision-escalation",
        )
        count_before = len(harness.engine.handlers.versions.versions)
        rollback = harness.decision(
            "decision-rollback",
            "REVISION_ESCALATION",
            "ROLLBACK",
            version_id=pending["parent_version_id"],
        )
        harness.capture(rollback)
        self.assertEqual(
            harness.engine.handlers.versions.current_version_id,
            pending["parent_version_id"],
        )
        self.assertEqual(len(harness.engine.handlers.versions.versions), count_before)
        self.assertTrue(read_jsonl(self.root / harness.track_id / "events.jsonl"))

    def test_final_request_revision_routes_to_diagnosis(self) -> None:
        harness = Harness(self.root)
        pending = harness.accept_edit_and_reach_final_gate()
        decision = harness.decision(
            "decision-final-revise",
            "FINAL_APPROVAL",
            "REQUEST_REVISION",
            version_id=pending["child_version_id"],
        )
        harness.capture(decision)
        self.assertEqual(harness.engine.dispatch().next_step, "diagnose-defects")

    def test_stop_pauses_track(self) -> None:
        harness = Harness(self.root)
        harness.reach_package_gate()
        stop = harness.decision(
            "decision-stop",
            "PACKAGE_APPROVAL",
            "STOP",
            song_package_version_id="package-001",
        )
        harness.capture(stop)
        outcome = harness.engine.run_one_step()
        self.assertEqual(outcome.outcome, Outcome.BLOCKED)
        self.assertEqual(outcome.state, "PAUSED")

    def test_generation_replay_does_not_duplicate_job_or_budget(self) -> None:
        harness = Harness(self.root)
        harness.reach_package_gate()
        harness.approve_package()
        harness.engine.run_one_step()  # prompt compile
        first = harness.engine.run_one_step()
        self.assertEqual(first.executed_step, "generate-batch")
        jobs_path = self.root / harness.track_id / "jobs.json"
        jobs_before = json.loads(jobs_path.read_text(encoding="utf-8"))
        versions_before = len(harness.engine.handlers.versions.versions)
        provider_jobs_before = harness.adapter.job_count
        candidate_artifacts_before = len(
            harness.engine.artifacts.records("candidates")
        )
        harness.engine.state_store.event(
            "simulate:lost-candidates-index",
            {
                "type": "artifacts-invalidated",
                "artifact_types": ["candidates"],
                "reason": "simulated crash after durable job",
            },
        )
        restarted = harness.new_engine()
        replay = restarted.run_one_step()
        self.assertEqual(replay.executed_step, "generate-batch")
        self.assertEqual(harness.adapter.job_count, provider_jobs_before)
        self.assertEqual(
            json.loads(jobs_path.read_text(encoding="utf-8")),
            jobs_before,
        )
        self.assertEqual(
            len(restarted.handlers.versions.versions),
            versions_before,
        )
        self.assertEqual(
            len(restarted.artifacts.records("candidates")),
            candidate_artifacts_before,
        )

    def test_duplicate_decision_id_is_idempotent_but_conflict_rejected(self) -> None:
        harness = Harness(self.root)
        harness.reach_package_gate()
        decision = harness.decision(
            "decision-same",
            "PACKAGE_APPROVAL",
            "APPROVE_PACKAGE",
            song_package_version_id="package-001",
        )
        self.assertEqual(harness.engine.record_decision(decision), decision)
        self.assertEqual(harness.engine.record_decision(decision), decision)
        conflicting = copy.deepcopy(decision)
        conflicting["verdict"] = "STOP"
        with self.assertRaises(DecisionConflictError):
            harness.engine.record_decision(conflicting)
        records = read_jsonl(self.root / harness.track_id / "decisions.jsonl")
        self.assertEqual(len(records), 1)

    def test_event_id_deduplicates(self) -> None:
        store = StateStore(self.root, "track-event", clock=lambda: NOW)
        self.assertTrue(store.event("same", {"type": "fixture"}))
        self.assertFalse(store.event("same", {"type": "fixture"}))
        self.assertEqual(len(read_jsonl(store.events_path)), 1)

    def test_transition_event_replay_does_not_apply_twice(self) -> None:
        store = StateStore(self.root, "track-transition", clock=lambda: NOW)
        state = store.load()
        state["state"] = "REVISING"
        state["revision_budget_remaining"] = 1
        atomic_write_json(store.state_path, state)
        store.transition(
            "REPLENISH_REVISION_BUDGET",
            {"amount": 2},
            event_id="replenish-once",
        )
        replayed = store.transition(
            "REPLENISH_REVISION_BUDGET",
            {"amount": 2},
            event_id="replenish-once",
        )
        self.assertEqual(replayed["revision_budget_remaining"], 3)

    def test_crash_before_atomic_commit_keeps_previous_state(self) -> None:
        store = StateStore(self.root, "track-crash", clock=lambda: NOW)
        before = store.load()

        def crash(_path):
            raise RuntimeError("simulated crash")

        with self.assertRaises(RuntimeError):
            store.transition(
                "BRIEF_COMPLETED",
                {"revision_budget": 3},
                event_id="never-committed",
                before_replace=crash,
            )
        self.assertEqual(store.load(), before)
        prepared = read_jsonl(store.events_path)
        self.assertEqual(prepared[-1]["payload"]["type"], "state-transition-prepared")
        recovered = store.transition(
            "BRIEF_COMPLETED",
            {"revision_budget": 3},
            event_id="never-committed",
        )
        self.assertEqual(recovered["state"], "BRIEF_READY")

    def test_path_traversal_and_unknown_artifact_are_rejected(self) -> None:
        with self.assertRaises(InvalidTrackIdError):
            StateStore(self.root, "../escape")
        store = StateStore(self.root, "track-safe", clock=lambda: NOW)
        artifacts = ArtifactStore(store.track_dir, "track-safe")
        with self.assertRaises(UnknownArtifactTypeError):
            artifacts.path_for("unknown", "id")
        with self.assertRaises(UnsafeArtifactPathError):
            artifacts.path_for("brief", "/absolute")

    def test_artifact_without_commit_event_is_invisible(self) -> None:
        store = StateStore(self.root, "track-artifact", clock=lambda: NOW)
        artifacts = ArtifactStore(store.track_dir, "track-artifact")
        brief = fixture("sample-brief.json", "track-artifact")
        artifacts.write("brief", brief, artifact_id="interrupted")
        self.assertIsNone(artifacts.latest("brief"))

    def test_revise_without_artifact_routes_lyrics_revision(self) -> None:
        harness = Harness(self.root)
        harness.engine.run_one_step()  # brief
        harness.engine.run_one_step()  # lyrics
        revise = {
            "schema_version": "1.0",
            "track_id": harness.track_id,
            "created_at": NOW,
            "agent_id": "music-lyrics-editor",
            "step": "lyrics-review",
            "outcome": "REVISE",
            "artifact_type": "lyrics-review",
            "artifact": None,
            "issues": [
                {"code": "METER", "severity": "MAJOR", "message": "revise meter"}
            ],
            "blocked_reason": None,
        }
        harness.runtime.set_result(revise)
        outcome = harness.engine.run_one_step()
        self.assertEqual(outcome.next_step, "lyrics-write")

    def test_max_steps_stops_a_revision_loop(self) -> None:
        harness = Harness(self.root)
        revise = fixture("sample-lyrics-review-revise.json", harness.track_id)
        harness._set("lyrics-review", revise)
        with self.assertRaises(StepLimitExceededError):
            harness.engine.run_until_blocked(max_steps=4)


if __name__ == "__main__":
    unittest.main()

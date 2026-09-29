"""One-step and run-until-blocked orchestration for offline music runs."""

from __future__ import annotations

import copy
import json
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from types import SimpleNamespace
from typing import Callable, Mapping, Optional

from music_production.adapters.capabilities import CapabilityRegistry
from music_production.adapters.mock_suno import MockSunoAdapter
from music_production.orchestration.artifact_store import ArtifactStore
from music_production.orchestration.decisions import DecisionStore, STEP_TO_GATE
from music_production.orchestration.errors import (
    DecisionConflictError,
    StepLimitExceededError,
    UnexpectedHumanGateError,
)
from music_production.orchestration.state_store import (
    StateStore,
    read_json,
    read_jsonl,
    utc_now,
)
from music_production.orchestration.step_handlers import (
    HandlerResult,
    MockTechnicalQC,
    StepHandlers,
    TechnicalQC,
)
from music_production.runtime.base import AgentRuntime
from music_production.runtime.mock import MockAgentRuntime

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPOSITORY_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from pipeline_router import evaluate_dispatch  # noqa: E402

PIPELINE_ID = "music-production"
HUMAN_STEPS = frozenset(STEP_TO_GATE)


class Outcome(str, Enum):
    PROGRESSED = "PROGRESSED"
    WAITING_FOR_HUMAN = "WAITING_FOR_HUMAN"
    BLOCKED = "BLOCKED"
    DONE = "DONE"
    FAILED = "FAILED"


@dataclass(frozen=True)
class EngineOutcome:
    outcome: Outcome
    track_id: str
    state: str
    executed_step: Optional[str]
    next_step: Optional[str]
    reason: str
    steps_executed: int = 0


class OrchestrationEngine:
    def __init__(
        self,
        *,
        run_root: Path,
        track_id: str,
        runtime: AgentRuntime,
        adapter: MockSunoAdapter,
        capabilities: CapabilityRegistry,
        technical_qc: TechnicalQC,
        max_steps: int = 100,
        clock: Callable[[], str] = utc_now,
    ) -> None:
        if max_steps < 1:
            raise ValueError("max_steps must be positive")
        if not isinstance(runtime, MockAgentRuntime):
            raise TypeError("Prompt 5 orchestration requires MockAgentRuntime")
        if not isinstance(adapter, MockSunoAdapter):
            raise TypeError("Prompt 5 orchestration requires MockSunoAdapter")
        if not isinstance(technical_qc, MockTechnicalQC):
            raise TypeError("Prompt 5 orchestration requires MockTechnicalQC")
        self.track_id = track_id
        self.max_steps = max_steps
        self.state_store = StateStore(run_root, track_id, clock=clock)
        self.artifacts = ArtifactStore(self.state_store.track_dir, track_id)
        self.decisions = DecisionStore(self.state_store.track_dir, track_id)
        self.handlers = StepHandlers(
            track_id=track_id,
            state_store=self.state_store,
            artifact_store=self.artifacts,
            decisions=self.decisions,
            runtime=runtime,
            adapter=adapter,
            capabilities=capabilities,
            technical_qc=technical_qc,
            clock=clock,
        )

    def _knowledge(self) -> dict:
        path = self.state_store.track_dir / "knowledge.json"
        return read_json(path) if path.exists() else {}

    def _jobs(self) -> list[dict]:
        path = self.state_store.track_dir / "jobs.json"
        if not path.exists():
            return []
        value = read_json(path)
        raw = value.get("jobs")
        return raw if isinstance(raw, list) else []

    def _status(self) -> SimpleNamespace:
        state = self.state_store.load()
        brief = self.artifacts.latest("brief") or {}
        lyrics_review = self.artifacts.latest("lyrics-review") or {}
        package_review = self.artifacts.latest("package-review") or {}
        comparison = self.artifacts.latest("version-comparison") or {}
        qc = self.artifacts.latest("technical-qc") or {}
        plan = self.artifacts.latest("revision-plan") or {}
        pending_edit = self.artifacts.latest("pending-edit") or {}
        candidate_review = self.artifacts.latest("candidate-review") or {}
        decision = self.decisions.current()
        knowledge = self._knowledge()
        captured = knowledge.get("captured_decision_ids")
        captured_ids = set(captured) if isinstance(captured, list) else set()
        comparison_outcome = {
            "ACCEPTED": "accept",
            "REJECTED": "reject",
            "PARTIAL": "reject",
            "BLOCKED": "reject",
        }.get(str(comparison.get("outcome") or ""), "")
        edit_done = bool(pending_edit) and (
            not comparison
            or comparison.get("child_version_id") != pending_edit.get("child_version_id")
        )
        jobs = self._jobs()
        unsuccessful = [
            item
            for item in jobs
            if item.get("kind") == "edit"
            and item.get("outcome") not in {None, "SUCCEEDED"}
        ]
        status = SimpleNamespace(
            slug=self.track_id,
            pipeline_id=PIPELINE_ID,
            state=str(state["state"]),
            has_brief=self.artifacts.exists("brief"),
            has_lyrics=self.artifacts.exists("lyrics"),
            has_sound=self.artifacts.exists("sound-direction"),
            has_package=self.artifacts.exists("song-package"),
            has_generation_request=self.artifacts.exists("generation-request"),
            has_candidates=self.artifacts.exists("candidates"),
            has_track_state=True,
            has_revision_plan=self.artifacts.exists("revision-plan"),
            has_knowledge=bool(knowledge.get("cases")),
            has_expert_decision=bool(decision),
            has_routing_signals=True,
            lyrics_verdict=str(lyrics_review.get("verdict") or ""),
            package_verdict=str(package_review.get("verdict") or ""),
            revision_target=str(package_review.get("revision_target") or ""),
            comparison_outcome=comparison_outcome,
            qc_result=str(qc.get("result") or "").lower(),
            package_review_required=bool(
                brief.get("package_review_required", True) if brief else False
            ),
            revision_budget_remaining=int(state["revision_budget_remaining"]),
            open_blocking_defects=int(state["open_critical_defects"])
            + int(state["open_major_defects"]),
            base_selected=bool(state["base_version_id"]),
            candidate_reviewed=bool(candidate_review),
            edit_done=edit_done,
            comparisons_without_improvement=len(unsuccessful)
            + (1 if comparison_outcome == "reject" else 0),
            capability_missing=bool(plan.get("capability_required"))
            and not self.handlers.capabilities.supports(
                str(plan.get("capability_required"))
            ),
            defect_fix_limit_exhausted=sum(
                1
                for item in jobs
                if item.get("kind") == "edit" and item.get("charged")
            )
            >= int(
                (brief.get("budget") or {}).get("max_defect_fix_attempts", 0)
                if isinstance(brief.get("budget"), dict)
                else 0
            ),
            decision_id=str(decision.get("decision_id") or ""),
            decision_gate=str(decision.get("gate") or ""),
            decision_verdict=str(decision.get("verdict") or ""),
            decision_version_id=str(decision.get("version_id") or ""),
            decision_capture_pending=bool(decision.get("decision_id"))
            and decision.get("decision_id") not in captured_ids,
            awaiting_human=False,
            required_operation=str(plan.get("capability_required") or ""),
            available_operations=sorted(self.handlers.capabilities.operations),
        )
        return status

    def dispatch(self):
        return evaluate_dispatch(
            REPOSITORY_ROOT,
            self.track_id,
            self._status(),
            pipeline_id=PIPELINE_ID,
        )

    def _outcome_after(
        self,
        *,
        executed_step: Optional[str],
        handler_result: Optional[HandlerResult] = None,
        steps_executed: int = 0,
    ) -> EngineOutcome:
        state = self.state_store.load()
        decision = self.dispatch()
        if handler_result and handler_result.kind == "FAILED":
            kind = Outcome.FAILED
        elif handler_result and handler_result.kind == "BLOCKED":
            kind = Outcome.BLOCKED
        elif decision.ready:
            kind = Outcome.DONE
        elif decision.next_step in HUMAN_STEPS:
            kind = Outcome.WAITING_FOR_HUMAN
        elif decision.next_step == "paused" or state["state"] == "PAUSED":
            kind = Outcome.BLOCKED
        elif state["state"] == "FAILED":
            kind = Outcome.FAILED
        elif decision.stopped:
            kind = Outcome.BLOCKED
        else:
            kind = Outcome.PROGRESSED
        reason = (
            handler_result.detail
            if handler_result and handler_result.detail
            else decision.next_reason
        )
        return EngineOutcome(
            outcome=kind,
            track_id=self.track_id,
            state=str(state["state"]),
            executed_step=executed_step,
            next_step=decision.next_step or None,
            reason=reason,
            steps_executed=steps_executed,
        )

    def run_one_step(self) -> EngineOutcome:
        decision = self.dispatch()
        if decision.ready:
            return self._outcome_after(executed_step=None)
        if decision.next_step in HUMAN_STEPS:
            gate = STEP_TO_GATE[decision.next_step]
            self.state_store.event(
                f"human-gate:{gate}:{self.state_store.load()['revision_iteration']}",
                {"type": "human-gate-opened", "gate": gate},
            )
            return self._outcome_after(executed_step=None)
        if not decision.next_step:
            return self._outcome_after(executed_step=None)
        result = self.handlers.execute(decision.next_step)
        return self._outcome_after(
            executed_step=decision.next_step,
            handler_result=result,
            steps_executed=1,
        )

    def run_until_blocked(self, *, max_steps: Optional[int] = None) -> EngineOutcome:
        limit = self.max_steps if max_steps is None else max_steps
        if limit < 1:
            raise ValueError("max_steps must be positive")
        for count in range(limit):
            outcome = self.run_one_step()
            if outcome.outcome != Outcome.PROGRESSED:
                return EngineOutcome(
                    **{
                        **outcome.__dict__,
                        "steps_executed": count + outcome.steps_executed,
                    }
                )
        raise StepLimitExceededError(f"exceeded {limit} orchestration steps")

    def record_decision(self, decision: Mapping[str, object]) -> dict:
        historical = next(
            (
                item
                for item in self.decisions.all()
                if item.get("decision_id") == decision.get("decision_id")
            ),
            None,
        )
        if historical is not None:
            if historical != dict(decision):
                raise DecisionConflictError(
                    f"decision_id conflict: {decision.get('decision_id')}"
                )
            return copy.deepcopy(historical)
        current = self.decisions.current()
        if current:
            if current.get("decision_id") == decision.get("decision_id"):
                return self.decisions.record(
                    decision,
                    expected_gate=str(current["gate"]),
                )
            raise UnexpectedHumanGateError(
                "a different human decision is already pending capture"
            )
        dispatch = self.dispatch()
        gate = STEP_TO_GATE.get(dispatch.next_step)
        if gate is None:
            for event in reversed(read_jsonl(self.state_store.events_path)):
                payload = event.get("payload")
                if not isinstance(payload, dict):
                    continue
                if payload.get("type") == "human-decision-recorded":
                    break
                if payload.get("type") == "human-gate-opened":
                    gate = str(payload.get("gate") or "")
                    break
        if gate is None:
            raise UnexpectedHumanGateError(
                f"track is not waiting at a human gate: {dispatch.next_step or 'none'}"
            )
        recorded = self.decisions.record(decision, expected_gate=gate)
        self.state_store.event(
            f"human-decision:{recorded['decision_id']}",
            {
                "type": "human-decision-recorded",
                "gate": recorded["gate"],
                "decision_id": recorded["decision_id"],
            },
        )
        return recorded

    def replenish_revision_budget(self, amount: int, *, event_id: str) -> dict:
        return self.state_store.transition(
            "REPLENISH_REVISION_BUDGET",
            {"amount": amount},
            event_id=event_id,
        )

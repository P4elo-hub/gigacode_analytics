"""Agent and deterministic service handlers used by the orchestration engine."""

from __future__ import annotations

import copy
import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Callable, Mapping, Optional

from jsonschema import Draft202012Validator, FormatChecker

from music_production.adapters.capabilities import CapabilityRegistry
from music_production.adapters.mock_suno import MockSunoAdapter
from music_production.orchestration.artifact_store import ArtifactStore
from music_production.orchestration.decisions import DecisionStore
from music_production.orchestration.errors import StepExecutionError
from music_production.orchestration.state_store import (
    StateStore,
    atomic_write_json,
    read_json,
    read_jsonl,
    utc_now,
)
from music_production.runtime.base import AgentRuntime, ArtifactReference
from music_production.runtime.validation import AGENT_ARTIFACT_TYPES, validate_agent_result
from music_production.services.budget_guard import (
    BudgetGuard,
    BudgetLimits,
    BudgetUsage,
)
from music_production.services.job_runner import JobRunOutcome, JobRunner
from music_production.services.version_store import (
    UnknownParentError,
    UnknownVersionError,
    VersionRecord,
    VersionStore,
)

INVALID_VERSION_LINEAGE = "INVALID_VERSION_LINEAGE"

STEP_TO_AGENT = {
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

SNAPSHOT_BASE = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["schema_version", "track_id", "created_at"],
    "properties": {
        "schema_version": {"const": "1.0"},
        "track_id": {"type": "string", "minLength": 1},
        "created_at": {
            "type": "string",
            "format": "date-time",
            "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T"
            "[0-9]{2}:[0-9]{2}:[0-9]{2}Z$",
        },
    },
}


def _snapshot_schema(array_name: str) -> dict:
    schema = copy.deepcopy(SNAPSHOT_BASE)
    schema["required"].append(array_name)
    schema["properties"][array_name] = {"type": "array", "items": {"type": "object"}}
    if array_name == "cases":
        schema["required"].append("captured_decision_ids")
        schema["properties"]["captured_decision_ids"] = {
            "type": "array",
            "uniqueItems": True,
            "items": {"type": "string", "minLength": 1},
        }
    return schema


def _validate_snapshot(document: Mapping[str, object], array_name: str) -> dict:
    value = copy.deepcopy(dict(document))
    schema = _snapshot_schema(array_name)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(value)
    return value


class TechnicalQC(ABC):
    """Provider-neutral technical-QC boundary."""

    @abstractmethod
    def analyze(self, *, track_id: str, version: VersionRecord) -> Mapping[str, object]:
        """Return facts only; creative judgement remains outside this interface."""


class MockTechnicalQC(TechnicalQC):
    def __init__(self, result: Mapping[str, object]) -> None:
        self.result = copy.deepcopy(dict(result))

    def analyze(self, *, track_id: str, version: VersionRecord) -> Mapping[str, object]:
        value = copy.deepcopy(self.result)
        value.setdefault("schema_version", "1.0")
        value.setdefault("track_id", track_id)
        value.setdefault("created_at", utc_now())
        value["analyzer"] = "mock"
        value.setdefault("version_id", version.version_id)
        value.setdefault("result", "pass")
        value.setdefault("facts", {})
        return value


@dataclass(frozen=True)
class HandlerResult:
    kind: str = "PROGRESSED"
    detail: str = ""
    error_code: Optional[str] = None


class StepHandlers:
    def __init__(
        self,
        *,
        track_id: str,
        state_store: StateStore,
        artifact_store: ArtifactStore,
        decisions: DecisionStore,
        runtime: AgentRuntime,
        adapter: MockSunoAdapter,
        capabilities: CapabilityRegistry,
        technical_qc: TechnicalQC,
        clock: Callable[[], str] = utc_now,
    ) -> None:
        self.track_id = track_id
        self.state_store = state_store
        self.artifacts = artifact_store
        self.decisions = decisions
        self.runtime = runtime
        self.adapter = adapter
        self.capabilities = capabilities
        self.technical_qc = technical_qc
        self.clock = clock
        track_dir = state_store.track_dir
        self.jobs_path = track_dir / "jobs.json"
        self.knowledge_path = track_dir / "knowledge.json"
        self.versions = VersionStore(
            track_dir / "versions.json",
            track_id=track_id,
            clock=clock,
        )

    def execute(self, step: str) -> HandlerResult:
        if step in STEP_TO_AGENT:
            return self._agent_step(step)
        if step == "generate-batch":
            return self._generate_batch()
        if step == "execute-edit":
            return self._execute_edit()
        if step == "final-qc":
            return self._final_qc()
        if step == "paused":
            return HandlerResult("BLOCKED", "track is paused")
        raise StepExecutionError(f"no handler for {step}")

    def _artifact_id(self, document: Mapping[str, object]) -> str:
        for name in (
            "decision_id",
            "case_id",
            "comparison_id",
            "edit_attempt_id",
            "revision_plan_id",
            "review_id",
            "lyrics_version_id",
            "sound_direction_version_id",
            "id",
            "prompt_id",
            "version_id",
        ):
            value = document.get(name)
            if isinstance(value, str) and value:
                return f"{value}-{ArtifactStore.content_id(document)[:8]}"
        return ArtifactStore.content_id(document)

    def _write_artifact(self, artifact_type: str, document: Mapping[str, object]) -> dict:
        artifact_id = self._artifact_id(document)
        self.artifacts.write(
            artifact_type,
            document,
            artifact_id=artifact_id,
        )
        self.artifacts.commit(
            artifact_type,
            artifact_id,
            occurred_at=self.clock(),
        )
        return copy.deepcopy(dict(document))

    def _invalidate(self, *artifact_types: str, reason: str) -> None:
        digest = hashlib.sha256(
            f"{reason}:{','.join(artifact_types)}:{self.clock()}".encode("utf-8")
        ).hexdigest()[:16]
        self.artifacts.invalidate(
            list(artifact_types),
            event_id=f"invalidate:{digest}",
            reason=reason,
            occurred_at=self.clock(),
        )

    def _lineage_blocked(
        self,
        *,
        step: str,
        detail: str,
        context: Mapping[str, object],
    ) -> HandlerResult:
        payload = {
            "type": "invalid-version-lineage",
            "error_code": INVALID_VERSION_LINEAGE,
            "step": step,
            "detail": detail,
            "context": copy.deepcopy(dict(context)),
        }
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()[:20]
        self.state_store.event(f"lineage-blocked:{digest}", payload)
        return HandlerResult("BLOCKED", detail, INVALID_VERSION_LINEAGE)

    def _comparison_resolution(self, edit_attempt_id: str) -> Optional[dict]:
        for event in reversed(read_jsonl(self.state_store.events_path)):
            payload = event.get("payload")
            if (
                isinstance(payload, dict)
                and payload.get("type") == "edit-attempt-resolved"
                and payload.get("edit_attempt_id") == edit_attempt_id
            ):
                return payload
        return None

    def _record_comparison_resolution(
        self,
        comparison: Mapping[str, object],
    ) -> None:
        edit_attempt_id = str(comparison["edit_attempt_id"])
        comparison_id = str(comparison["comparison_id"])
        self.state_store.event(
            f"edit-attempt-resolution:{edit_attempt_id}",
            {
                "type": "edit-attempt-resolved",
                "edit_attempt_id": edit_attempt_id,
                "comparison_id": comparison_id,
                "comparison_hash": ArtifactStore.content_id(comparison),
                "outcome": comparison["outcome"],
            },
        )

    def _agent_step(self, step: str) -> HandlerResult:
        agent_id = STEP_TO_AGENT[step]
        artifact_type = AGENT_ARTIFACT_TYPES[agent_id]
        state = self.state_store.load()
        correlation_id = (
            f"{self.track_id}:{step}:{state['state']}:{state['revision_iteration']}"
        )
        result = validate_agent_result(
            self.runtime.run(
                agent_id=agent_id,
                step=step,
                track_id=self.track_id,
                input_artifacts=[
                    ArtifactReference(value=name)
                    for name in sorted(self.artifacts.allowed_types())
                    if self.artifacts.exists(name)
                ],
                timeout=30,
                correlation_id=correlation_id,
            )
        )
        if (
            result["agent_id"] != agent_id
            or result["step"] != step
            or result["track_id"] != self.track_id
        ):
            raise StepExecutionError("runtime result identity does not match request")
        if result["outcome"] == "BLOCKED":
            self.state_store.event(
                f"blocked:{correlation_id}",
                {
                    "type": "agent-blocked",
                    "step": step,
                    "reason": result["blocked_reason"],
                },
            )
            return HandlerResult("BLOCKED", str(result["blocked_reason"]))

        artifact = result["artifact"]
        if not isinstance(artifact, dict):
            if result["outcome"] == "REVISE":
                if step == "lyrics-review":
                    lyrics = self.artifacts.latest("lyrics") or {}
                    artifact = {
                        "schema_version": "1.0",
                        "track_id": self.track_id,
                        "created_at": str(result["created_at"]),
                        "review_id": f"review-{correlation_id.replace(':', '-')}",
                        "lyrics_version_id": str(
                            lyrics.get("lyrics_version_id") or "missing"
                        ),
                        "verdict": "REVISE",
                        "issues": result["issues"],
                    }
                else:
                    self.state_store.event(
                        f"revise-without-artifact:{correlation_id}",
                        {
                            "type": "agent-revise-without-artifact",
                            "step": step,
                            "issues": result["issues"],
                        },
                    )
                    return HandlerResult(
                        "BLOCKED",
                        f"{step} returned REVISE without a routable review artifact",
                    )
            else:
                raise StepExecutionError(f"{step} returned no artifact")
        if artifact.get("track_id") != self.track_id:
            if step == "compare-versions":
                return self._lineage_blocked(
                    step=step,
                    detail="comparison track_id does not match the run",
                    context={
                        "comparison_track_id": artifact.get("track_id"),
                        "track_id": self.track_id,
                    },
                )
            raise StepExecutionError("artifact track_id does not match run")
        defer_comparison = step == "compare-versions"
        if not defer_comparison:
            self._write_artifact(artifact_type, artifact)
        if step == "package-review" and isinstance(artifact.get("song_package"), dict):
            self._write_artifact("song-package", artifact["song_package"])

        if result["outcome"] == "REVISE":
            return HandlerResult("PROGRESSED", f"{step} requested revision")

        if step == "brief" and state["state"] == "NEW":
            budget = artifact.get("budget")
            revision_budget = (
                int(budget.get("max_defect_fix_attempts", 0))
                if isinstance(budget, dict)
                else 0
            )
            self.state_store.transition(
                "BRIEF_COMPLETED",
                {"revision_budget": revision_budget},
                event_id=f"transition:{correlation_id}",
            )
        elif step == "package-review" and artifact.get("verdict") == "PASS":
            if state["state"] == "BRIEF_READY":
                self.state_store.transition(
                    "PACKAGE_COMPLETED",
                    event_id=f"transition:{correlation_id}",
                )
        elif step == "prompt-compile":
            if state["state"] == "PACKAGE_APPROVED":
                self.state_store.transition(
                    "GENERATION_REQUESTED",
                    event_id=f"transition:{correlation_id}",
                )
        elif step == "candidate-review":
            if state["state"] == "GENERATING":
                self.state_store.transition(
                    "CANDIDATES_REVIEWED",
                    event_id=f"transition:{correlation_id}",
                )
        elif step == "diagnose-defects":
            importance = str(artifact.get("importance", "")).lower()
            self.state_store.transition(
                "REVISION_DIAGNOSED",
                {
                    "critical": 1 if importance == "critical" else 0,
                    "major": 1 if importance in {"high", "major"} else 0,
                },
                event_id=f"transition:{correlation_id}",
            )
            current = self.decisions.current()
            if current.get("verdict") == "REQUEST_REVISION":
                self.decisions.clear_current(str(current["decision_id"]))
        elif step == "plan-revision":
            comparison = self.artifacts.latest("version-comparison")
            if comparison and comparison.get("outcome") in {
                "REJECTED",
                "PARTIAL",
                "BLOCKED",
            }:
                self._invalidate(
                    "edit-attempt",
                    "version-comparison",
                    reason="new-revision-plan",
                )
            current = self.decisions.current()
            if current.get("verdict") == "RETRY_REVISION":
                self.decisions.clear_current(str(current["decision_id"]))
        elif step == "compare-versions":
            comparison_result = self._apply_comparison(artifact, correlation_id)
            if comparison_result.kind == "BLOCKED":
                return comparison_result
            if comparison_result.kind == "IDEMPOTENT":
                return HandlerResult()
            self._write_artifact(artifact_type, artifact)
            self._record_comparison_resolution(artifact)
        elif step == "capture-knowledge":
            self._capture_decision(artifact, correlation_id)
        return HandlerResult()

    def _jobs(self) -> dict:
        if self.jobs_path.exists():
            return read_json(self.jobs_path)
        return {
            "schema_version": "1.0",
            "track_id": self.track_id,
            "created_at": self.clock(),
            "jobs": [],
        }

    def _save_jobs(self, value: Mapping[str, object]) -> None:
        document = _validate_snapshot(value, "jobs")
        if document.get("track_id") != self.track_id:
            raise ValueError("jobs track_id mismatch")
        atomic_write_json(self.jobs_path, document)

    def _budget_guard(self) -> BudgetGuard:
        brief = self.artifacts.latest("brief")
        if not brief or not isinstance(brief.get("budget"), dict):
            raise StepExecutionError("brief budget is missing")
        budget = brief["budget"]
        guard = BudgetGuard(
            BudgetLimits(
                max_batch=int(budget["max_batch"]),
                max_defect_fix_attempts=int(budget["max_defect_fix_attempts"]),
                max_iterations=int(budget["max_iterations"]),
                max_api_wait_seconds=int(budget["max_api_wait_seconds"]),
                max_cost=Decimal(str(budget["max_cost"])),
            )
        )
        jobs = self._jobs()["jobs"]
        guard.committed = BudgetUsage(
            generation_batches=sum(
                1
                for item in jobs
                if item.get("charged") and item.get("kind") == "generation"
            ),
            defect_fix_attempts=sum(
                1
                for item in jobs
                if item.get("charged") and item.get("kind") == "edit"
            ),
            iterations=sum(1 for item in jobs if item.get("charged")),
            api_wait_seconds=0,
            cost=Decimal("0"),
        )
        return guard

    def _run_job(
        self,
        *,
        request: Mapping[str, object],
        request_key: str,
        kind: str,
    ) -> dict:
        jobs = self._jobs()
        existing = next(
            (item for item in jobs["jobs"] if item.get("request_key") == request_key),
            None,
        )
        if existing is not None and existing.get("outcome"):
            return copy.deepcopy(existing)

        if existing is None:
            existing = {
                "request_key": request_key,
                "kind": kind,
                "idempotency_key": request_key,
                "charged": False,
                "outcome": None,
            }
            jobs["jobs"].append(existing)
            self._save_jobs(jobs)

        usage = (
            BudgetUsage(generation_batches=1, iterations=1)
            if kind == "generation"
            else BudgetUsage(defect_fix_attempts=1, iterations=1)
        )
        runner = JobRunner(
            self.adapter,
            self._budget_guard(),
            key_factory=lambda: request_key,
        )
        result = runner.run_creative_attempt(request, usage)
        existing["outcome"] = result.outcome.value
        existing["job_id"] = result.job_id
        existing["charged"] = result.outcome != JobRunOutcome.REVISION_ESCALATION
        existing["outputs"] = (
            [asdict(output) for output in result.provider_result.outputs]
            if result.provider_result is not None
            else []
        )
        self._save_jobs(jobs)
        return copy.deepcopy(existing)

    def _generate_batch(self) -> HandlerResult:
        request = self.artifacts.latest("generation-request")
        if request is None:
            raise StepExecutionError("generation-request is missing")
        self.capabilities.require(str(request["operation"]))
        request_key = str(request["idempotency_key"])
        job = self._run_job(
            request=request,
            request_key=request_key,
            kind="generation",
        )
        if job["outcome"] == JobRunOutcome.REVISION_ESCALATION.value:
            return HandlerResult("BLOCKED", "generation budget exhausted")
        if job["outcome"] != JobRunOutcome.SUCCEEDED.value:
            self.state_store.transition(
                "FAIL",
                event_id=f"provider:{request_key}:{job['outcome']}",
            )
            return HandlerResult("FAILED", str(job["outcome"]))

        candidates = []
        for output in job["outputs"]:
            version_id = str(output["provider_output_id"])
            record = VersionRecord(
                version_id=version_id,
                parent_version_id=None,
                operation=str(request["operation"]),
                provider_job_id=str(job["job_id"]),
                prompt_id=str(request["prompt_id"]),
                audio_uri=str(output["audio_uri"]),
                checksum=str(output["checksum"]),
                status="candidate",
            )
            self.versions.add(record)
            candidates.append(
                {
                    "candidate_id": version_id,
                    "version_id": version_id,
                    "audio_uri": record.audio_uri,
                    "checksum": record.checksum,
                }
            )
        document = {
            "schema_version": "1.0",
            "track_id": self.track_id,
            "created_at": request["created_at"],
            "generation_request_id": request["prompt_id"],
            "provider_job_id": job["job_id"],
            "candidates": candidates,
        }
        self._write_artifact("candidates", document)
        return HandlerResult()

    def _execute_edit(self) -> HandlerResult:
        plan = self.artifacts.latest("revision-plan")
        if plan is None:
            raise StepExecutionError("revision plan is missing")
        operation = str(plan["operation"])
        if not self.capabilities.supports(operation):
            self._write_artifact(
                "service-status",
                {
                    "schema_version": "1.0",
                    "track_id": self.track_id,
                    "created_at": self.clock(),
                    "required_operation": operation,
                    "status": "CAPABILITY_UNAVAILABLE",
                },
            )
            return HandlerResult("PROGRESSED", "capability unavailable")
        state = self.state_store.load()
        if int(state["revision_budget_remaining"]) <= 0:
            return HandlerResult("PROGRESSED", "revision budget exhausted")
        parent_id = str(state["current_version_id"])
        if not parent_id or parent_id == "None":
            return self._lineage_blocked(
                step="execute-edit",
                detail="current version is missing",
                context={"current_version_id": state["current_version_id"]},
            )
        try:
            self.versions.get(parent_id)
        except UnknownVersionError:
            return self._lineage_blocked(
                step="execute-edit",
                detail="parent version does not exist",
                context={"parent_version_id": parent_id},
            )
        if str(plan["source_version_id"]) != parent_id:
            return self._lineage_blocked(
                step="execute-edit",
                detail="revision plan source is not current version",
                context={
                    "source_version_id": plan["source_version_id"],
                    "current_version_id": parent_id,
                },
            )
        request_key = f"edit:{plan['revision_plan_id']}"
        request = {
            "schema_version": "1.0",
            "track_id": self.track_id,
            "created_at": self.clock(),
            "operation": operation,
            "idempotency_key": request_key,
            "song_package_version_id": str(
                (self.artifacts.latest("song-package") or {}).get("version_id", "package")
            ),
            "prompt_id": str(plan["revision_plan_id"]),
        }
        job = self._run_job(request=request, request_key=request_key, kind="edit")
        if job["outcome"] == JobRunOutcome.REVISION_ESCALATION.value:
            return HandlerResult("PROGRESSED", "revision budget exhausted")
        if job["outcome"] != JobRunOutcome.SUCCEEDED.value:
            self.state_store.transition(
                "FAIL",
                event_id=f"provider:{request_key}:{job['outcome']}",
            )
            return HandlerResult("FAILED", str(job["outcome"]))
        output = job["outputs"][0]
        child_id = f"{parent_id}-edit-{str(plan['revision_plan_id'])}"
        child = VersionRecord(
            version_id=child_id,
            parent_version_id=parent_id,
            operation=operation,
            provider_job_id=str(job["job_id"]),
            prompt_id=str(plan["revision_plan_id"]),
            audio_uri=str(output["audio_uri"]),
            checksum=str(output["checksum"]),
            status="pending-comparison",
        )
        try:
            self.versions.add(child)
        except UnknownParentError:
            return self._lineage_blocked(
                step="execute-edit",
                detail="parent version does not exist",
                context={"parent_version_id": parent_id, "child_version_id": child_id},
            )
        edit_attempt_id = f"edit-attempt-{plan['revision_plan_id']}"
        self._write_artifact(
            "edit-attempt",
            {
                "schema_version": "1.0",
                "track_id": self.track_id,
                "created_at": plan["created_at"],
                "edit_attempt_id": edit_attempt_id,
                "revision_plan_id": plan["revision_plan_id"],
                "defect_id": plan["defect_id"],
                "parent_version_id": parent_id,
                "child_version_id": child_id,
                "provider_job_id": str(job["job_id"]),
                "operation": operation,
            },
        )
        self.state_store.transition(
            "EDIT_COMPLETED",
            event_id=f"transition:edit:{plan['revision_plan_id']}",
        )
        return HandlerResult()

    def _apply_comparison(
        self,
        comparison: Mapping[str, object],
        correlation_id: str,
    ) -> HandlerResult:
        if comparison.get("track_id") != self.track_id:
            return self._lineage_blocked(
                step="compare-versions",
                detail="comparison track_id does not match the run",
                context={
                    "comparison_track_id": comparison.get("track_id"),
                    "track_id": self.track_id,
                },
            )
        attempt = self.artifacts.latest("edit-attempt")
        attempt_id = str(comparison["edit_attempt_id"])
        if attempt is None or attempt.get("edit_attempt_id") != attempt_id:
            return self._lineage_blocked(
                step="compare-versions",
                detail="comparison does not reference the current edit attempt",
                context={
                    "edit_attempt_id": attempt_id,
                    "current_edit_attempt_id": (
                        attempt.get("edit_attempt_id") if attempt else None
                    ),
                },
            )
        resolution = self._comparison_resolution(attempt_id)
        comparison_hash = ArtifactStore.content_id(comparison)
        if resolution is not None:
            if (
                resolution.get("comparison_id") == comparison.get("comparison_id")
                and resolution.get("comparison_hash") == comparison_hash
            ):
                return HandlerResult("IDEMPOTENT", "comparison already applied")
            return self._lineage_blocked(
                step="compare-versions",
                detail="edit attempt already has a different comparison",
                context={
                    "edit_attempt_id": attempt_id,
                    "existing_comparison_id": resolution.get("comparison_id"),
                    "comparison_id": comparison.get("comparison_id"),
                },
            )
        plan = self.artifacts.latest("revision-plan")
        if (
            plan is None
            or attempt.get("revision_plan_id") != plan.get("revision_plan_id")
            or attempt.get("defect_id") != plan.get("defect_id")
            or comparison.get("target_defect_id") != attempt.get("defect_id")
        ):
            return self._lineage_blocked(
                step="compare-versions",
                detail="edit attempt does not match the active revision plan",
                context={
                    "edit_attempt_id": attempt_id,
                    "attempt_revision_plan_id": attempt.get("revision_plan_id"),
                    "active_revision_plan_id": (
                        plan.get("revision_plan_id") if plan else None
                    ),
                    "attempt_defect_id": attempt.get("defect_id"),
                    "comparison_defect_id": comparison.get("target_defect_id"),
                },
            )
        outcome = comparison["outcome"]
        parent = str(comparison["parent_version_id"])
        child = str(comparison["child_version_id"])
        state = self.state_store.load()
        if parent != attempt.get("parent_version_id"):
            return self._lineage_blocked(
                step="compare-versions",
                detail="comparison parent does not match edit attempt",
                context={
                    "comparison_parent_version_id": parent,
                    "attempt_parent_version_id": attempt.get("parent_version_id"),
                },
            )
        if child != attempt.get("child_version_id"):
            return self._lineage_blocked(
                step="compare-versions",
                detail="comparison child does not match edit attempt",
                context={
                    "comparison_child_version_id": child,
                    "attempt_child_version_id": attempt.get("child_version_id"),
                },
            )
        try:
            parent_version = self.versions.get(parent)
            child_version = self.versions.get(child)
        except UnknownVersionError as exc:
            return self._lineage_blocked(
                step="compare-versions",
                detail="comparison references a version that does not exist",
                context={"version_id": str(exc)},
            )
        if parent_version.version_id != parent or child_version.parent_version_id != parent:
            return self._lineage_blocked(
                step="compare-versions",
                detail="comparison child is not a child of its parent",
                context={
                    "parent_version_id": parent,
                    "child_version_id": child,
                    "actual_parent_version_id": child_version.parent_version_id,
                },
            )
        if state["current_version_id"] != parent:
            return self._lineage_blocked(
                step="compare-versions",
                detail="comparison parent is not current",
                context={
                    "parent_version_id": parent,
                    "current_version_id": state["current_version_id"],
                },
            )
        regressions = comparison["regressions"]
        accepted = (
            outcome == "ACCEPTED"
            and comparison["protected_elements_preserved"] is True
            and not regressions
        )
        if accepted:
            remaining = comparison["remaining_defects"]
            critical = sum(
                1 for item in remaining if item.get("severity") == "CRITICAL"
            )
            major = sum(1 for item in remaining if item.get("severity") == "MAJOR")
            self.versions.set_current(child)
            self.state_store.transition(
                "COMPARISON_ACCEPTED",
                {
                    "version_id": child,
                    "critical": critical,
                    "major": major,
                },
                event_id=f"transition:{correlation_id}",
            )
        else:
            self.state_store.transition(
                "COMPARISON_REJECTED",
                event_id=f"transition:{correlation_id}",
            )
        return HandlerResult()

    def _knowledge(self) -> dict:
        if self.knowledge_path.exists():
            return read_json(self.knowledge_path)
        return {
            "schema_version": "1.0",
            "track_id": self.track_id,
            "created_at": self.clock(),
            "captured_decision_ids": [],
            "cases": [],
        }

    def _capture_decision(
        self,
        knowledge_case: Mapping[str, object],
        correlation_id: str,
    ) -> None:
        decision = self.decisions.current()
        if not decision:
            # Final track knowledge can be captured without another human decision.
            return
        if knowledge_case.get("decision_id") != decision["decision_id"]:
            raise StepExecutionError("knowledge case decision_id mismatch")
        clear = self._apply_decision(decision, correlation_id)
        knowledge = self._knowledge()
        decision_id = str(decision["decision_id"])
        if decision_id not in knowledge["captured_decision_ids"]:
            knowledge["cases"].append(copy.deepcopy(dict(knowledge_case)))
            knowledge["captured_decision_ids"].append(decision_id)
            atomic_write_json(
                self.knowledge_path,
                _validate_snapshot(knowledge, "cases"),
            )
        if clear:
            self.decisions.clear_current(decision_id)

    def _apply_decision(
        self,
        decision: Mapping[str, object],
        correlation_id: str,
    ) -> bool:
        verdict = str(decision["verdict"])
        state = self.state_store.load()
        clear = True
        if verdict == "APPROVE_PACKAGE":
            package = self.artifacts.latest("song-package") or {}
            if decision.get("song_package_version_id") != package.get("version_id"):
                raise StepExecutionError("decision references a different song package")
            self.state_store.transition(
                "PACKAGE_APPROVED",
                event_id=f"transition:{correlation_id}",
            )
        elif verdict == "CHANGE_LYRICS":
            self._invalidate(
                "lyrics",
                "lyrics-review",
                "sound-direction",
                "package-review",
                "song-package",
                "generation-request",
                "candidates",
                "candidate-review",
                reason=verdict,
            )
            self.state_store.transition(
                "RETURN_TO_LYRICS",
                event_id=f"transition:{correlation_id}",
            )
        elif verdict in {"CHANGE_PRODUCTION", "COMBINE_DIRECTION"}:
            self._invalidate(
                "sound-direction",
                "package-review",
                "song-package",
                "generation-request",
                "candidates",
                "candidate-review",
                reason=verdict,
            )
            self.state_store.transition(
                "RETURN_TO_PRODUCTION",
                event_id=f"transition:{correlation_id}",
            )
        elif verdict == "REGENERATE_BATCH":
            self._invalidate(
                "generation-request",
                "candidates",
                "candidate-review",
                reason=verdict,
            )
            self.state_store.transition(
                "REGENERATE",
                event_id=f"transition:{correlation_id}",
            )
        elif verdict == "SELECT_AS_BASE":
            candidates = self.artifacts.latest("candidates") or {}
            candidate = next(
                (
                    item
                    for item in candidates.get("candidates", [])
                    if item.get("candidate_id") == decision.get("candidate_id")
                ),
                None,
            )
            if candidate is None:
                raise StepExecutionError("selected candidate is not in the batch")
            version_id = str(candidate["version_id"])
            self.versions.set_current(version_id)
            self.state_store.transition(
                "BASE_SELECTED",
                {"version_id": version_id},
                event_id=f"transition:{correlation_id}",
            )
        elif verdict == "RETRY_REVISION":
            self._invalidate(
                "revision-plan",
                "edit-attempt",
                "version-comparison",
                reason=verdict,
            )
            clear = False
        elif verdict == "ROLLBACK":
            current_id = self.versions.current_version_id
            requested_id = str(decision["version_id"])
            if current_id == requested_id:
                version_id = requested_id
            else:
                current = self.versions.get(str(current_id))
                if current.parent_version_id != requested_id:
                    raise StepExecutionError(
                        "rollback decision must reference the current parent"
                    )
                version_id = self.versions.rollback()
            self.state_store.transition(
                "ROLLBACK",
                {"version_id": version_id},
                event_id=f"transition:{correlation_id}",
            )
            self._invalidate(
                "revision-plan",
                "edit-attempt",
                "version-comparison",
                reason=verdict,
            )
        elif verdict == "REQUEST_REVISION":
            if decision.get("version_id") != state["current_version_id"]:
                raise StepExecutionError("revision request references a stale version")
            self.state_store.transition(
                "REQUEST_REVISION",
                event_id=f"transition:{correlation_id}",
            )
            clear = False
        elif verdict == "ACCEPT_REVISION":
            if decision.get("version_id") != state["current_version_id"]:
                raise StepExecutionError("accepted revision is not current")
            clear = False
        elif verdict == "APPROVE_FINAL":
            if decision.get("version_id") != state["current_version_id"]:
                raise StepExecutionError("final approval references a stale version")
            self.state_store.transition(
                "APPROVE_FINAL",
                event_id=f"transition:{correlation_id}",
            )
        elif verdict == "STOP":
            self.state_store.transition(
                "PAUSE",
                event_id=f"transition:{correlation_id}",
            )
        else:
            raise StepExecutionError(f"unsupported decision verdict: {verdict}")
        return clear

    def _final_qc(self) -> HandlerResult:
        state = self.state_store.load()
        version_id = state["current_version_id"]
        if not isinstance(version_id, str):
            raise StepExecutionError("final QC requires current version")
        result = dict(
            self.technical_qc.analyze(
                track_id=self.track_id,
                version=self.versions.get(version_id),
            )
        )
        if result.get("analyzer") != "mock":
            raise StepExecutionError("Prompt 5 accepts only injected mock QC")
        self._write_artifact("technical-qc", result)
        if str(result.get("result")).lower() == "pass":
            self.state_store.transition(
                "FINAL_QC_PASSED",
                event_id=f"transition:final-qc:{version_id}:pass",
            )
        else:
            self.state_store.transition(
                "FINAL_QC_FAILED",
                event_id=f"transition:final-qc:{version_id}:fail",
            )
        current = self.decisions.current()
        if current.get("verdict") == "ACCEPT_REVISION":
            self.decisions.clear_current(str(current["decision_id"]))
        return HandlerResult()

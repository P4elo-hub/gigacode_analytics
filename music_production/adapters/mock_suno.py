"""Deterministic offline stand-in for a generated-audio provider."""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Mapping, Optional, Tuple

from jsonschema import Draft202012Validator, FormatChecker

from music_production.adapters.base import (
    AudioGenerationAdapter,
    AudioGenerationResult,
    AudioOutput,
    IdempotencyConflictError,
    JobNotFoundError,
    JobStatus,
    NetworkError,
    ResultNotReadyError,
)
from music_production.adapters.capabilities import CapabilityRegistry


GENERATION_REQUEST_SCHEMA = (
    Path(__file__).resolve().parents[1]
    / "contracts"
    / "generation-request.schema.json"
)


@dataclass(frozen=True)
class MockScenario:
    statuses: Tuple[JobStatus, ...] = (JobStatus.SUCCEEDED,)
    status_network_failures: int = 0
    lose_first_submit_response: bool = False
    error_code: Optional[str] = None


@dataclass
class _MockJob:
    job_id: str
    request: dict
    request_fingerprint: str
    scenario: MockScenario
    status_index: int = 0
    status_failures_remaining: int = 0
    submit_response_lost: bool = False
    cancelled: bool = False


class MockSunoAdapter(AudioGenerationAdapter):
    """No-network adapter with reproducible jobs, failures, and outputs."""

    def __init__(
        self,
        capabilities: CapabilityRegistry,
        scenarios: Optional[Mapping[str, MockScenario]] = None,
    ) -> None:
        self.capabilities = capabilities
        self._scenarios = dict(scenarios or {})
        self._jobs: Dict[str, _MockJob] = {}
        self._job_by_key: Dict[str, str] = {}
        self.submit_calls = 0

    @property
    def job_count(self) -> int:
        return len(self._jobs)

    def _validate_request(self, request: Mapping[str, object]) -> dict:
        schema = json.loads(GENERATION_REQUEST_SCHEMA.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        document = copy.deepcopy(dict(request))
        Draft202012Validator(
            schema,
            format_checker=FormatChecker(),
        ).validate(document)
        return document

    @staticmethod
    def _fingerprint(request: Mapping[str, object]) -> str:
        payload = json.dumps(
            request,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _job_id(idempotency_key: str) -> str:
        digest = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()[:20]
        return f"mock-job-{digest}"

    def submit(
        self,
        request: Mapping[str, object],
        *,
        idempotency_key: str,
    ) -> str:
        self.submit_calls += 1
        document = dict(request)
        document["idempotency_key"] = idempotency_key
        document = self._validate_request(document)
        self.capabilities.require(str(document["operation"]))
        fingerprint = self._fingerprint(document)

        existing_id = self._job_by_key.get(idempotency_key)
        if existing_id is not None:
            existing = self._jobs[existing_id]
            if existing.request_fingerprint != fingerprint:
                raise IdempotencyConflictError(
                    "idempotency key was reused with a different request"
                )
            return existing_id

        scenario = self._scenarios.get(idempotency_key, MockScenario())
        if not scenario.statuses:
            raise ValueError("mock scenario must contain at least one status")
        job_id = self._job_id(idempotency_key)
        job = _MockJob(
            job_id=job_id,
            request=document,
            request_fingerprint=fingerprint,
            scenario=scenario,
            status_failures_remaining=scenario.status_network_failures,
        )
        self._jobs[job_id] = job
        self._job_by_key[idempotency_key] = job_id
        if scenario.lose_first_submit_response:
            job.submit_response_lost = True
            raise NetworkError(
                "mock submit response was lost after job creation",
                job_created=True,
            )
        return job_id

    def _job(self, job_id: str) -> _MockJob:
        try:
            return self._jobs[job_id]
        except KeyError as exc:
            raise JobNotFoundError(job_id) from exc

    def get_status(self, job_id: str) -> JobStatus:
        job = self._job(job_id)
        if job.cancelled:
            return JobStatus.CANCELLED
        if job.status_failures_remaining:
            job.status_failures_remaining -= 1
            raise NetworkError("mock status transport failure")
        statuses = job.scenario.statuses
        status = statuses[min(job.status_index, len(statuses) - 1)]
        if job.status_index < len(statuses) - 1:
            job.status_index += 1
        return status

    def get_result(self, job_id: str) -> AudioGenerationResult:
        job = self._job(job_id)
        status = self.get_status(job_id)
        if status == JobStatus.FAILED:
            return AudioGenerationResult(
                job_id=job_id,
                status=status,
                outputs=(),
                error_code=job.scenario.error_code or "PROVIDER_FAILURE",
            )
        if status != JobStatus.SUCCEEDED:
            raise ResultNotReadyError(f"job {job_id} is {status.value}")
        output_digest = hashlib.sha256(job_id.encode("utf-8")).hexdigest()
        output = AudioOutput(
            provider_output_id=f"mock-output-{output_digest[:16]}",
            audio_uri=f"mock://audio/{job_id}.wav",
            checksum=output_digest,
        )
        return AudioGenerationResult(
            job_id=job_id,
            status=status,
            outputs=(output,),
        )

    def cancel(self, job_id: str) -> JobStatus:
        job = self._job(job_id)
        current = (
            JobStatus.CANCELLED
            if job.cancelled
            else job.scenario.statuses[
                min(job.status_index, len(job.scenario.statuses) - 1)
            ]
        )
        if current.terminal:
            return current
        job.cancelled = True
        return JobStatus.CANCELLED

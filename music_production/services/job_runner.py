"""Run provider jobs without mixing transport retries and creative attempts."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Mapping, Optional
from uuid import uuid4

from music_production.adapters.base import (
    AudioGenerationAdapter,
    AudioGenerationResult,
    JobStatus,
    NetworkError,
)
from music_production.services.budget_guard import (
    BudgetDecision,
    BudgetGuard,
    BudgetUsage,
)


class JobRunOutcome(str, Enum):
    SUCCEEDED = "SUCCEEDED"
    PROVIDER_FAILED = "PROVIDER_FAILED"
    TIMED_OUT = "TIMED_OUT"
    CANCELLED = "CANCELLED"
    NETWORK_RETRY_EXHAUSTED = "NETWORK_RETRY_EXHAUSTED"
    REVISION_ESCALATION = "REVISION_ESCALATION"


@dataclass(frozen=True)
class JobRunResult:
    outcome: JobRunOutcome
    idempotency_key: Optional[str] = None
    job_id: Optional[str] = None
    provider_result: Optional[AudioGenerationResult] = None
    budget_decision: Optional[BudgetDecision] = None
    network_retries: int = 0


class JobRunner:
    """Own retries and accounting, but never operation selection."""

    def __init__(
        self,
        adapter: AudioGenerationAdapter,
        budget_guard: BudgetGuard,
        *,
        max_network_retries: int = 2,
        max_status_polls: int = 20,
        backoff: Callable[[float], None] = lambda _delay: None,
        key_factory: Callable[[], str] = lambda: str(uuid4()),
    ) -> None:
        if max_network_retries < 0 or max_status_polls < 1:
            raise ValueError("retry limits must be non-negative and polls positive")
        self.adapter = adapter
        self.budget_guard = budget_guard
        self.max_network_retries = max_network_retries
        self.max_status_polls = max_status_polls
        self.backoff = backoff
        self.key_factory = key_factory
        self.creative_attempts = 0

    def run_creative_attempt(
        self,
        request: Mapping[str, object],
        usage: BudgetUsage,
    ) -> JobRunResult:
        reservation_result = self.budget_guard.reserve(usage)
        if not reservation_result.decision.allowed:
            return JobRunResult(
                outcome=JobRunOutcome.REVISION_ESCALATION,
                budget_decision=reservation_result.decision,
            )
        reservation = reservation_result.reservation
        assert reservation is not None

        idempotency_key = self.key_factory()
        request_document = copy.deepcopy(dict(request))
        request_document["idempotency_key"] = idempotency_key
        retries = 0
        job_id = None
        while True:
            try:
                job_id = self.adapter.submit(
                    request_document,
                    idempotency_key=idempotency_key,
                )
                break
            except NetworkError as exc:
                retries += 1
                if retries > self.max_network_retries:
                    if exc.job_created:
                        self.budget_guard.commit(reservation.reservation_id)
                        self.creative_attempts += 1
                    else:
                        self.budget_guard.release(reservation.reservation_id)
                    return JobRunResult(
                        outcome=JobRunOutcome.NETWORK_RETRY_EXHAUSTED,
                        idempotency_key=idempotency_key,
                        network_retries=retries,
                    )
                self.backoff(float(2 ** (retries - 1)))

        self.budget_guard.commit(reservation.reservation_id)
        self.creative_attempts += 1

        for _ in range(self.max_status_polls):
            status, added_retries = self._status_with_retry(job_id)
            retries += added_retries
            if status is None:
                return JobRunResult(
                    outcome=JobRunOutcome.NETWORK_RETRY_EXHAUSTED,
                    idempotency_key=idempotency_key,
                    job_id=job_id,
                    network_retries=retries,
                )
            if status in {JobStatus.QUEUED, JobStatus.RUNNING}:
                continue
            if status == JobStatus.SUCCEEDED:
                provider_result, added_retries = self._result_with_retry(job_id)
                retries += added_retries
                if provider_result is None:
                    return JobRunResult(
                        outcome=JobRunOutcome.NETWORK_RETRY_EXHAUSTED,
                        idempotency_key=idempotency_key,
                        job_id=job_id,
                        network_retries=retries,
                    )
                return JobRunResult(
                    outcome=JobRunOutcome.SUCCEEDED,
                    idempotency_key=idempotency_key,
                    job_id=job_id,
                    provider_result=provider_result,
                    network_retries=retries,
                )
            if status == JobStatus.FAILED:
                return JobRunResult(
                    outcome=JobRunOutcome.PROVIDER_FAILED,
                    idempotency_key=idempotency_key,
                    job_id=job_id,
                    network_retries=retries,
                )
            if status == JobStatus.CANCELLED:
                return JobRunResult(
                    outcome=JobRunOutcome.CANCELLED,
                    idempotency_key=idempotency_key,
                    job_id=job_id,
                    network_retries=retries,
                )
            if status == JobStatus.TIMED_OUT:
                return JobRunResult(
                    outcome=JobRunOutcome.TIMED_OUT,
                    idempotency_key=idempotency_key,
                    job_id=job_id,
                    network_retries=retries,
                )

        return JobRunResult(
            outcome=JobRunOutcome.TIMED_OUT,
            idempotency_key=idempotency_key,
            job_id=job_id,
            network_retries=retries,
        )

    def _status_with_retry(
        self,
        job_id: str,
    ) -> tuple[Optional[JobStatus], int]:
        retries = 0
        while True:
            try:
                return self.adapter.get_status(job_id), retries
            except NetworkError:
                retries += 1
                if retries > self.max_network_retries:
                    return None, retries
                self.backoff(float(2 ** (retries - 1)))
    def _result_with_retry(
        self,
        job_id: str,
    ) -> tuple[Optional[AudioGenerationResult], int]:
        retries = 0
        while True:
            try:
                return self.adapter.get_result(job_id), retries
            except NetworkError:
                retries += 1
                if retries > self.max_network_retries:
                    return None, retries
                self.backoff(float(2 ** (retries - 1)))

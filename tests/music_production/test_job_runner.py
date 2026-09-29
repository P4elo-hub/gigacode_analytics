#!/usr/bin/env python3
"""JobRunner transport retries and creative-attempt accounting."""

from __future__ import annotations

import json
import unittest
from decimal import Decimal
from pathlib import Path

from music_production.adapters.base import (
    AudioGenerationAdapter,
    JobStatus,
    NetworkError,
)
from music_production.adapters.capabilities import CapabilityRegistry
from music_production.adapters.mock_suno import MockScenario, MockSunoAdapter
from music_production.services.budget_guard import (
    BudgetGuard,
    BudgetLimits,
    BudgetUsage,
)
from music_production.services.job_runner import JobRunOutcome, JobRunner


FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "music_production"
    / "fixtures"
    / "sample-generation-request.json"
)


def request() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def guard(max_batch: int = 10) -> BudgetGuard:
    return BudgetGuard(
        BudgetLimits(
            max_batch=max_batch,
            max_defect_fix_attempts=10,
            max_iterations=10,
            max_api_wait_seconds=1000,
            max_cost=Decimal("100"),
        )
    )


USAGE = BudgetUsage(
    generation_batches=1,
    iterations=1,
    api_wait_seconds=10,
    cost=Decimal("1.00"),
)


class _PreSubmitNetworkFailure(AudioGenerationAdapter):
    def submit(self, request, *, idempotency_key):
        raise NetworkError("provider did not receive request", job_created=False)

    def get_status(self, job_id):
        raise AssertionError("no job")

    def get_result(self, job_id):
        raise AssertionError("no job")

    def cancel(self, job_id):
        raise AssertionError("no job")


class JobRunnerTest(unittest.TestCase):
    def adapter(self, key: str, scenario: MockScenario) -> MockSunoAdapter:
        return MockSunoAdapter(
            CapabilityRegistry({"generate-batch"}),
            {key: scenario},
        )

    def test_network_retry_does_not_create_creative_attempt(self) -> None:
        key = "retry-key"
        adapter = self.adapter(
            key,
            MockScenario(status_network_failures=2),
        )
        budget = guard()
        runner = JobRunner(
            adapter,
            budget,
            max_network_retries=2,
            key_factory=lambda: key,
        )
        result = runner.run_creative_attempt(request(), USAGE)
        self.assertEqual(result.outcome, JobRunOutcome.SUCCEEDED)
        self.assertEqual(result.network_retries, 2)
        self.assertEqual(runner.creative_attempts, 1)
        self.assertEqual(adapter.job_count, 1)
        self.assertEqual(budget.committed.generation_batches, 1)

    def test_lost_submit_response_reuses_same_provider_job(self) -> None:
        key = "lost-response"
        adapter = self.adapter(
            key,
            MockScenario(lose_first_submit_response=True),
        )
        runner = JobRunner(
            adapter,
            guard(),
            max_network_retries=1,
            key_factory=lambda: key,
        )
        result = runner.run_creative_attempt(request(), USAGE)
        self.assertEqual(result.outcome, JobRunOutcome.SUCCEEDED)
        self.assertEqual(adapter.job_count, 1)
        self.assertEqual(runner.creative_attempts, 1)

    def test_provider_failure_is_not_network_failure(self) -> None:
        key = "provider-failure"
        runner = JobRunner(
            self.adapter(
                key,
                MockScenario(statuses=(JobStatus.FAILED,)),
            ),
            guard(),
            key_factory=lambda: key,
        )
        result = runner.run_creative_attempt(request(), USAGE)
        self.assertEqual(result.outcome, JobRunOutcome.PROVIDER_FAILED)
        self.assertEqual(result.network_retries, 0)

    def test_retry_exhaustion(self) -> None:
        key = "retry-exhausted"
        runner = JobRunner(
            self.adapter(
                key,
                MockScenario(status_network_failures=3),
            ),
            guard(),
            max_network_retries=1,
            key_factory=lambda: key,
        )
        result = runner.run_creative_attempt(request(), USAGE)
        self.assertEqual(result.outcome, JobRunOutcome.NETWORK_RETRY_EXHAUSTED)
        self.assertEqual(result.network_retries, 2)

    def test_timeout(self) -> None:
        key = "timeout"
        runner = JobRunner(
            self.adapter(
                key,
                MockScenario(statuses=(JobStatus.TIMED_OUT,)),
            ),
            guard(),
            key_factory=lambda: key,
        )
        self.assertEqual(
            runner.run_creative_attempt(request(), USAGE).outcome,
            JobRunOutcome.TIMED_OUT,
        )

    def test_backoff_is_injected_without_sleep(self) -> None:
        key = "backoff"
        delays = []
        runner = JobRunner(
            self.adapter(
                key,
                MockScenario(status_network_failures=2),
            ),
            guard(),
            max_network_retries=2,
            backoff=delays.append,
            key_factory=lambda: key,
        )
        runner.run_creative_attempt(request(), USAGE)
        self.assertEqual(delays, [1.0, 2.0])

    def test_pre_submit_technical_failure_releases_reservation(self) -> None:
        budget = guard()
        runner = JobRunner(
            _PreSubmitNetworkFailure(),
            budget,
            max_network_retries=0,
            key_factory=lambda: "not-created",
        )
        result = runner.run_creative_attempt(request(), USAGE)
        self.assertEqual(result.outcome, JobRunOutcome.NETWORK_RETRY_EXHAUSTED)
        self.assertEqual(budget.committed, BudgetUsage())
        self.assertEqual(budget.reserved, BudgetUsage())
        self.assertEqual(runner.creative_attempts, 0)

    def test_each_creative_attempt_gets_new_key_without_changing_operation(self) -> None:
        keys = iter(("creative-one", "creative-two"))
        adapter = MockSunoAdapter(CapabilityRegistry({"generate-batch"}))
        runner = JobRunner(adapter, guard(), key_factory=lambda: next(keys))
        document = request()
        first = runner.run_creative_attempt(document, USAGE)
        second = runner.run_creative_attempt(document, USAGE)
        self.assertNotEqual(first.idempotency_key, second.idempotency_key)
        self.assertEqual(adapter.job_count, 2)
        self.assertEqual(document["operation"], "generate-batch")
        self.assertEqual(runner.creative_attempts, 2)

    def test_budget_escalation_prevents_submit(self) -> None:
        adapter = MockSunoAdapter(CapabilityRegistry({"generate-batch"}))
        runner = JobRunner(adapter, guard(max_batch=0))
        result = runner.run_creative_attempt(request(), USAGE)
        self.assertEqual(result.outcome, JobRunOutcome.REVISION_ESCALATION)
        self.assertEqual(adapter.submit_calls, 0)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""CapabilityRegistry and offline MockSunoAdapter contract."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from music_production.adapters.base import (
    JobStatus,
    NetworkError,
    ResultNotReadyError,
)
from music_production.adapters.capabilities import (
    CapabilityRegistry,
    UnsupportedCapabilityError,
)
from music_production.adapters.mock_suno import MockScenario, MockSunoAdapter


FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "music_production"
    / "fixtures"
    / "sample-generation-request.json"
)


def request() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class MockSunoAdapterContractTest(unittest.TestCase):
    def adapter(self, **scenarios: MockScenario) -> MockSunoAdapter:
        return MockSunoAdapter(
            CapabilityRegistry({"generate-batch", "replace-section"}),
            scenarios,
        )

    def test_supported_operation(self) -> None:
        adapter = self.adapter()
        job_id = adapter.submit(request(), idempotency_key="supported")
        self.assertTrue(job_id.startswith("mock-job-"))

    def test_unsupported_operation_returns_typed_error(self) -> None:
        adapter = self.adapter()
        document = request()
        document["operation"] = "remaster"
        with self.assertRaises(UnsupportedCapabilityError) as caught:
            adapter.submit(document, idempotency_key="unsupported")
        self.assertEqual(caught.exception.error.code, "CAPABILITY_UNAVAILABLE")
        self.assertEqual(adapter.job_count, 0)

    def test_same_idempotency_key_does_not_create_second_job(self) -> None:
        adapter = self.adapter()
        first = adapter.submit(request(), idempotency_key="same-key")
        second = adapter.submit(request(), idempotency_key="same-key")
        self.assertEqual(first, second)
        self.assertEqual(adapter.job_count, 1)

    def test_different_keys_create_different_jobs(self) -> None:
        adapter = self.adapter()
        first = adapter.submit(request(), idempotency_key="key-one")
        second = adapter.submit(request(), idempotency_key="key-two")
        self.assertNotEqual(first, second)
        self.assertEqual(adapter.job_count, 2)

    def test_success_returns_mock_uri_and_checksum_without_file(self) -> None:
        adapter = self.adapter()
        job_id = adapter.submit(request(), idempotency_key="success")
        result = adapter.get_result(job_id)
        self.assertEqual(result.status, JobStatus.SUCCEEDED)
        self.assertEqual(len(result.outputs), 1)
        self.assertTrue(result.outputs[0].audio_uri.startswith("mock://"))
        self.assertEqual(len(result.outputs[0].checksum), 64)

    def test_network_failure_is_distinct(self) -> None:
        adapter = self.adapter(
            network=MockScenario(status_network_failures=1)
        )
        job_id = adapter.submit(request(), idempotency_key="network")
        with self.assertRaises(NetworkError):
            adapter.get_status(job_id)
        self.assertEqual(adapter.get_status(job_id), JobStatus.SUCCEEDED)

    def test_provider_failure(self) -> None:
        adapter = self.adapter(
            provider=MockScenario(
                statuses=(JobStatus.FAILED,),
                error_code="MOCK_PROVIDER_FAILURE",
            )
        )
        job_id = adapter.submit(request(), idempotency_key="provider")
        self.assertEqual(adapter.get_status(job_id), JobStatus.FAILED)
        result = adapter.get_result(job_id)
        self.assertEqual(result.status, JobStatus.FAILED)
        self.assertEqual(result.error_code, "MOCK_PROVIDER_FAILURE")

    def test_timeout(self) -> None:
        adapter = self.adapter(
            timeout=MockScenario(statuses=(JobStatus.TIMED_OUT,))
        )
        job_id = adapter.submit(request(), idempotency_key="timeout")
        self.assertEqual(adapter.get_status(job_id), JobStatus.TIMED_OUT)
        with self.assertRaises(ResultNotReadyError):
            adapter.get_result(job_id)

    def test_cancel_non_terminal_job(self) -> None:
        adapter = self.adapter(
            cancel=MockScenario(
                statuses=(JobStatus.QUEUED, JobStatus.RUNNING)
            )
        )
        job_id = adapter.submit(request(), idempotency_key="cancel")
        self.assertEqual(adapter.cancel(job_id), JobStatus.CANCELLED)
        self.assertEqual(adapter.get_status(job_id), JobStatus.CANCELLED)

    def test_request_is_not_mutated(self) -> None:
        document = request()
        before = copy.deepcopy(document)
        self.adapter().submit(document, idempotency_key="not-mutated")
        self.assertEqual(document, before)


if __name__ == "__main__":
    unittest.main()

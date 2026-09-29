#!/usr/bin/env python3
"""AgentRuntime boundary and two-layer validation."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from music_production.runtime.base import ArtifactReference
from music_production.runtime.mock import MockAgentRuntime
from music_production.runtime.validation import (
    AgentArtifactMismatchError,
    InvalidArtifactError,
    InvalidEnvelopeError,
    UnknownAgentError,
    UnknownArtifactTypeError,
    validate_agent_result,
)


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "music_production" / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class AgentRuntimeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime = MockAgentRuntime.with_standard_outcomes()

    def run_fixture(self, fixture_name: str) -> dict:
        fixture = load_fixture(fixture_name)
        return dict(
            self.runtime.run(
                agent_id=fixture["agent_id"],
                step=fixture["step"],
                track_id=fixture["track_id"],
                input_artifacts=[ArtifactReference("artifact://input/1")],
                timeout=5,
                correlation_id="correlation-001",
            )
        )

    def test_valid_pass(self) -> None:
        self.assertEqual(
            self.run_fixture("sample-agent-result-pass.json")["outcome"],
            "PASS",
        )

    def test_valid_revise(self) -> None:
        result = self.run_fixture("sample-agent-result-revise.json")
        self.assertEqual(result["outcome"], "REVISE")
        self.assertTrue(result["issues"])

    def test_valid_blocked(self) -> None:
        result = self.run_fixture("sample-agent-result-blocked.json")
        self.assertEqual(result["outcome"], "BLOCKED")
        self.assertTrue(result["blocked_reason"])

    def test_prepared_result_can_be_injected(self) -> None:
        result = load_fixture("sample-agent-result-pass.json")
        runtime = MockAgentRuntime()
        runtime.set_result(result)
        actual = runtime.run(
            agent_id=result["agent_id"],
            step=result["step"],
            track_id=result["track_id"],
            input_artifacts=[],
            timeout=1,
            correlation_id="injected-result",
        )
        self.assertEqual(actual, result)

    def test_invalid_envelope_is_rejected(self) -> None:
        result = load_fixture("sample-agent-result-pass.json")
        result.pop("issues")
        with self.assertRaises(InvalidEnvelopeError):
            validate_agent_result(result)

    def test_invalid_artifact_is_rejected(self) -> None:
        result = load_fixture("sample-agent-result-pass.json")
        result["artifact"] = copy.deepcopy(result["artifact"])
        result["artifact"]["unknown_field"] = True
        with self.assertRaises(InvalidArtifactError):
            validate_agent_result(result)

    def test_wrong_agent_artifact_pair_is_rejected(self) -> None:
        result = load_fixture("sample-agent-result-pass.json")
        result["artifact_type"] = "sound-direction"
        with self.assertRaises(AgentArtifactMismatchError):
            validate_agent_result(result)

    def test_unknown_agent_and_artifact_are_rejected(self) -> None:
        result = load_fixture("sample-agent-result-pass.json")
        result["agent_id"] = "unknown-agent"
        with self.assertRaises(UnknownAgentError):
            validate_agent_result(result)
        result = load_fixture("sample-agent-result-pass.json")
        result["artifact_type"] = "unknown-artifact"
        with self.assertRaises(UnknownArtifactTypeError):
            validate_agent_result(result)

    def test_core_has_no_gigacode_cli_dependency(self) -> None:
        package = ROOT / "music_production"
        core_files = (
            list((package / "runtime").glob("*.py"))
            + list((package / "adapters").glob("*.py"))
            + list((package / "services").glob("*.py"))
        )
        for path in core_files:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8").lower()
                self.assertNotIn("import gigacode", text)
                self.assertNotIn("subprocess", text)


if __name__ == "__main__":
    unittest.main()

"""Deterministic, offline agent runtime for contract tests."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Mapping, MutableMapping, Optional, Sequence, Tuple

from music_production.runtime.base import (
    AgentRuntime,
    ArtifactInput,
    ArtifactReference,
)
from music_production.runtime.validation import validate_agent_result


FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"


class MockResultNotConfiguredError(LookupError):
    """No deterministic response was configured for a request."""


class MockAgentRuntime(AgentRuntime):
    """Return configured envelopes without invoking a CLI or network."""

    def __init__(
        self,
        results: Optional[
            Mapping[Tuple[str, str], Mapping[str, object]]
        ] = None,
    ) -> None:
        self._results: MutableMapping[Tuple[str, str], dict] = {
            key: copy.deepcopy(dict(value))
            for key, value in (results or {}).items()
        }

    @classmethod
    def with_standard_outcomes(cls) -> "MockAgentRuntime":
        """Build the three deterministic PASS/REVISE/BLOCKED examples."""

        fixtures = (
            "sample-agent-result-pass.json",
            "sample-agent-result-revise.json",
            "sample-agent-result-blocked.json",
        )
        results = {}
        for fixture_name in fixtures:
            result = json.loads(
                (FIXTURES_DIR / fixture_name).read_text(encoding="utf-8")
            )
            results[(result["agent_id"], result["step"])] = result
        return cls(results)

    def set_result(self, result: Mapping[str, object]) -> None:
        """Install a prepared result after validating both schema layers."""

        validated = validate_agent_result(result)
        self._results[(validated["agent_id"], validated["step"])] = copy.deepcopy(
            validated
        )

    def run(
        self,
        *,
        agent_id: str,
        step: str,
        track_id: str,
        input_artifacts: Sequence[ArtifactInput],
        timeout: float,
        correlation_id: str,
    ) -> Mapping[str, object]:
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        if not correlation_id:
            raise ValueError("correlation_id is required")
        for reference in input_artifacts:
            if not isinstance(reference, (ArtifactReference, Path, str)):
                raise TypeError(
                    "input_artifacts must contain paths, strings, or references"
                )

        key = (agent_id, step)
        if key not in self._results:
            raise MockResultNotConfiguredError(f"no result configured for {key}")
        result = copy.deepcopy(self._results[key])
        if result.get("track_id") != track_id:
            raise ValueError("configured result track_id does not match request")
        return validate_agent_result(result)

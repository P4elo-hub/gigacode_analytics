"""Two-layer validation for music agent results."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError


CONTRACTS_DIR = Path(__file__).resolve().parents[1] / "contracts"

AGENT_ARTIFACT_TYPES = {
    "music-brief-analyst": "brief",
    "music-lyrics-writer": "lyrics",
    "music-lyrics-editor": "lyrics-review",
    "music-sound-director": "sound-direction",
    "music-package-reviewer": "package-review",
    "music-suno-prompt-compiler": "generation-request",
    "music-candidate-critic": "candidate-review",
    "music-defect-diagnostician": "defect",
    "music-revision-planner": "revision-plan",
    "music-version-comparator": "version-comparison",
    "music-knowledge-capturer": "knowledge-case",
}

ARTIFACT_SCHEMAS = {
    artifact_type: CONTRACTS_DIR / f"{artifact_type}.schema.json"
    for artifact_type in set(AGENT_ARTIFACT_TYPES.values())
}


class AgentResultValidationError(ValueError):
    """Base class for invalid runtime results."""


class UnknownAgentError(AgentResultValidationError):
    """The result names an agent outside the runtime contract."""


class UnknownArtifactTypeError(AgentResultValidationError):
    """The result names an artifact type without a registered schema."""


class AgentArtifactMismatchError(AgentResultValidationError):
    """The agent is not allowed to produce this artifact type."""


class InvalidEnvelopeError(AgentResultValidationError):
    """The agent-result envelope violates its JSON Schema."""


class InvalidArtifactError(AgentResultValidationError):
    """The embedded artifact violates its JSON Schema."""


def _load_schema(path: Path) -> dict:
    schema = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return schema


def _validator(path: Path) -> Draft202012Validator:
    return Draft202012Validator(
        _load_schema(path),
        format_checker=FormatChecker(),
    )


def validate_agent_result(result: Mapping[str, object]) -> dict:
    """Validate the envelope, producer/type pair, and embedded artifact."""

    document = dict(result)
    agent_id = document.get("agent_id")
    artifact_type = document.get("artifact_type")
    if isinstance(agent_id, str) and agent_id not in AGENT_ARTIFACT_TYPES:
        raise UnknownAgentError(str(agent_id))
    if isinstance(artifact_type, str) and artifact_type not in ARTIFACT_SCHEMAS:
        raise UnknownArtifactTypeError(str(artifact_type))
    if isinstance(agent_id, str) and isinstance(artifact_type, str):
        expected = AGENT_ARTIFACT_TYPES[agent_id]
        if artifact_type != expected:
            raise AgentArtifactMismatchError(
                f"{agent_id} must produce {expected}, got {artifact_type}"
            )
    try:
        _validator(CONTRACTS_DIR / "agent-result.schema.json").validate(document)
    except ValidationError as exc:
        raise InvalidEnvelopeError(exc.message) from exc

    artifact = document["artifact"]
    if artifact is not None:
        try:
            _validator(ARTIFACT_SCHEMAS[artifact_type]).validate(artifact)
        except ValidationError as exc:
            raise InvalidArtifactError(exc.message) from exc
    return document

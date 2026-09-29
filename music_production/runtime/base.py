"""Provider-neutral boundary for executing one music agent."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence, Union


@dataclass(frozen=True)
class ArtifactReference:
    """A checked local path or an opaque artifact reference."""

    value: Union[Path, str]


ArtifactInput = Union[ArtifactReference, Path, str]


class AgentRuntime(ABC):
    """Execute an agent without exposing provider or pipeline internals."""

    @abstractmethod
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
        """Return a validated agent-result envelope."""

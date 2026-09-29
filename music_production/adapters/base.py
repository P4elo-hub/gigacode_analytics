"""Provider-neutral generated-audio adapter contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Optional, Tuple


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"

    @property
    def terminal(self) -> bool:
        return self in {
            JobStatus.SUCCEEDED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
            JobStatus.TIMED_OUT,
        }


@dataclass(frozen=True)
class AudioOutput:
    provider_output_id: str
    audio_uri: str
    checksum: str


@dataclass(frozen=True)
class AudioGenerationResult:
    job_id: str
    status: JobStatus
    outputs: Tuple[AudioOutput, ...]
    error_code: Optional[str] = None


class AudioAdapterError(RuntimeError):
    """Base class for typed adapter failures."""


class NetworkError(AudioAdapterError):
    """A retryable transport failure."""

    def __init__(self, message: str, *, job_created: bool = False) -> None:
        super().__init__(message)
        self.job_created = job_created


class JobNotFoundError(AudioAdapterError):
    """The provider job id is unknown."""


class ResultNotReadyError(AudioAdapterError):
    """A result was requested before successful completion."""


class IdempotencyConflictError(AudioAdapterError):
    """An idempotency key was reused with different request content."""


class AudioGenerationAdapter(ABC):
    @abstractmethod
    def submit(
        self,
        request: Mapping[str, object],
        *,
        idempotency_key: str,
    ) -> str:
        """Submit one provider operation and return its stable job id."""

    @abstractmethod
    def get_status(self, job_id: str) -> JobStatus:
        """Return current provider status."""

    @abstractmethod
    def get_result(self, job_id: str) -> AudioGenerationResult:
        """Return outputs for a successfully completed job."""

    @abstractmethod
    def cancel(self, job_id: str) -> JobStatus:
        """Cancel a non-terminal job."""

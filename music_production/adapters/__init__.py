"""Provider-neutral audio generation adapters."""

from music_production.adapters.base import (
    AudioGenerationAdapter,
    AudioGenerationResult,
    JobStatus,
)
from music_production.adapters.capabilities import CapabilityRegistry
from music_production.adapters.mock_suno import MockSunoAdapter

__all__ = [
    "AudioGenerationAdapter",
    "AudioGenerationResult",
    "CapabilityRegistry",
    "JobStatus",
    "MockSunoAdapter",
]

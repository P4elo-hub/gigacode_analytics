"""Open an existing music run with the same stores the orchestration tests use."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Optional

from music_production.adapters.capabilities import CapabilityRegistry
from music_production.adapters.mock_suno import MockSunoAdapter
from music_production.orchestration.engine import OrchestrationEngine
from music_production.orchestration.errors import InvalidTrackIdError
from music_production.orchestration.state_store import (
    TRACK_ID,
    read_json,
    validate_document,
    validate_track_id,
)
from music_production.orchestration.step_handlers import MockTechnicalQC
from music_production.runtime.mock import MockAgentRuntime

ENABLED_OPERATIONS = ("generate-batch", "replace-section")


class TrackNotFound(LookupError):
    """The track id is absent or not a safe directory inside the runs root."""


def _is_contained(root: Path, candidate: Path) -> bool:
    resolved_root = root.resolve()
    resolved = candidate.resolve()
    return resolved == resolved_root or resolved_root in resolved.parents


def list_track_ids(runs_root: Path) -> list[str]:
    """Safe track directory names that contain a valid track-state document."""

    root = Path(runs_root)
    if not root.exists() or not root.is_dir() or root.is_symlink():
        return []
    found = []
    for child in sorted(root.iterdir(), key=lambda item: item.name):
        if not _track_dir_is_safe(root, child):
            continue
        found.append(child.name)
    return found


def _track_dir_is_safe(root: Path, child: Path) -> bool:
    if child.is_symlink() or not child.is_dir():
        return False
    if not TRACK_ID.fullmatch(child.name):
        return False
    if not _is_contained(root, child) or child.resolve().parent != root.resolve():
        return False
    state_path = child / "track-state.json"
    if state_path.is_symlink() or not state_path.is_file():
        return False
    try:
        document = validate_document("track-state", read_json(state_path))
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    except Exception:
        return False
    return document.get("track_id") == child.name


def require_track_dir(runs_root: Path, track_id: str) -> Path:
    try:
        validate_track_id(track_id)
    except InvalidTrackIdError as exc:
        raise TrackNotFound(track_id) from exc
    root = Path(runs_root)
    child = root / track_id
    if not _track_dir_is_safe(root, child):
        raise TrackNotFound(track_id)
    return child


def open_engine(
    runs_root: Path,
    track_id: str,
    *,
    clock: Optional[Callable[[], str]] = None,
) -> OrchestrationEngine:
    """Build the offline engine for a track directory that already exists."""

    require_track_dir(runs_root, track_id)
    capabilities = CapabilityRegistry(ENABLED_OPERATIONS)
    kwargs = {
        "run_root": Path(runs_root),
        "track_id": track_id,
        "runtime": MockAgentRuntime(),
        "adapter": MockSunoAdapter(capabilities),
        "capabilities": capabilities,
        "technical_qc": MockTechnicalQC(
            {"result": "pass", "facts": {"listened": False}}
        ),
    }
    if clock is not None:
        kwargs["clock"] = clock
    return OrchestrationEngine(**kwargs)


def prepare_capture_runtime(engine: OrchestrationEngine, decision: dict) -> None:
    """Give the mock runtime the echo the capture step already requires.

    The handler discards this artifact and assembles the case from the
    committed decision. The runtime still needs a schema-valid envelope.
    """

    stamp = str(decision["created_at"])
    artifact = {
        "schema_version": "1.0",
        "track_id": engine.track_id,
        "created_at": stamp,
        "case_id": f"echo-{decision['decision_id']}",
        "decision_id": decision["decision_id"],
        "gate": decision["gate"],
        "subject_type": "SONG_PACKAGE",
        "subject_id": "echo",
        "version_before_id": None,
        "defect_id": None,
        "proposed_action": None,
        "prompt_id": None,
        "result_version_id": None,
        "verdict": decision["verdict"],
        "decided_by": decision["decided_by"],
        "comment": decision.get("comment"),
        "captured_at": stamp,
        "evidence_refs": [],
        "technical_facts": [],
        "rule_status": "candidate_rule",
    }
    engine.handlers.runtime.set_result(
        {
            "schema_version": "1.0",
            "track_id": engine.track_id,
            "created_at": stamp,
            "agent_id": "music-knowledge-capturer",
            "step": "capture-knowledge",
            "outcome": "PASS",
            "artifact_type": "knowledge-case",
            "artifact": artifact,
            "issues": [],
            "blocked_reason": None,
        }
    )

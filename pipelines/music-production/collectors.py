"""Facts for music-production dispatch.

Reads track-state, brief, expert-decision, knowledge and routing-signals.
Does not choose the next step and does not increase revision_budget_remaining.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from music_production.orchestration.artifact_store import resolve_committed_artifact


def _read_object(path: Path | None) -> dict:
    if path is None or not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _count(value: object) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _captured_ids(knowledge: dict) -> set[str]:
    raw = knowledge.get("captured_decision_ids")
    if not isinstance(raw, list):
        return set()
    return {str(item) for item in raw if str(item)}


def track_signals(root: Path, task_id: str, status, paths: dict[str, Path] | None = None) -> None:
    paths = paths or {}
    index_path = paths.get("artifact_index")
    track_dir = (
        index_path.parent
        if index_path is not None
        else root / "Music-runs" / task_id
    )
    committed_types = {
        "brief": "has_brief",
        "lyrics": "has_lyrics",
        "sound-direction": "has_sound",
        "song-package": "has_package",
        "generation-request": "has_generation_request",
        "candidates": "has_candidates",
        "revision-plan": "has_revision_plan",
    }
    committed_paths = {}
    for artifact_type, status_field in committed_types.items():
        artifact_path = resolve_committed_artifact(track_dir, artifact_type)
        committed_paths[artifact_type] = artifact_path
        setattr(status, status_field, artifact_path is not None)
    brief = _read_object(committed_paths["brief"])
    track = _read_object(paths.get("track_state"))
    signals = _read_object(paths.get("routing_signals"))
    decision = _read_object(paths.get("expert_decision"))
    knowledge = _read_object(paths.get("knowledge"))
    status.state = _text(track.get("state"))
    status.revision_budget_remaining = _count(track.get("revision_budget_remaining"))
    status.open_blocking_defects = _count(track.get("open_critical_defects")) + _count(
        track.get("open_major_defects")
    )
    status.base_selected = bool(track.get("base_version_id"))
    status.lyrics_verdict = _text(signals.get("lyrics_verdict"))
    status.package_verdict = _text(signals.get("package_verdict"))
    status.revision_target = _text(signals.get("revision_target"))
    status.comparison_outcome = _text(signals.get("comparison_outcome"))
    status.qc_result = _text(signals.get("qc_result"))
    status.candidate_reviewed = bool(signals.get("candidate_reviewed"))
    status.edit_done = bool(signals.get("edit_done"))
    status.comparisons_without_improvement = _count(signals.get("comparisons_without_improvement"))
    required = _text(signals.get("required_operation"))
    available = signals.get("available_operations")
    if not isinstance(available, list):
        available = []
    status.capability_missing = bool(required) and required not in {str(item) for item in available}
    if brief:
        status.package_review_required = bool(brief.get("package_review_required", True))
        budget = brief.get("budget") if isinstance(brief.get("budget"), dict) else {}
        status.defect_fix_limit_exhausted = _count(signals.get("defect_fix_attempts")) >= _count(
            budget.get("max_defect_fix_attempts")
        )
    else:
        status.package_review_required = False
        status.defect_fix_limit_exhausted = False
    status.decision_id = _text(decision.get("decision_id"))
    status.decision_gate = _text(decision.get("gate"))
    status.decision_verdict = _text(decision.get("verdict"))
    status.decision_version_id = _text(decision.get("version_id"))
    status.decision_capture_pending = bool(status.decision_id) and (
        status.decision_id not in _captured_ids(knowledge)
    )
    captured_retry_closed = (
        status.decision_gate == "REVISION_ESCALATION"
        and status.decision_verdict == "RETRY_REVISION"
        and not status.decision_capture_pending
        and status.revision_budget_remaining <= 0
    )
    rollback_waiting = (
        status.decision_gate == "REVISION_ESCALATION"
        and status.decision_verdict == "ROLLBACK"
        and not status.decision_capture_pending
        and status.decision_version_id == ""
    )
    status.awaiting_human = bool(
        (
            status.state == "PACKAGE_READY"
            and status.package_review_required
            and status.package_verdict == "PASS"
            and status.decision_id == ""
        )
        or (status.state == "AWAITING_BASE_SELECTION" and status.decision_id == "")
        or (status.state == "AWAITING_FINAL_APPROVAL" and status.decision_id == "")
        or (
            status.state == "REVISING"
            and status.decision_id == ""
            and (
                status.revision_budget_remaining <= 0
                or status.defect_fix_limit_exhausted
                or status.comparisons_without_improvement >= 2
            )
        )
        or (status.capability_missing and status.decision_id == "")
        or captured_retry_closed
        or rollback_waiting
    )


COLLECTORS = {"track_signals": track_signals}

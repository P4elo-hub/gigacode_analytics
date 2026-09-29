"""Atomic run snapshots, idempotent events, and track-state transitions."""

from __future__ import annotations

import copy
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping, Optional

from jsonschema import Draft202012Validator, FormatChecker

from music_production.orchestration.errors import (
    InvalidTrackIdError,
    InvalidTransitionError,
)

CONTRACTS = Path(__file__).resolve().parents[1] / "contracts"
TRACK_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def validate_track_id(track_id: str) -> str:
    if (
        not TRACK_ID.fullmatch(track_id)
        or track_id in {".", ".."}
        or "/" in track_id
        or "\\" in track_id
    ):
        raise InvalidTrackIdError(track_id)
    return track_id


def load_schema(name: str) -> dict:
    schema = json.loads((CONTRACTS / f"{name}.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return schema


def validate_document(name: str, document: Mapping[str, object]) -> dict:
    value = copy.deepcopy(dict(document))
    Draft202012Validator(
        load_schema(name),
        format_checker=FormatChecker(),
    ).validate(value)
    return value


def atomic_write_json(
    path: Path,
    document: Mapping[str, object],
    *,
    before_replace: Optional[Callable[[Path], None]] = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(document, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        if before_replace is not None:
            before_replace(temporary)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def read_json(path: Path, default: Optional[dict] = None) -> dict:
    if not path.exists():
        return copy.deepcopy(default or {})
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path} contains a non-object record")
            records.append(value)
    return records


def append_event(
    path: Path,
    *,
    event_id: str,
    track_id: str,
    payload: Mapping[str, object],
    occurred_at: Optional[str] = None,
) -> bool:
    """Append one event unless event_id already exists."""

    records = read_jsonl(path)
    existing = next((item for item in records if item.get("event_id") == event_id), None)
    record = {
        "event_id": event_id,
        "occurred_at": occurred_at or utc_now(),
        "track_id": track_id,
        "payload": copy.deepcopy(dict(payload)),
    }
    if existing is not None:
        if existing != record and existing.get("payload") != record["payload"]:
            raise ValueError(f"event_id conflict: {event_id}")
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return True


def initial_state(track_id: str, *, created_at: Optional[str] = None) -> dict:
    return {
        "schema_version": "1.0",
        "track_id": track_id,
        "created_at": created_at or utc_now(),
        "state": "NEW",
        "current_version_id": None,
        "base_version_id": None,
        "revision_iteration": 0,
        "revision_budget_remaining": 0,
        "open_critical_defects": 0,
        "open_major_defects": 0,
    }


def reduce_track_state(
    state: Mapping[str, object],
    action: str,
    payload: Mapping[str, object],
) -> dict:
    """Apply one enumerated transition; arbitrary state patches are unsupported."""

    current = str(state["state"])
    result = copy.deepcopy(dict(state))

    def require(*allowed: str) -> None:
        if current not in allowed:
            raise InvalidTransitionError(f"{action}: {current} not in {allowed}")

    if action == "BRIEF_COMPLETED":
        require("NEW")
        result["state"] = "BRIEF_READY"
        result["revision_budget_remaining"] = int(payload["revision_budget"])
    elif action == "PACKAGE_COMPLETED":
        require("BRIEF_READY", "PACKAGE_READY")
        result["state"] = "PACKAGE_READY"
    elif action == "PACKAGE_APPROVED":
        require("PACKAGE_READY")
        result["state"] = "PACKAGE_APPROVED"
    elif action == "GENERATION_REQUESTED":
        require("PACKAGE_APPROVED")
        result["state"] = "GENERATING"
    elif action == "CANDIDATES_REVIEWED":
        require("GENERATING")
        result["state"] = "AWAITING_BASE_SELECTION"
    elif action == "BASE_SELECTED":
        require("AWAITING_BASE_SELECTION")
        version_id = str(payload["version_id"])
        result["state"] = "REVISING"
        result["base_version_id"] = version_id
        result["current_version_id"] = version_id
    elif action == "REVISION_DIAGNOSED":
        require("REVISING", "FINAL_QC", "AWAITING_FINAL_APPROVAL")
        result["state"] = "REVISING"
        result["open_critical_defects"] = int(payload.get("critical", 0))
        result["open_major_defects"] = int(payload.get("major", 0))
    elif action == "EDIT_COMPLETED":
        require("REVISING")
        result["revision_iteration"] = int(result["revision_iteration"]) + 1
        result["revision_budget_remaining"] = max(
            0,
            int(result["revision_budget_remaining"]) - 1,
        )
    elif action == "COMPARISON_ACCEPTED":
        require("REVISING")
        result["current_version_id"] = str(payload["version_id"])
        result["open_critical_defects"] = int(payload.get("critical", 0))
        result["open_major_defects"] = int(payload.get("major", 0))
    elif action == "COMPARISON_REJECTED":
        require("REVISING")
    elif action == "FINAL_QC_PASSED":
        require("REVISING", "FINAL_QC")
        result["state"] = "AWAITING_FINAL_APPROVAL"
    elif action == "FINAL_QC_FAILED":
        require("REVISING", "FINAL_QC")
        result["state"] = "FINAL_QC"
        result["open_major_defects"] = max(1, int(result["open_major_defects"]))
    elif action == "REGENERATE":
        require("AWAITING_BASE_SELECTION")
        result["state"] = "PACKAGE_APPROVED"
    elif action == "RETURN_TO_LYRICS":
        require("PACKAGE_READY", "AWAITING_BASE_SELECTION")
        result["state"] = "BRIEF_READY"
    elif action == "RETURN_TO_PRODUCTION":
        require("PACKAGE_READY", "AWAITING_BASE_SELECTION")
        result["state"] = "BRIEF_READY"
    elif action == "REQUEST_REVISION":
        require("AWAITING_FINAL_APPROVAL")
        result["state"] = "REVISING"
        result["open_major_defects"] = max(1, int(result["open_major_defects"]))
    elif action == "ROLLBACK":
        require("REVISING")
        result["current_version_id"] = str(payload["version_id"])
    elif action == "APPROVE_FINAL":
        require("AWAITING_FINAL_APPROVAL")
        result["state"] = "APPROVED"
    elif action == "PAUSE":
        require(
            "PACKAGE_READY",
            "AWAITING_BASE_SELECTION",
            "REVISING",
            "AWAITING_FINAL_APPROVAL",
        )
        result["state"] = "PAUSED"
    elif action == "FAIL":
        result["state"] = "FAILED"
    elif action == "REPLENISH_REVISION_BUDGET":
        require("REVISING")
        amount = int(payload["amount"])
        if amount <= 0:
            raise InvalidTransitionError("replenishment must be positive")
        result["revision_budget_remaining"] = (
            int(result["revision_budget_remaining"]) + amount
        )
    else:
        raise InvalidTransitionError(f"unknown transition: {action}")
    return validate_document("track-state", result)


class StateStore:
    def __init__(
        self,
        run_root: Path,
        track_id: str,
        *,
        clock: Callable[[], str] = utc_now,
    ) -> None:
        self.run_root = Path(run_root)
        self.track_id = validate_track_id(track_id)
        self.track_dir = self.run_root / self.track_id
        self.track_dir.mkdir(parents=True, exist_ok=True)
        if self.track_dir.resolve().parent != self.run_root.resolve():
            raise InvalidTrackIdError(track_id)
        self.state_path = self.track_dir / "track-state.json"
        self.events_path = self.track_dir / "events.jsonl"
        self.clock = clock
        if not self.state_path.exists():
            document = validate_document(
                "track-state",
                initial_state(track_id, created_at=clock()),
            )
            atomic_write_json(self.state_path, document)

    def load(self) -> dict:
        return validate_document("track-state", read_json(self.state_path))

    def transition(
        self,
        action: str,
        payload: Optional[Mapping[str, object]] = None,
        *,
        event_id: str,
        before_replace: Optional[Callable[[Path], None]] = None,
    ) -> dict:
        events = read_jsonl(self.events_path)
        existing = next(
            (
                item
                for item in events
                if item.get("event_id") == event_id
            ),
            None,
        )
        if existing is not None:
            payload_value = existing.get("payload")
            if not isinstance(payload_value, dict) or payload_value.get(
                "action"
            ) != action or payload_value.get("input", {}) != dict(payload or {}):
                raise ValueError(f"event_id conflict: {event_id}")
            return self.load()
        input_payload = copy.deepcopy(dict(payload or {}))
        prepare_id = f"prepare:{event_id}"
        prepared = next(
            (item for item in events if item.get("event_id") == prepare_id),
            None,
        )
        if prepared is None:
            previous = self.load()
            updated = reduce_track_state(previous, action, input_payload)
            append_event(
                self.events_path,
                event_id=prepare_id,
                track_id=self.track_id,
                occurred_at=self.clock(),
                payload={
                    "type": "state-transition-prepared",
                    "action": action,
                    "input": input_payload,
                    "previous_state": previous,
                    "next_state": updated,
                },
            )
        else:
            prepared_payload = prepared.get("payload")
            if (
                not isinstance(prepared_payload, dict)
                or prepared_payload.get("action") != action
                or prepared_payload.get("input", {}) != input_payload
            ):
                raise ValueError(f"event_id conflict: {event_id}")
            previous = validate_document(
                "track-state",
                prepared_payload["previous_state"],
            )
            updated = validate_document(
                "track-state",
                prepared_payload["next_state"],
            )
            current = self.load()
            if current != previous and current != updated:
                raise InvalidTransitionError(
                    f"{event_id}: state diverged from prepared transition"
                )
        atomic_write_json(
            self.state_path,
            updated,
            before_replace=before_replace,
        )
        append_event(
            self.events_path,
            event_id=event_id,
            track_id=self.track_id,
            occurred_at=self.clock(),
            payload={
                "type": "state-transition",
                "action": action,
                "from": previous["state"],
                "to": updated["state"],
                "input": input_payload,
                "next_state": updated,
            },
        )
        return updated

    def event(self, event_id: str, payload: Mapping[str, object]) -> bool:
        return append_event(
            self.events_path,
            event_id=event_id,
            track_id=self.track_id,
            occurred_at=self.clock(),
            payload=payload,
        )

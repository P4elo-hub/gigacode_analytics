"""Canonical human-decision store.

DecisionStore is the only store for human decisions. Do not add a second
ExpertDecisionStore. Knowledge cases are a separate journal.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Mapping, Optional

from music_production.orchestration.errors import DecisionConflictError
from music_production.orchestration.state_store import (
    append_event,
    atomic_write_json,
    read_json,
    read_jsonl,
    utc_now,
    validate_document,
)

STEP_TO_GATE = {
    "package-approval": "PACKAGE_APPROVAL",
    "select-base": "BASE_SELECTION",
    "revision-escalation": "REVISION_ESCALATION",
    "final-approval": "FINAL_APPROVAL",
}


class DecisionStore:
    def __init__(self, track_dir: Path, track_id: str) -> None:
        self.track_dir = Path(track_dir)
        self.track_id = track_id
        self.snapshot_path = self.track_dir / "expert-decision.json"
        self.log_path = self.track_dir / "decisions.jsonl"

    def current(self) -> dict:
        if not self.snapshot_path.exists():
            return {}
        return validate_document(
            "expert-decision",
            read_json(self.snapshot_path),
        )

    def all(self) -> list[dict]:
        values = []
        for record in read_jsonl(self.log_path):
            payload = record.get("payload")
            if isinstance(payload, dict):
                values.append(validate_document("expert-decision", payload))
        return values

    def record(
        self,
        decision: Mapping[str, object],
        *,
        expected_gate: str,
    ) -> dict:
        value = validate_document("expert-decision", decision)
        if value["track_id"] != self.track_id:
            raise ValueError("decision track_id mismatch")
        if value["gate"] != expected_gate:
            raise DecisionConflictError(
                f"expected gate {expected_gate}, got {value['gate']}"
            )
        existing = next(
            (
                item
                for item in self.all()
                if item.get("decision_id") == value["decision_id"]
            ),
            None,
        )
        if existing is not None:
            if existing != value:
                raise DecisionConflictError(
                    f"decision_id conflict: {value['decision_id']}"
                )
            if not self.snapshot_path.exists():
                atomic_write_json(self.snapshot_path, value)
            return copy.deepcopy(value)
        atomic_write_json(self.snapshot_path, value)
        append_event(
            self.log_path,
            event_id=f"decision:{value['decision_id']}",
            track_id=self.track_id,
            occurred_at=str(value.get("created_at") or utc_now()),
            payload=value,
        )
        return copy.deepcopy(value)

    def clear_current(self, decision_id: Optional[str] = None) -> None:
        current = self.current()
        if not current:
            return
        if decision_id is not None and current.get("decision_id") != decision_id:
            raise DecisionConflictError("cannot clear a different decision")
        self.snapshot_path.unlink()

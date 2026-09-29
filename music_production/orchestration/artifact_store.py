"""Schema-checked immutable artifacts below one run directory."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Mapping, Optional

from jsonschema import Draft202012Validator, FormatChecker

from music_production.orchestration.errors import (
    UnknownArtifactTypeError,
    UnsafeArtifactPathError,
)
from music_production.orchestration.state_store import (
    atomic_write_json,
    read_jsonl,
    validate_document,
)

SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
CONTRACT_TYPES = {
    "brief",
    "lyrics",
    "lyrics-review",
    "sound-direction",
    "package-review",
    "song-package",
    "generation-request",
    "candidate-review",
    "defect",
    "revision-plan",
    "version-comparison",
    "knowledge-case",
}
INTERNAL_TYPES = {
    "candidates",
    "technical-qc",
    "pending-edit",
    "service-status",
}

INTERNAL_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["schema_version", "track_id", "created_at"],
    "properties": {
        "schema_version": {"const": "1.0"},
        "track_id": {"type": "string", "minLength": 1},
        "created_at": {
            "type": "string",
            "format": "date-time",
            "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T"
            "[0-9]{2}:[0-9]{2}:[0-9]{2}Z$",
        },
    },
}


def _safe_component(value: str) -> str:
    if (
        not SAFE_COMPONENT.fullmatch(value)
        or value in {".", ".."}
        or "/" in value
        or "\\" in value
    ):
        raise UnsafeArtifactPathError(value)
    return value


class ArtifactStore:
    def __init__(self, track_dir: Path, track_id: str) -> None:
        self.track_dir = Path(track_dir)
        self.track_id = track_id
        self.root = self.track_dir / "artifacts"
        self.events_path = self.track_dir / "events.jsonl"
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def allowed_types() -> frozenset[str]:
        return frozenset(CONTRACT_TYPES | INTERNAL_TYPES)

    def _validate(self, artifact_type: str, document: Mapping[str, object]) -> dict:
        if artifact_type in CONTRACT_TYPES:
            value = validate_document(artifact_type, document)
            if value.get("track_id") != self.track_id:
                raise ValueError("artifact track_id mismatch")
            return value
        if artifact_type not in INTERNAL_TYPES:
            raise UnknownArtifactTypeError(artifact_type)
        value = copy.deepcopy(dict(document))
        Draft202012Validator(
            INTERNAL_SCHEMA,
            format_checker=FormatChecker(),
        ).validate(value)
        if value["track_id"] != self.track_id:
            raise ValueError("artifact track_id mismatch")
        return value

    def path_for(self, artifact_type: str, artifact_id: str) -> Path:
        if artifact_type not in self.allowed_types():
            raise UnknownArtifactTypeError(artifact_type)
        safe_type = _safe_component(artifact_type)
        safe_id = _safe_component(artifact_id)
        path = self.root / safe_type / f"{safe_id}.json"
        if self.root.resolve() not in path.resolve().parents:
            raise UnsafeArtifactPathError(str(path))
        return path

    @staticmethod
    def content_id(document: Mapping[str, object]) -> str:
        encoded = json.dumps(
            document,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()[:24]

    def write(
        self,
        artifact_type: str,
        document: Mapping[str, object],
        *,
        artifact_id: Optional[str] = None,
    ) -> Path:
        value = self._validate(artifact_type, document)
        key = artifact_id or self.content_id(value)
        path = self.path_for(artifact_type, key)
        if path.exists():
            existing = json.loads(path.read_text(encoding="utf-8"))
            if existing != value:
                raise ValueError(f"immutable artifact conflict: {artifact_type}/{key}")
            return path
        atomic_write_json(path, value)
        return path

    def records(self, artifact_type: str) -> list[dict]:
        if artifact_type not in self.allowed_types():
            raise UnknownArtifactTypeError(artifact_type)
        folder = self.root / artifact_type
        if not folder.exists():
            return []
        values = []
        for path in sorted(folder.glob("*.json")):
            value = json.loads(path.read_text(encoding="utf-8"))
            values.append(self._validate(artifact_type, value))
        return values

    def latest(self, artifact_type: str) -> Optional[dict]:
        # Event order, not mtime, decides which immutable artifact is active.
        for event in reversed(read_jsonl(self.events_path)):
            payload = event.get("payload")
            if not isinstance(payload, dict):
                continue
            if payload.get("type") == "artifact-written" and payload.get(
                "artifact_type"
            ) == artifact_type:
                artifact_id = payload.get("artifact_id")
                if isinstance(artifact_id, str):
                    path = self.path_for(artifact_type, artifact_id)
                    if path.exists():
                        value = json.loads(path.read_text(encoding="utf-8"))
                        return self._validate(artifact_type, value)
            if payload.get("type") == "artifacts-invalidated":
                names = payload.get("artifact_types")
                if isinstance(names, list) and artifact_type in names:
                    return None
        # A file without its commit event is an interrupted write and is invisible.
        return None

    def exists(self, artifact_type: str) -> bool:
        return self.latest(artifact_type) is not None

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
    append_event,
    atomic_write_json,
    read_json,
    read_jsonl,
    utc_now,
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
    "edit-attempt",
    "revision-plan",
    "version-comparison",
    "knowledge-case",
}
INTERNAL_TYPES = {
    "candidates",
    "technical-qc",
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
        self.index_path = self.track_dir / "artifact-index.json"
        self.root.mkdir(parents=True, exist_ok=True)
        self._refresh_index()

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

    def _index_document(self) -> dict:
        committed: dict[str, dict[str, str]] = {}
        updated_at = utc_now()
        for event in read_jsonl(self.events_path):
            payload = event.get("payload")
            if not isinstance(payload, dict):
                continue
            if payload.get("type") == "artifact-written":
                artifact_type = payload.get("artifact_type")
                artifact_id = payload.get("artifact_id")
                if not isinstance(artifact_type, str) or not isinstance(artifact_id, str):
                    continue
                if artifact_type not in self.allowed_types():
                    continue
                path = self.path_for(artifact_type, artifact_id)
                if path.is_file():
                    committed[artifact_type] = {"artifact_id": artifact_id}
                    updated_at = str(event.get("occurred_at") or updated_at)
            elif payload.get("type") == "artifacts-invalidated":
                names = payload.get("artifact_types")
                if isinstance(names, list):
                    for artifact_type in names:
                        if isinstance(artifact_type, str):
                            committed.pop(artifact_type, None)
                updated_at = str(event.get("occurred_at") or updated_at)
        return {
            "schema_version": "1.0",
            "track_id": self.track_id,
            "created_at": updated_at,
            "committed": committed,
        }

    def _refresh_index(self) -> None:
        atomic_write_json(self.index_path, self._index_document())

    def commit(
        self,
        artifact_type: str,
        artifact_id: str,
        *,
        occurred_at: Optional[str] = None,
    ) -> None:
        path = self.path_for(artifact_type, artifact_id)
        if not path.is_file():
            raise ValueError(f"cannot commit missing artifact: {artifact_type}/{artifact_id}")
        append_event(
            self.events_path,
            event_id=f"artifact:{artifact_type}:{artifact_id}",
            track_id=self.track_id,
            occurred_at=occurred_at,
            payload={
                "type": "artifact-written",
                "artifact_type": artifact_type,
                "artifact_id": artifact_id,
            },
        )
        self._refresh_index()

    def invalidate(
        self,
        artifact_types: list[str],
        *,
        event_id: str,
        reason: str,
        occurred_at: Optional[str] = None,
    ) -> None:
        for artifact_type in artifact_types:
            if artifact_type not in self.allowed_types():
                raise UnknownArtifactTypeError(artifact_type)
        append_event(
            self.events_path,
            event_id=event_id,
            track_id=self.track_id,
            occurred_at=occurred_at,
            payload={
                "type": "artifacts-invalidated",
                "artifact_types": list(artifact_types),
                "reason": reason,
            },
        )
        self._refresh_index()

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

    def committed_id(self, artifact_type: str) -> Optional[str]:
        """Identifier of the latest committed artifact, or None if invalidated."""

        if artifact_type not in self.allowed_types():
            raise UnknownArtifactTypeError(artifact_type)
        for event in reversed(read_jsonl(self.events_path)):
            payload = event.get("payload")
            if not isinstance(payload, dict):
                continue
            if (
                payload.get("type") == "artifact-written"
                and payload.get("artifact_type") == artifact_type
            ):
                artifact_id = payload.get("artifact_id")
                if isinstance(artifact_id, str) and self.path_for(
                    artifact_type, artifact_id
                ).is_file():
                    return artifact_id
            if payload.get("type") == "artifacts-invalidated":
                names = payload.get("artifact_types")
                if isinstance(names, list) and artifact_type in names:
                    return None
        return None


def resolve_committed_artifact(track_dir: Path, artifact_type: str) -> Optional[Path]:
    """Resolve one indexed artifact; never fall back to legacy flat paths."""

    safe_type = _safe_component(artifact_type)
    index_path = Path(track_dir) / "artifact-index.json"
    if not index_path.is_file():
        return None
    index = read_json(index_path)
    committed = index.get("committed")
    if not isinstance(committed, dict):
        return None
    entry = committed.get(safe_type)
    if not isinstance(entry, dict):
        return None
    artifact_id = entry.get("artifact_id")
    if not isinstance(artifact_id, str):
        return None
    safe_id = _safe_component(artifact_id)
    root = Path(track_dir) / "artifacts"
    path = root / safe_type / f"{safe_id}.json"
    if root.resolve() not in path.resolve().parents or not path.is_file():
        return None
    return path

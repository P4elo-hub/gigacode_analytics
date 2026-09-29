"""Atomic immutable version history for one track."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, Iterable, Mapping, Optional

from music_production.services.defect_validation import validate_defect


@dataclass(frozen=True)
class VersionRecord:
    version_id: str
    parent_version_id: Optional[str]
    operation: str
    prompt_id: str
    audio_uri: str
    checksum: str
    status: str
    provider_job_id: Optional[str] = None


class VersionStoreError(RuntimeError):
    pass


class UnknownParentError(VersionStoreError):
    pass


class UnknownVersionError(VersionStoreError):
    pass


class ImmutableVersionError(VersionStoreError):
    pass


class RollbackError(VersionStoreError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class VersionStore:
    """Persist versions.json by writing a sibling temp file then os.replace."""

    def __init__(
        self,
        path: Path,
        *,
        track_id: str,
        clock: Callable[[], str] = _utc_now,
    ) -> None:
        self.path = Path(path)
        self.track_id = track_id
        self._clock = clock
        self._created_at = clock()
        self._versions: Dict[str, VersionRecord] = {}
        self._current_version_id: Optional[str] = None
        if self.path.exists():
            self._load()

    @property
    def current_version_id(self) -> Optional[str]:
        return self._current_version_id

    @property
    def versions(self) -> Mapping[str, VersionRecord]:
        return dict(self._versions)

    def get(self, version_id: str) -> VersionRecord:
        try:
            return self._versions[version_id]
        except KeyError as exc:
            raise UnknownVersionError(version_id) from exc

    def add(
        self,
        record: VersionRecord,
        *,
        defects: Iterable[Mapping[str, object]] = (),
    ) -> VersionRecord:
        for defect in defects:
            validate_defect(defect)
        existing = self._versions.get(record.version_id)
        if existing is not None:
            if existing != record:
                raise ImmutableVersionError(
                    f"version {record.version_id} already has different content"
                )
            return existing
        if (
            record.parent_version_id is not None
            and record.parent_version_id not in self._versions
        ):
            raise UnknownParentError(record.parent_version_id)
        self._versions[record.version_id] = record
        try:
            self._persist()
        except Exception:
            self._versions.pop(record.version_id, None)
            raise
        return record

    def set_current(self, version_id: str) -> None:
        if version_id not in self._versions:
            raise UnknownVersionError(version_id)
        previous = self._current_version_id
        self._current_version_id = version_id
        try:
            self._persist()
        except Exception:
            self._current_version_id = previous
            raise

    def rollback(self) -> str:
        if self._current_version_id is None:
            raise RollbackError("current_version_id is not set")
        current = self._versions[self._current_version_id]
        if current.parent_version_id is None:
            raise RollbackError("current version has no parent")
        self.set_current(current.parent_version_id)
        return current.parent_version_id

    def _serialize(self) -> dict:
        versions = []
        for record in self._versions.values():
            item = asdict(record)
            if item["provider_job_id"] is None:
                item.pop("provider_job_id")
            versions.append(item)
        return {
            "schema_version": "1.0",
            "track_id": self.track_id,
            "created_at": self._created_at,
            "current_version_id": self._current_version_id,
            "versions": versions,
        }

    def _persist(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temp_name = tempfile.mkstemp(
            dir=str(self.path.parent),
            prefix=f".{self.path.name}.",
            suffix=".tmp",
        )
        temp_path = Path(temp_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(
                    self._serialize(),
                    handle,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, self.path)
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def _load(self) -> None:
        document = json.loads(self.path.read_text(encoding="utf-8"))
        if document.get("track_id") != self.track_id:
            raise VersionStoreError("versions.json track_id mismatch")
        self._created_at = document["created_at"]
        records = [VersionRecord(**item) for item in document.get("versions", [])]
        loaded: Dict[str, VersionRecord] = {}
        for record in records:
            if record.version_id in loaded:
                raise VersionStoreError(f"duplicate version_id: {record.version_id}")
            if (
                record.parent_version_id is not None
                and record.parent_version_id not in loaded
            ):
                raise UnknownParentError(record.parent_version_id)
            loaded[record.version_id] = record
        current = document.get("current_version_id")
        if current is not None and current not in loaded:
            raise UnknownVersionError(current)
        self._versions = loaded
        self._current_version_id = current

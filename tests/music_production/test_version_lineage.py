#!/usr/bin/env python3
"""Immutable VersionStore lineage, atomic persistence, and defect ranges."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from music_production.orchestration.artifact_store import ArtifactStore
from music_production.orchestration.state_store import StateStore
from music_production.services.defect_validation import (
    InvalidDefectRangeError,
    validate_defect_range,
)
from music_production.services.version_store import (
    ImmutableVersionError,
    UnknownParentError,
    VersionRecord,
    VersionStore,
)


def version(
    version_id: str,
    parent_version_id=None,
    checksum=None,
) -> VersionRecord:
    return VersionRecord(
        version_id=version_id,
        parent_version_id=parent_version_id,
        operation="generate-batch",
        provider_job_id=f"job-{version_id}",
        prompt_id="prompt-001",
        audio_uri=f"mock://audio/{version_id}.wav",
        checksum=checksum or f"checksum-{version_id}",
        status="stored",
    )


class VersionStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "track-001" / "versions.json"
        self.store = VersionStore(
            self.path,
            track_id="track-001",
            clock=lambda: "2026-09-29T10:00:00Z",
        )

    def test_create_root_and_child(self) -> None:
        self.store.add(version("root"))
        self.store.add(version("child", "root"))
        self.assertEqual(set(self.store.versions), {"root", "child"})
        self.assertEqual(self.store.get("child").parent_version_id, "root")

    def test_unknown_parent_is_rejected(self) -> None:
        with self.assertRaises(UnknownParentError):
            self.store.add(version("child", "missing"))
        self.assertFalse(self.path.exists())

    def test_version_is_immutable(self) -> None:
        original = version("root")
        self.store.add(original)
        self.assertEqual(self.store.add(original), original)
        with self.assertRaises(ImmutableVersionError):
            self.store.add(version("root", checksum="changed"))
        self.assertEqual(self.store.get("root"), original)

    def test_current_changes_only_explicitly(self) -> None:
        self.store.add(version("root"))
        self.store.add(version("child", "root"))
        self.assertIsNone(self.store.current_version_id)
        self.store.set_current("child")
        self.assertEqual(self.store.current_version_id, "child")

    def test_rollback_keeps_children_and_history(self) -> None:
        self.store.add(version("root"))
        self.store.add(version("child", "root"))
        self.store.add(version("grandchild", "child"))
        self.store.set_current("grandchild")
        self.assertEqual(self.store.rollback(), "child")
        self.assertEqual(self.store.current_version_id, "child")
        self.assertEqual(
            set(self.store.versions),
            {"root", "child", "grandchild"},
        )

    def test_persistence_is_atomic(self) -> None:
        real_replace = os.replace
        with patch(
            "music_production.services.version_store.os.replace",
            wraps=real_replace,
        ) as replace:
            self.store.add(version("root"))
        replace.assert_called_once()
        source, destination = replace.call_args.args
        self.assertEqual(Path(destination), self.path)
        self.assertNotEqual(Path(source), self.path)
        self.assertFalse(Path(source).exists())

    def test_reload_restores_versions_and_current(self) -> None:
        self.store.add(version("root"))
        self.store.add(version("child", "root"))
        self.store.set_current("child")
        restarted = VersionStore(self.path, track_id="track-001")
        self.assertEqual(restarted.current_version_id, "child")
        self.assertEqual(restarted.get("child"), version("child", "root"))
        document = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(document["track_id"], "track-001")
        self.assertEqual(document["current_version_id"], "child")

    def test_invalid_defect_cannot_enter_store_flow(self) -> None:
        invalid = {"start_seconds": 4.0, "end_seconds": 4.0}
        with self.assertRaises(InvalidDefectRangeError):
            self.store.add(version("root"), defects=[invalid])
        self.assertEqual(self.store.versions, {})


class DefectRangeTest(unittest.TestCase):
    def test_valid_fractional_range(self) -> None:
        validate_defect_range(125.75, 130.0)

    def test_equal_boundaries_are_invalid(self) -> None:
        with self.assertRaises(InvalidDefectRangeError):
            validate_defect_range(125.75, 125.75)

    def test_end_before_start_is_invalid(self) -> None:
        with self.assertRaises(InvalidDefectRangeError):
            validate_defect_range(130.0, 125.75)

    def test_negative_start_is_invalid(self) -> None:
        with self.assertRaises(InvalidDefectRangeError):
            validate_defect_range(-0.01, 1.0)


class EditAttemptContractTest(unittest.TestCase):
    def test_committed_edit_attempt_is_immutable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run_root = Path(temporary)
            state = StateStore(
                run_root,
                "track-edit-attempt",
                clock=lambda: "2026-09-29T10:00:00Z",
            )
            artifacts = ArtifactStore(state.track_dir, "track-edit-attempt")
            attempt = {
                "schema_version": "1.0",
                "track_id": "track-edit-attempt",
                "created_at": "2026-09-29T10:00:00Z",
                "edit_attempt_id": "attempt-001",
                "revision_plan_id": "plan-001",
                "defect_id": "defect-001",
                "parent_version_id": "version-parent",
                "child_version_id": "version-child",
                "provider_job_id": "job-001",
                "operation": "replace-section",
            }
            artifacts.write(
                "edit-attempt",
                attempt,
                artifact_id="attempt-001",
            )
            artifacts.commit(
                "edit-attempt",
                "attempt-001",
                occurred_at="2026-09-29T10:00:00Z",
            )
            changed = dict(attempt)
            changed["child_version_id"] = "version-other"

            with self.assertRaisesRegex(ValueError, "immutable artifact conflict"):
                artifacts.write(
                    "edit-attempt",
                    changed,
                    artifact_id="attempt-001",
                )


if __name__ == "__main__":
    unittest.main()

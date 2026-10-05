#!/usr/bin/env python3
"""Active-task isolation and write-feature cycle window."""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from pipeline_active_task import (  # noqa: E402
    load_active_task,
    load_active_task_latest,
    save_active_task,
    write_cycle_still_open,
)

SLUG = "write-cycle-hook"
OTHER = "pipeline-viewer-smoke"
PIPELINE = "spec-v2"


class LoadActiveTaskLatestTest(unittest.TestCase):
    def test_does_not_pick_foreign_feature_marker(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="active-latest-"))
        try:
            other_dir = tmp / "Feature-writing" / OTHER
            other_dir.mkdir(parents=True)
            (other_dir / ".pipeline-active-task.json").write_text(
                json.dumps(
                    {
                        "slug": OTHER,
                        "step": "resolve-gaps",
                        "subagent": "gap-resolver",
                        "started_at": "2026-09-15T00:13:01Z",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            self.assertIsNone(load_active_task_latest(tmp))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_root_marker_wins(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="active-root-"))
        try:
            (tmp / "Feature-writing" / SLUG).mkdir(parents=True)
            save_active_task(
                tmp,
                slug=SLUG,
                step="write-feature",
                subagent="spec-writer",
                pipeline=PIPELINE,
                persistent=True,
            )
            other_dir = tmp / "Feature-writing" / OTHER
            other_dir.mkdir(parents=True)
            (other_dir / ".pipeline-active-task.json").write_text(
                json.dumps(
                    {
                        "slug": OTHER,
                        "step": "resolve-gaps",
                        "subagent": "gap-resolver",
                        "started_at": "2099-01-01T00:00:00Z",
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            latest = load_active_task_latest(tmp)
            self.assertIsNotNone(latest)
            self.assertEqual(latest["slug"], SLUG)
            self.assertEqual(latest["step"], "write-feature")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class WriteCycleStillOpenTest(unittest.TestCase):
    def _active(self, started: str) -> dict:
        return {
            "slug": SLUG,
            "step": "write-feature",
            "subagent": "spec-writer",
            "pipeline": PIPELINE,
            "persistent": True,
            "started_at": started,
        }

    def test_open_when_part_exists(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="cycle-part-"))
        try:
            folder = tmp / "Feature-writing" / SLUG
            folder.mkdir(parents=True)
            (folder / f"{SLUG}.part-goal.md").write_text("# goal\n", encoding="utf-8")
            self.assertTrue(write_cycle_still_open(tmp, SLUG, self._active("2026-09-16T07:56:14Z")))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_open_when_spec_older_than_cycle(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="cycle-old-spec-"))
        try:
            folder = tmp / "Feature-writing" / SLUG
            folder.mkdir(parents=True)
            spec = folder / f"{SLUG}.md"
            spec.write_text("# old spec\n", encoding="utf-8")
            old = (datetime.now(timezone.utc) - timedelta(days=1)).timestamp()
            os.utime(spec, (old, old))
            started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            self.assertTrue(write_cycle_still_open(tmp, SLUG, self._active(started)))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_closed_after_assemble(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="cycle-assembled-"))
        try:
            folder = tmp / "Feature-writing" / SLUG
            folder.mkdir(parents=True)
            started_dt = datetime.now(timezone.utc) - timedelta(seconds=30)
            spec = folder / f"{SLUG}.md"
            spec.write_text("# assembled\n", encoding="utf-8")
            now = datetime.now(timezone.utc).timestamp()
            os.utime(spec, (now, now))
            started = started_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            self.assertFalse(write_cycle_still_open(tmp, SLUG, self._active(started)))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_not_open_without_persistent(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="cycle-no-p-"))
        try:
            self.assertFalse(
                write_cycle_still_open(
                    tmp,
                    SLUG,
                    {
                        "slug": SLUG,
                        "step": "write-feature",
                        "subagent": "spec-writer",
                        "started_at": "2026-09-16T07:56:14Z",
                    },
                )
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_cycle_check_requires_pipeline_on_persistent_task(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="cycle-no-pipeline-"))
        try:
            active = self._active("2026-09-16T07:56:14Z")
            active.pop("pipeline")
            with self.assertRaisesRegex(ValueError, "active-task.pipeline required"):
                write_cycle_still_open(tmp, SLUG, active)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_save_roundtrip(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="cycle-save-"))
        try:
            (tmp / "Feature-writing" / SLUG).mkdir(parents=True)
            save_active_task(
                tmp,
                slug=SLUG,
                step="write-feature",
                subagent="spec-writer",
                pipeline=PIPELINE,
                persistent=True,
            )
            loaded = load_active_task(tmp)
            self.assertTrue(loaded.get("persistent"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_save_requires_pipeline(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="cycle-save-pipeline-"))
        try:
            (tmp / "Feature-writing" / SLUG).mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, "active-task.pipeline required"):
                save_active_task(
                    tmp,
                    slug=SLUG,
                    step="write-feature",
                    subagent="spec-writer",
                    persistent=True,
                )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_persistent_same_step_keeps_started_at(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="cycle-started-"))
        try:
            (tmp / "Feature-writing" / SLUG).mkdir(parents=True)
            first = save_active_task(
                tmp,
                slug=SLUG,
                step="write-feature",
                subagent="spec-writer",
                pipeline=PIPELINE,
                persistent=True,
            )
            marker = tmp / ".pipeline-active-task.json"
            payload = json.loads(marker.read_text(encoding="utf-8"))
            payload["started_at"] = "2026-01-01T00:00:00Z"
            marker.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            feature = tmp / "Feature-writing" / SLUG / ".pipeline-active-task.json"
            feature.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            second = save_active_task(
                tmp,
                slug=SLUG,
                step="write-feature",
                subagent="spec-writer",
                pipeline=PIPELINE,
                persistent=True,
            )
            self.assertEqual(second["started_at"], "2026-01-01T00:00:00Z")
            self.assertNotEqual(first["started_at"], second["started_at"])
            other = save_active_task(
                tmp,
                slug=SLUG,
                step="check-feature",
                subagent="spec-reviewer",
                pipeline=PIPELINE,
                persistent=True,
            )
            self.assertNotEqual(other["started_at"], "2026-01-01T00:00:00Z")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

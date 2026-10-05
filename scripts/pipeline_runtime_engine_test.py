#!/usr/bin/env python3
"""Pack-agnostic runtime checks for delegate/resolve/schema contract."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

from pipeline_active_task import save_active_task  # noqa: E402
from pipeline_delegate import build_delegate  # noqa: E402
from pipeline_runtime import resolve_pipeline_id, runtime_contract  # noqa: E402

ACTIVE_PIPELINE = "spec-v2"


class ResolvePipelineIdTest(unittest.TestCase):
    def test_no_pipeline_is_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "pipeline id required"):
            resolve_pipeline_id(None, None)

    def test_cli_matches_active_task(self) -> None:
        active = {"pipeline": ACTIVE_PIPELINE}
        self.assertEqual(resolve_pipeline_id(ACTIVE_PIPELINE, active), ACTIVE_PIPELINE)

    def test_cli_mismatch_active_task_is_error(self) -> None:
        active = {"pipeline": "calibration"}
        with self.assertRaisesRegex(ValueError, "pipeline mismatch"):
            resolve_pipeline_id(ACTIVE_PIPELINE, active)

    def test_active_task_used_when_cli_missing(self) -> None:
        active = {"pipeline": ACTIVE_PIPELINE}
        self.assertEqual(resolve_pipeline_id(None, active), ACTIVE_PIPELINE)


class RuntimeContractTest(unittest.TestCase):
    def test_runtime_contract_uses_explicit_pipeline(self) -> None:
        contract = runtime_contract(ACTIVE_PIPELINE)
        self.assertEqual(contract["pipeline_id"], ACTIVE_PIPELINE)
        joined = " ".join(contract["loop"])
        self.assertIn(f"--pipeline {ACTIVE_PIPELINE}", joined)
        self.assertIn("pipeline_delegate.py", joined)
        self.assertIn("pipeline_validate.py", joined)

    def test_runtime_contract_without_id_is_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "pipeline id required"):
            runtime_contract(None)


class DelegateDryRunTest(unittest.TestCase):
    def test_delegate_dry_run_does_not_write_active_task(self) -> None:
        with tempfile.TemporaryDirectory(prefix="delegate-dry-") as tmp:
            root = Path(tmp)
            slug = "engine-smoke"
            (root / "Feature-writing" / slug).mkdir(parents=True)
            result = build_delegate(root, slug, pipeline_id=ACTIVE_PIPELINE, dry_run=True)
            self.assertTrue(result.get("ok"), json.dumps(result, ensure_ascii=False))
            active = result.get("active_task") or {}
            if active:
                self.assertTrue(active.get("dry_run"), active)
            self.assertFalse((root / ".pipeline-active-task.json").exists())

    def test_delegate_writes_pipeline_into_active_task(self) -> None:
        with tempfile.TemporaryDirectory(prefix="delegate-active-") as tmp:
            root = Path(tmp)
            slug = "engine-smoke"
            (root / "Feature-writing" / slug).mkdir(parents=True)
            payload = save_active_task(
                root,
                slug=slug,
                step="analyze-routing",
                subagent="routing-analyzer",
                pipeline=ACTIVE_PIPELINE,
            )
            self.assertEqual(payload["pipeline"], ACTIVE_PIPELINE)
            self.assertEqual(resolve_pipeline_id(None, payload), ACTIVE_PIPELINE)


if __name__ == "__main__":
    unittest.main()

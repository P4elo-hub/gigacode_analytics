#!/usr/bin/env python3
"""Pack-agnostic runtime checks for delegate/resolve/schema contract."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

from pipeline_active_task import save_active_task  # noqa: E402
from build_pipeline_graph import (  # noqa: E402
    dedupe_run_log_stamps,
    infer_active_task,
    load_schema,
    mark_running_timeline,
)
import pipeline_delegate  # noqa: E402
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


class ActiveTaskLiveFallbackTest(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = load_schema()["pipelines"][ACTIVE_PIPELINE]
        self.now = datetime(2026, 10, 5, 15, 40, tzinfo=timezone.utc)

    def test_fresh_active_task_is_running_fallback(self) -> None:
        active = {
            "slug": "engine-smoke",
            "step": "context-researcher",
            "subagent": "context-researcher",
            "pipeline": ACTIVE_PIPELINE,
            "started_at": (self.now - timedelta(seconds=57)).isoformat().replace("+00:00", "Z"),
        }

        inferred = infer_active_task(
            active,
            self.schema,
            pipeline_id=ACTIVE_PIPELINE,
            now=self.now,
        )

        self.assertIsNotNone(inferred)
        self.assertEqual(inferred["step"], "context-researcher")
        self.assertEqual(inferred["source"], "active-task")

    def test_stale_active_task_is_not_running_fallback(self) -> None:
        active = {
            "slug": "engine-smoke",
            "step": "context-researcher",
            "subagent": "context-researcher",
            "pipeline": ACTIVE_PIPELINE,
            "started_at": (self.now - timedelta(seconds=181)).isoformat().replace("+00:00", "Z"),
        }

        inferred = infer_active_task(
            active,
            self.schema,
            pipeline_id=ACTIVE_PIPELINE,
            now=self.now,
        )

        self.assertIsNone(inferred)

    def test_stale_persistent_active_task_can_stay_running_fallback(self) -> None:
        active = {
            "slug": "engine-smoke",
            "step": "spec-writer",
            "subagent": "spec-writer",
            "pipeline": ACTIVE_PIPELINE,
            "started_at": (self.now - timedelta(minutes=10)).isoformat().replace("+00:00", "Z"),
            "persistent": True,
        }

        inferred = infer_active_task(
            active,
            self.schema,
            pipeline_id=ACTIVE_PIPELINE,
            now=self.now,
            allow_stale_persistent=True,
        )

        self.assertIsNotNone(inferred)
        self.assertEqual(inferred["step"], "spec-writer")

    def test_ask_user_continuation_is_not_running_fallback(self) -> None:
        active = {
            "slug": "engine-smoke",
            "step": "gap-resolver",
            "subagent": "gap-resolver",
            "pipeline": ACTIVE_PIPELINE,
            "started_at": (self.now - timedelta(seconds=30)).isoformat().replace("+00:00", "Z"),
            "continuation": "ask_user",
        }

        inferred = infer_active_task(
            active,
            self.schema,
            pipeline_id=ACTIVE_PIPELINE,
            now=self.now,
        )

        self.assertIsNone(inferred)


class TimelineLiveRowTest(unittest.TestCase):
    def test_dedupe_run_log_stamp_keeps_one_synced_pass(self) -> None:
        history = [
            {
                "ts": "2026-10-05T15:58:12Z",
                "step": "spec-writer",
                "subagent": "spec-writer",
                "result": "ok",
                "source": "merged",
                "note": "Write usecase-as-is block",
            },
            {
                "ts": "2026-10-05T15:58:12.632Z",
                "step": "spec-writer",
                "subagent": "spec-writer",
                "result": "ok",
                "source": "merged",
                "started_at": "2026-10-05T15:50:58.910Z",
                "ended_at": "2026-10-05T15:58:12.632Z",
                "duration_sec": 433.7,
                "call_id": "call_00_fuakq9SjZeWBBkyBUYQj0692",
                "note": "sync:call_00_fuakq9SjZeWBBkyBUYQj0692 · Write usecase-as-is block",
            },
            {
                "ts": "2026-10-05T15:58:25Z",
                "step": "spec-writer",
                "subagent": "spec-writer",
                "result": "active",
                "source": "current",
                "note": "Write usecase-to-be block",
            },
        ]

        deduped = dedupe_run_log_stamps(history)

        self.assertEqual(len(deduped), 2)
        self.assertEqual(deduped[0]["call_id"], "call_00_fuakq9SjZeWBBkyBUYQj0692")
        self.assertEqual(deduped[1]["source"], "current")

    def test_running_current_adds_next_active_pass(self) -> None:
        timeline = [
            {
                "ts": "2026-10-05T15:50:43Z",
                "step": "spec-writer",
                "subagent": "spec-writer",
                "result": "ok",
                "seq": 1,
                "pass": 1,
            }
        ]
        current = {
            "step": "spec-writer",
            "subagent": "spec-writer",
            "status": "running",
            "since": "2026-10-05T15:44:39Z",
            "note": "persistent active-task marker",
            "source": "active-task",
        }

        mark_running_timeline(timeline, current)

        self.assertEqual(len(timeline), 2)
        self.assertEqual(timeline[-1]["step"], "spec-writer")
        self.assertEqual(timeline[-1]["pass"], 2)
        self.assertEqual(timeline[-1]["display_state"], "active")


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

    def test_ask_user_continuation_returns_source_step_after_answer(self) -> None:
        with tempfile.TemporaryDirectory(prefix="delegate-ask-cont-") as tmp:
            root = Path(tmp)
            slug = "engine-smoke"
            (root / "Feature-writing" / slug).mkdir(parents=True)
            save_active_task(
                root,
                slug=slug,
                step="gap-resolver",
                subagent="gap-resolver",
                pipeline=ACTIVE_PIPELINE,
                persistent=True,
                continuation="ask_user",
            )
            dispatch = {
                "orchestrator_mode": "delegate",
                "next_step": "analyze-routing",
                "next_subagent": "routing-analyzer",
                "next_reason": "routing-state stale",
                "ready": False,
            }

            with patch.object(pipeline_delegate, "build_dispatch", return_value=dispatch):
                result = build_delegate(root, slug, pipeline_id=ACTIVE_PIPELINE, dry_run=True)

            self.assertEqual(result["action"], "task", json.dumps(result, ensure_ascii=False))
            self.assertEqual(result["task"]["step"], "gap-resolver")
            self.assertEqual(result["task"]["subagent_type"], "gap-resolver")
            self.assertEqual(result["dispatch"]["next_step"], "gap-resolver")
            self.assertEqual(result["dispatch"]["next_subagent"], "gap-resolver")
            self.assertNotIn("routing_dispatch", result)
            self.assertNotEqual(result["task"]["step"], "analyze-routing")
            self.assertIn("Продолжение ask_user", result["instruction"])

    def test_ask_user_continuation_is_not_gap_resolver_specific(self) -> None:
        with tempfile.TemporaryDirectory(prefix="delegate-ask-ch-") as tmp:
            root = Path(tmp)
            slug = "engine-smoke"
            (root / "Feature-writing" / slug).mkdir(parents=True)
            save_active_task(
                root,
                slug=slug,
                step="challenge-resolver",
                subagent="challenge-resolver",
                pipeline=ACTIVE_PIPELINE,
                persistent=True,
                continuation="ask_user",
            )
            dispatch = {
                "orchestrator_mode": "delegate",
                "next_step": "analyze-routing",
                "next_subagent": "routing-analyzer",
                "next_reason": "routing-state stale",
                "ready": False,
            }

            with patch.object(pipeline_delegate, "build_dispatch", return_value=dispatch):
                result = build_delegate(root, slug, pipeline_id=ACTIVE_PIPELINE, dry_run=True)

            self.assertEqual(result["action"], "task", json.dumps(result, ensure_ascii=False))
            self.assertEqual(result["task"]["step"], "challenge-resolver")
            self.assertEqual(result["task"]["subagent_type"], "challenge-resolver")
            self.assertEqual(result["dispatch"]["next_step"], "challenge-resolver")
            self.assertEqual(result["dispatch"]["next_subagent"], "challenge-resolver")

    def test_ask_user_continuation_does_not_skip_unanswered_ask(self) -> None:
        with tempfile.TemporaryDirectory(prefix="delegate-ask-wait-") as tmp:
            root = Path(tmp)
            slug = "engine-smoke"
            (root / "Feature-writing" / slug).mkdir(parents=True)
            dispatch = {
                "orchestrator_mode": "ask_user",
                "next_step": "gap-resolver",
                "next_subagent": "gap-resolver",
                "next_reason": "needs-answer",
                "ready": False,
            }

            with patch.object(pipeline_delegate, "build_dispatch", return_value=dispatch):
                result = build_delegate(root, slug, pipeline_id=ACTIVE_PIPELINE, dry_run=False)

            self.assertEqual(result["action"], "ask_user", json.dumps(result, ensure_ascii=False))
            active = result.get("active_task") or {}
            self.assertEqual(active.get("continuation"), "ask_user")
            self.assertEqual(result["task"]["step"], "gap-resolver")


if __name__ == "__main__":
    unittest.main()

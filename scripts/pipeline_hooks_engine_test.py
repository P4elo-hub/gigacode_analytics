#!/usr/bin/env python3
"""Hook helper checks that are independent of a concrete feature pipeline."""

from __future__ import annotations

import sys
import tempfile
import unittest
import json
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from pipeline_after_subagent import (  # noqa: E402
    capture_routing_report,
    infer_result,
    infer_run_outcome,
    requested_ask_parent,
)
from routing_reports import read_reports_after, reports_index_path  # noqa: E402
from pipeline_routing_state import load_routing_state  # noqa: E402
from pipeline_status import populate_status, resolve_artifact_paths  # noqa: E402
from types import SimpleNamespace


class InferResultTest(unittest.TestCase):
    def test_quality_gate_fail_zero_is_finished_ok(self) -> None:
        self.assertEqual(infer_result("quality_gates.py → PASS (fail: 0, warn: 1)"), "ok")
        self.assertEqual(infer_result("PASS · fail 0 · warn 1"), "ok")

    def test_quality_report_fail_count_is_not_process_abort(self) -> None:
        self.assertEqual(infer_result("quality_gates → FAIL · fail 3 · warn 0"), "ok")

    def test_wrapper_failures_are_aborted(self) -> None:
        self.assertEqual(infer_result("Subagent failed: timeout"), "fail")
        self.assertEqual(infer_run_outcome({"status": "timeout"}), "fail")
        self.assertEqual(infer_run_outcome({"error": "killed"}), "fail")

    def test_empty_message_is_finished(self) -> None:
        self.assertEqual(infer_result(""), "ok")

    def test_ask_parent_is_continuation_signal(self) -> None:
        self.assertTrue(
            requested_ask_parent(
                {
                    "last_assistant_message": (
                        "ASK_PARENT\nD-13, D-14 со статусом needs-answer"
                    )
                }
            )
        )
        self.assertFalse(requested_ask_parent({"last_assistant_message": "applied"}))

    def test_subagent_message_is_captured_as_routing_report(self) -> None:
        with tempfile.TemporaryDirectory(prefix="routing-report-hook-") as raw:
            root = Path(raw)
            message = (
                '<routing-report>{"summary":"Контекст найден",'
                '"outcomes":["Контекст готов"],"remaining_work":[]}</routing-report>'
            )
            stored, appended = capture_routing_report(
                root,
                slug="demo",
                pipeline_id="spec-v2",
                step="find-context",
                subagent="context-researcher",
                result="ok",
                cli="qwen",
                hook_input={"last_assistant_message": message},
                active={"started_at": "2026-10-27T09:00:00Z"},
            )
            index_path = reports_index_path(root, "demo", "spec-v2")
            self.assertTrue(appended)
            self.assertFalse(stored["incomplete"])
            self.assertEqual(read_reports_after(index_path)[0]["summary"], "Контекст найден")

    def test_missing_block_is_stored_as_incomplete(self) -> None:
        with tempfile.TemporaryDirectory(prefix="routing-report-incomplete-") as raw:
            root = Path(raw)
            stored, appended = capture_routing_report(
                root,
                slug="demo",
                pipeline_id="spec-v2",
                step="gap-resolver",
                subagent="gap-resolver",
                result="ok",
                cli="qwen",
                hook_input={"last_assistant_message": "Закрыл GAP-12, отчёт забыл"},
                active={"started_at": "2026-10-27T09:01:00Z"},
            )
            self.assertTrue(appended)
            self.assertTrue(stored["incomplete"])
            self.assertEqual(
                read_reports_after(reports_index_path(root, "demo", "spec-v2"))[0]["incomplete"],
                True,
            )

    def test_analyzer_report_is_acknowledged_without_refresh_loop(self) -> None:
        with tempfile.TemporaryDirectory(prefix="routing-analyzer-report-") as raw:
            root = Path(raw)
            paths = resolve_artifact_paths(root, "demo", "spec-v2")
            state_path = paths["routing_state"]
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(
                json.dumps({"schema_version": 1, "slug": "demo", "fields": {}}),
                encoding="utf-8",
            )
            message = (
                '<routing-report>{"summary":"Routing state refreshed",'
                '"artifacts":[],"outcomes":[],"remaining_work":[]}</routing-report>'
            )
            capture_routing_report(
                root,
                slug="demo",
                pipeline_id="spec-v2",
                step="analyze-routing",
                subagent="routing-analyzer",
                result="ok",
                cli="qwen",
                hook_input={"last_assistant_message": message},
                active={"started_at": "2026-10-27T09:00:00Z"},
            )
            payload, error = load_routing_state(state_path, slug="demo")
            self.assertEqual(error, "")
            self.assertEqual(payload["routing_reports"]["last_seq"], 1)
            status = SimpleNamespace(pipeline_id="spec-v2")
            populate_status(status, root, "demo", "spec-v2")
            self.assertNotIn("routing_state", status.stale)


if __name__ == "__main__":
    unittest.main()

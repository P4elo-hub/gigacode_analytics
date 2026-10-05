#!/usr/bin/env python3
"""Hook helper checks that are independent of a concrete feature pipeline."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from pipeline_after_subagent import infer_result, infer_run_outcome  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()

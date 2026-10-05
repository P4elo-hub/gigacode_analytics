#!/usr/bin/env python3
"""Main-session orchestrator must not inspect pipelines/ or router sources."""

from __future__ import annotations

import unittest

from pipeline_box_orchestrator import box_orchestrator_hook


def _decision(payload: dict) -> str:
    return payload["hookSpecificOutput"]["permissionDecision"]


class BoxOrchestratorTest(unittest.TestCase):
    def test_subagent_may_read_predicates(self) -> None:
        payload = box_orchestrator_hook(
            {
                "agent_id": "routing-analyzer-1",
                "tool_name": "read_file",
                "tool_input": {
                    "file_path": "pipelines/spec/predicates.py",
                },
            }
        )
        self.assertEqual(_decision(payload), "allow")

    def test_orchestrator_denied_predicates(self) -> None:
        payload = box_orchestrator_hook(
            {
                "tool_name": "read_file",
                "tool_input": {
                    "file_path": "/Users/ivan/Documents/gigacode_analytics/pipelines/spec/predicates.py",
                },
            }
        )
        self.assertEqual(_decision(payload), "deny")

    def test_orchestrator_denied_routing_conditions_grep(self) -> None:
        payload = box_orchestrator_hook(
            {
                "tool_name": "run_shell_command",
                "tool_input": {
                    "command": "grep -n open_gaps pipelines/spec/predicates.py",
                },
            }
        )
        self.assertEqual(_decision(payload), "deny")

    def test_orchestrator_allowed_delegate(self) -> None:
        payload = box_orchestrator_hook(
            {
                "tool_name": "run_shell_command",
                "tool_input": {
                    "command": (
                        "python3 scripts/pipeline_delegate.py "
                        "bph-coupons-dividends-monthly-summary --cli qwen --pipeline spec"
                    ),
                },
            }
        )
        self.assertEqual(_decision(payload), "allow")

    def test_orchestrator_allowed_decisions_read(self) -> None:
        payload = box_orchestrator_hook(
            {
                "tool_name": "read_file",
                "tool_input": {
                    "file_path": (
                        "Feature-writing/bph-coupons-dividends-monthly-summary/"
                        "bph-coupons-dividends-monthly-summary-decisions.md"
                    ),
                },
            }
        )
        self.assertEqual(_decision(payload), "allow")

    def test_orchestrator_denied_schema_python_c(self) -> None:
        payload = box_orchestrator_hook(
            {
                "tool_name": "run_shell_command",
                "tool_input": {
                    "command": (
                        "python3 -c \"import json; "
                        "json.load(open('scripts/pipeline_schema.json'))\""
                    ),
                },
            }
        )
        self.assertEqual(_decision(payload), "deny")


if __name__ == "__main__":
    unittest.main()

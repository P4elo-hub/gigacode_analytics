#!/usr/bin/env python3
"""Pack-neutral routing report journal tests."""

from __future__ import annotations

import sys
import tempfile
import unittest
import json
import os
from pathlib import Path
from types import SimpleNamespace

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from routing_reports import (  # noqa: E402
    append_report,
    cursor_from_state,
    extract_report,
    load_index,
    normalize_report,
    read_reports_after,
)
from pipeline_status import populate_status, resolve_artifact_paths  # noqa: E402


class RoutingReportsTest(unittest.TestCase):
    def test_extract_and_normalize_report(self) -> None:
        message = """
Done.
<routing-report>
{"summary":"Контекст найден","artifacts":["Feature-context/demo.md"],
 "outcomes":["Контекст готов"],"remaining_work":[]}
</routing-report>
"""
        payload, error = extract_report(message)
        self.assertEqual(error, "")
        report = normalize_report(
            payload,
            slug="demo",
            pipeline_id="sample",
            step="find-context",
            subagent="context-researcher",
            result="ok",
            cli="qwen",
            event_key="sample/demo/find-context/1",
        )
        self.assertFalse(report["incomplete"])
        self.assertEqual(report["artifacts"][0]["action"], "updated")

    def test_missing_report_is_incomplete(self) -> None:
        payload, error = extract_report("Done")
        report = normalize_report(
            payload,
            slug="demo",
            pipeline_id="sample",
            step="first",
            subagent="worker",
            result="ok",
            cli="qwen",
            event_key="event-1",
            error=error,
        )
        self.assertTrue(report["incomplete"])
        self.assertIn("missing", report["capture_error"])

    def test_append_is_ordered_idempotent_and_cursor_based(self) -> None:
        with tempfile.TemporaryDirectory(prefix="routing-reports-") as raw:
            index_path = Path(raw) / "task" / ".pipeline" / "routing-reports" / "index.json"
            base = normalize_report(
                {"summary": "one"},
                slug="demo",
                pipeline_id="sample",
                step="one",
                subagent="worker",
                result="ok",
                cli="qwen",
                event_key="event-1",
            )
            first, appended = append_report(index_path, base)
            duplicate, appended_again = append_report(index_path, base)
            second_payload = dict(base, event_key="event-2", step="two", summary="two")
            second, appended_second = append_report(index_path, second_payload)

            self.assertTrue(appended)
            self.assertFalse(appended_again)
            self.assertTrue(appended_second)
            self.assertEqual(first["seq"], duplicate["seq"])
            self.assertEqual(second["seq"], 2)
            self.assertEqual(load_index(index_path)["last_seq"], 2)
            self.assertEqual([row["seq"] for row in read_reports_after(index_path, 1)], [2])

    def test_cursor_is_optional_metadata(self) -> None:
        self.assertEqual(cursor_from_state(None), 0)
        self.assertEqual(cursor_from_state({"routing_reports": {"last_seq": 7}}), 7)

    def test_missing_journal_does_not_mark_routing_state_stale(self) -> None:
        with tempfile.TemporaryDirectory(prefix="routing-report-legacy-") as raw:
            root = Path(raw)
            paths = resolve_artifact_paths(root, "demo", "spec-v2")
            state_path = paths["routing_state"]
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(
                json.dumps({"schema_version": 1, "slug": "demo", "fields": {}}),
                encoding="utf-8",
            )
            status = SimpleNamespace(pipeline_id="spec-v2")
            populate_status(status, root, "demo", "spec-v2")
            self.assertFalse(paths["routing_reports"].is_file())
            self.assertNotIn("routing_state", status.stale)

    def test_new_report_marks_routing_state_stale(self) -> None:
        with tempfile.TemporaryDirectory(prefix="routing-report-stale-") as raw:
            root = Path(raw)
            paths = resolve_artifact_paths(root, "demo", "spec-v2")
            state_path = paths["routing_state"]
            report_index = paths["routing_reports"]
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(
                json.dumps({"schema_version": 1, "slug": "demo", "fields": {}}),
                encoding="utf-8",
            )
            report_index.parent.mkdir(parents=True, exist_ok=True)
            report_index.write_text(
                json.dumps({"schema_version": 1, "last_seq": 1, "events": []}),
                encoding="utf-8",
            )
            os.utime(state_path, (100, 100))
            os.utime(report_index, (200, 200))
            status = SimpleNamespace(pipeline_id="spec-v2")
            populate_status(status, root, "demo", "spec-v2")
            self.assertIn("routing_state", status.stale)


if __name__ == "__main__":
    unittest.main()

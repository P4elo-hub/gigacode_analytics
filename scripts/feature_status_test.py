#!/usr/bin/env python3
"""Unit tests for spec collectors and yaml-driven populate_status."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from pipeline_pack import load_pack_module  # noqa: E402
from pipeline_status import populate_status  # noqa: E402
from feature_status import build_status_fields, render_markdown  # noqa: E402

_collectors = load_pack_module("spec", "collectors")
ALIGNMENT_RELATES_RE = _collectors.ALIGNMENT_RELATES_RE
DECISION_ROW_RE = _collectors.DECISION_ROW_RE
parse_alignment = _collectors.parse_alignment

GOLDEN = SCRIPTS / "fixtures" / "status_golden" / "spec" / "cases.json"


class ParseAlignmentTest(unittest.TestCase):
    def test_counts_critical_major_mismatch_rows(self) -> None:
        text = """---
verdict: FAIL
alignment_iteration: 1
---

| claim | evidence | verdict | severity |
| a | b | MISMATCH | Critical |
| c | d | MISMATCH | Major |
| e | f | CONFIRMED | Minor |
"""
        verdict, iteration, mismatch = parse_alignment(text)
        self.assertEqual(verdict, "FAIL")
        self.assertEqual(iteration, 1)
        self.assertEqual(mismatch, 2)

    def test_ignores_aggregate_summary_rows(self) -> None:
        text = """---
verdict: FAIL
alignment_iteration: 1
---

| Major MISMATCH | **2** |
| MISMATCH (Major) | 2 |
| total mismatch | 2 |
| claim | evidence | verdict | severity |
| a | b | MISMATCH | Critical |
"""
        _, _, mismatch = parse_alignment(text)
        self.assertEqual(mismatch, 1)

    def test_no_mismatch_when_only_minor(self) -> None:
        text = """---
verdict: FAIL
alignment_iteration: 1
---

| claim | evidence | verdict | severity |
| a | b | MISMATCH | Minor |
"""
        _, _, mismatch = parse_alignment(text)
        self.assertEqual(mismatch, 0)


class DecisionsParsingTest(unittest.TestCase):
    SAMPLE = """# DECISIONS

| ID | Relates | Prompt | Options | Decision | Status | Date |
|----|---------|--------|---------|----------|--------|------|
| D-01 | Q-01 | gap | A) one | pick A | needs-answer | 2026-09-12 |
| D-02 | F-01 | align | A) one | pick A | needs-answer | 2026-09-12 |
| D-03 | CH-01 | ch | A) one | pick A | pending-apply | 2026-09-12 |
| D-04 | I-05 | align | A) one | pick A | pending-apply | 2026-09-12 |
"""

    def test_decision_row_re_reads_status_column(self) -> None:
        rows = list(DECISION_ROW_RE.finditer(self.SAMPLE))
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0].group(2).strip().lower(), "needs-answer")
        self.assertEqual(rows[3].group(2).strip().lower(), "pending-apply")

    def test_alignment_relates_detected(self) -> None:
        self.assertTrue(ALIGNMENT_RELATES_RE.search("F-01"))
        self.assertTrue(ALIGNMENT_RELATES_RE.search("I-05"))
        self.assertFalse(ALIGNMENT_RELATES_RE.search("Q-01"))
        self.assertFalse(ALIGNMENT_RELATES_RE.search("CH-01"))

    def test_build_status_fields_alignment_decision_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            slug = "unit-test-slug"
            fw = root / "Feature-writing" / slug
            fw.mkdir(parents=True)
            ctx_dir = root / "Feature-context"
            ctx_dir.mkdir(parents=True)
            (ctx_dir / f"{slug}.md").write_text("# Context\n\nVerified.\n", encoding="utf-8")
            (fw / f"{slug}.md").write_text("# spec\n", encoding="utf-8")
            (fw / f"{slug}-decisions.md").write_text(self.SAMPLE, encoding="utf-8")

            status = build_status_fields(root, slug)
            self.assertEqual(status.decisions_needs_answer, 2)
            self.assertEqual(status.decisions_needs_answer_alignment, 1)
            self.assertEqual(status.decisions_pending_apply, 2)
            self.assertEqual(status.decisions_pending_apply_alignment, 1)


class PopulateStatusYamlTest(unittest.TestCase):
    def test_populate_status_generic_namespace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            slug = "ns-task"
            status = SimpleNamespace(slug=slug)
            populate_status(status, root, slug, "spec")
            self.assertFalse(status.has_spec)
            self.assertFalse(status.has_context)
            self.assertEqual(status.stale, [])
            self.assertFalse(status.alignment_stale)

    def test_render_markdown_uses_display_labels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            slug = "unit-render"
            fw = root / "Feature-writing" / slug
            fw.mkdir(parents=True)
            (fw / f"{slug}.md").write_text("# spec\n", encoding="utf-8")
            text = render_markdown(build_status_fields(root, slug))
            self.assertIn("| CONTEXT_DOC |", text)
            self.assertIn("| SPEC |", text)
            self.assertIn("| ALIGNMENT |", text)


class StatusGoldenTest(unittest.TestCase):
    def test_yaml_files_to_fields(self) -> None:
        cases = json.loads(GOLDEN.read_text(encoding="utf-8"))
        for case in cases:
            with self.subTest(case["id"]):
                self._run_case(case)

    def _run_case(self, case: dict) -> None:
        task_id = case["task_id"]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel, content in (case.get("files") or {}).items():
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            order = case.get("mtime_order") or []
            base = time.time() - max(len(order), 1) * 10
            for index, rel in enumerate(order):
                os.utime(root / rel, (base + index * 10, base + index * 10))
            status = build_status_fields(root, task_id)
            for key, expected in (case.get("expect") or {}).items():
                actual = getattr(status, key)
                self.assertEqual(actual, expected, msg=f"{case['id']}.{key}")


class PipelineRuntimeTest(unittest.TestCase):
    def test_load_dispatch_spec_present(self) -> None:
        from pipeline_router import load_dispatch
        from pipeline_runtime import dispatch_supported, load_pipeline_dispatch

        spec = load_dispatch("spec")
        self.assertIsInstance(spec, dict)
        self.assertIn("rules", spec)
        self.assertEqual(load_pipeline_dispatch("spec"), spec)
        self.assertTrue(dispatch_supported("spec"))

    def test_load_status_spec_parameterized(self) -> None:
        from pipeline_status import load_status_spec

        spec = load_status_spec("spec")
        self.assertIn("artifacts", spec)
        self.assertIn("spec", spec["artifacts"])
        self.assertTrue(any(item.get("id") == "needs_check_feature" for item in spec.get("collectors") or []))
        self.assertTrue(any(item.get("id") == "needs-check-feature" for item in spec.get("invariants") or []))
        cal = load_status_spec("calibration")
        self.assertIsInstance(cal.get("artifacts"), dict)

    def test_load_dispatch_unknown_and_calibration(self) -> None:
        from pipeline_router import load_dispatch
        from pipeline_runtime import dispatch_supported, normalize_pipeline_id

        self.assertIsNone(load_dispatch("no-such-pipeline"))
        self.assertIsNone(load_dispatch("calibration"))
        self.assertFalse(dispatch_supported("calibration"))
        with self.assertRaises(ValueError):
            normalize_pipeline_id("no-such-pipeline")


if __name__ == "__main__":
    raise SystemExit(unittest.main())

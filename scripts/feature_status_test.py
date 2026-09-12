#!/usr/bin/env python3
"""Unit tests for feature_status parsing helpers."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from feature_status import (  # noqa: E402
    ALIGNMENT_RELATES_RE,
    DECISION_ROW_RE,
    build_status_fields,
    parse_alignment,
)


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
            ctx = ctx_dir / f"{slug}.md"
            ctx.write_text("# Context\n\nVerified.\n", encoding="utf-8")
            (fw / f"{slug}.md").write_text("# spec\n", encoding="utf-8")
            (fw / f"{slug}-decisions.md").write_text(self.SAMPLE, encoding="utf-8")

            status = build_status_fields(root, slug)
            self.assertEqual(status.decisions_needs_answer, 2)
            self.assertEqual(status.decisions_needs_answer_alignment, 1)
            self.assertEqual(status.decisions_pending_apply, 2)
            self.assertEqual(status.decisions_pending_apply_alignment, 1)


if __name__ == "__main__":
    raise SystemExit(unittest.main())

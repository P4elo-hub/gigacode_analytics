#!/usr/bin/env python3
"""Legacy closed GAP rows are not open; deferred leftovers still are."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from routing_state_baseline import apply_decisions_table, classify_relates, collect_open_gaps


class CollectOpenGapsTest(unittest.TestCase):
    def test_inline_only(self) -> None:
        self.assertEqual(collect_open_gaps("text [GAP-NFR-06] more"), ["GAP-NFR-06"])

    def test_deferred_table_still_open(self) -> None:
        spec = (
            "p85 [GAP-NFR-06]\n\n"
            "| ID | Тип | Подтверждено? |\n"
            "| GAP-NFR-06 | Gap | Отложено (D-14) |\n"
        )
        self.assertEqual(collect_open_gaps(spec), ["GAP-NFR-06"])

    def test_closed_row_excluded(self) -> None:
        spec = "| GAP-X | Gap | закрыт |\n[GAP-X]\n"
        self.assertEqual(collect_open_gaps(spec), [])

    def test_open_row_kept(self) -> None:
        spec = "| GAP-OBS-06 | Gap | Не покрыто |\n[GAP-OBS-06]\n"
        self.assertEqual(collect_open_gaps(spec), ["GAP-OBS-06"])


class ClassifyRelatesTest(unittest.TestCase):
    def test_gap_id_wins(self) -> None:
        self.assertEqual(classify_relates("GAP-NFR-06, Q-01", leftover_gaps=False), "gaps")

    def test_ch_id_not_stolen_by_leftover_gaps(self) -> None:
        self.assertEqual(classify_relates("CH-13, Q-42", leftover_gaps=True), "challenges")

    def test_alignment_code(self) -> None:
        self.assertEqual(classify_relates("F-12", leftover_gaps=True), "alignment")

    def test_q_only_follows_leftover(self) -> None:
        self.assertEqual(classify_relates("Q-01", leftover_gaps=True), "gaps")
        self.assertEqual(classify_relates("Q-01", leftover_gaps=False), "challenges")


class ApplyDecisionsRelatesTest(unittest.TestCase):
    def test_ch_pending_with_leftover_counts_as_challenges(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="relates-"))
        try:
            path = tmp / "decisions.md"
            path.write_text(
                "# DECISIONS\n\n"
                "| ID | Relates | Prompt | Options | Decision | Status | Date |\n"
                "|----|---------|--------|---------|----------|--------|------|\n"
                "| D-01 | CH-13 | leftover? | A) apply | A | pending-apply | 2026-09-19 |\n",
                encoding="utf-8",
            )
            status = SimpleNamespace(open_gaps=["GAP-LEFTOVER"])
            apply_decisions_table(status, {"decisions": path})
            self.assertEqual(status.decisions_pending_apply, 1)
            self.assertEqual(status.decisions_pending_apply_gaps, 0)
            self.assertEqual(status.decisions_pending_apply_challenges, 1)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

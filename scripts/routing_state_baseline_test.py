#!/usr/bin/env python3
"""Deferred / closed GAP rows are not open for dispatch."""

from __future__ import annotations

import unittest

from routing_state_baseline import collect_open_gaps


class CollectOpenGapsTest(unittest.TestCase):
    def test_inline_only(self) -> None:
        self.assertEqual(collect_open_gaps("text [GAP-NFR-06] more"), ["GAP-NFR-06"])

    def test_deferred_table_excludes_inline(self) -> None:
        spec = (
            "p85 [GAP-NFR-06]\n\n"
            "| ID | Тип | Подтверждено? |\n"
            "| GAP-NFR-06 | Gap | Отложено (D-14) |\n"
        )
        self.assertEqual(collect_open_gaps(spec), [])

    def test_closed_row_excluded(self) -> None:
        spec = "| GAP-X | Gap | закрыт |\n[GAP-X]\n"
        self.assertEqual(collect_open_gaps(spec), [])

    def test_open_row_kept(self) -> None:
        spec = "| GAP-OBS-06 | Gap | Не покрыто |\n[GAP-OBS-06]\n"
        self.assertEqual(collect_open_gaps(spec), ["GAP-OBS-06"])


if __name__ == "__main__":
    unittest.main()

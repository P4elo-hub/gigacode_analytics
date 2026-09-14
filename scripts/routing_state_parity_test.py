#!/usr/bin/env python3
"""Phase 11: collectors vs routing-state overlay parity (replay, match/mismatch)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

from pipeline_routing_state import (  # noqa: E402
    STATUS_OVERLAY_FIELDS,
    default_replay_path,
    example_payload,
    load_spec_routing_conditions,
)
from routing_state_parity import compare, main  # noqa: E402
from routing_state_replay_from_collectors import snapshot, write_fixture  # noqa: E402

REPLAY_SLUGS = (
    "pipeline-viewer-smoke",
    "bph-moex-tax",
    "composite-active-order-commission",
    "og-trading-order-yield",
)


def _mini_feature(root: Path, slug: str) -> None:
    fw = root / "Feature-writing" / slug
    fw.mkdir(parents=True)
    ctx = root / "Feature-context"
    ctx.mkdir(parents=True)
    (ctx / f"{slug}.md").write_text("# ctx\n\nVerified.\n", encoding="utf-8")
    (fw / f"{slug}.md").write_text("# spec\n\n[GAP-A]\n", encoding="utf-8")
    (fw / f"{slug}-challenges.md").write_text("# CH\n", encoding="utf-8")


class RoutingConditionsCoverageTest(unittest.TestCase):
    def test_status_fields_cover_overlay(self) -> None:
        data = load_spec_routing_conditions(ROOT)
        fields = data.get("status_fields") or {}
        self.assertTrue(set(STATUS_OVERLAY_FIELDS) <= set(fields))
        self.assertEqual(data.get("validate_ids"), ["routing-state-missing", "routing-state-stale"])
        stale_vs = data.get("stale_vs") or []
        self.assertEqual(
            list(stale_vs),
            ["spec", "context", "decisions", "challenges", "alignment", "gaps_map", "challenges_map"],
        )


class ReplayParityTest(unittest.TestCase):
    def test_identity_replay_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            slug = "parity-id"
            _mini_feature(root, slug)
            payload = snapshot(root, slug)
            replay = root / "replay.json"
            replay.write_text(json.dumps(payload), encoding="utf-8")
            report = compare(root, slug, replay=replay)
            self.assertTrue(report["match"], report)
            self.assertTrue(report["dispatch_match"])
            self.assertEqual(report["collector_dispatch"]["next_step"], "resolve-gaps")

    def test_mutated_open_gaps_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            slug = "parity-diff"
            _mini_feature(root, slug)
            payload = snapshot(root, slug)
            payload["fields"]["open_gaps"] = []
            replay = root / "replay.json"
            replay.write_text(json.dumps(payload), encoding="utf-8")
            report = compare(root, slug, replay=replay)
            self.assertFalse(report["match"])
            row = next(item for item in report["fields"] if item["field"] == "open_gaps")
            self.assertFalse(row["match"])
            self.assertEqual(report["collector_dispatch"]["next_step"], "resolve-gaps")
            self.assertEqual((report["analyzer_dispatch"] or {}).get("next_step"), "check-feature-code")
            with patch("sys.stdout", new=StringIO()):
                code = main([slug, "--root", str(root), "--replay", str(replay), "--strict"])
            self.assertEqual(code, 1)

    def test_strict_identity_exit_0(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            slug = "parity-ok"
            _mini_feature(root, slug)
            replay = write_fixture(root, slug)
            with patch("sys.stdout", new=StringIO()):
                code = main([slug, "--root", str(root), "--replay", str(replay), "--strict", "--json"])
            self.assertEqual(code, 0)

    def test_missing_json_is_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            slug = "parity-missing"
            _mini_feature(root, slug)
            report = compare(root, slug)
            self.assertFalse(report["match"])
            self.assertEqual(report["load_error"], "missing")


class LiveReplayFixturesTest(unittest.TestCase):
    def test_committed_replays_strict_pass(self) -> None:
        for slug in REPLAY_SLUGS:
            path = default_replay_path(ROOT, slug)
            if not path.is_file():
                self.skipTest(f"missing replay fixture {path}")
            with self.subTest(slug=slug):
                report = compare(ROOT, slug, replay=path)
                self.assertTrue(report["match"], json.dumps(report, default=str)[:2000])


class ExamplePayloadRoundtripTest(unittest.TestCase):
    def test_example_has_overlay_fields(self) -> None:
        fields = example_payload("demo")["fields"]
        self.assertTrue(set(STATUS_OVERLAY_FIELDS) <= set(fields))


if __name__ == "__main__":
    unittest.main()

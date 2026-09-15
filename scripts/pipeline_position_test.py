#!/usr/bin/env python3
"""Graph-constrained dispatch: only outgoing edges from current position."""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from pipeline_dispatch import build_dispatch  # noqa: E402
from pipeline_position import allowed_next_steps, record_position  # noqa: E402
from pipeline_routing_state import example_payload, load_routing_state, routing_state_path  # noqa: E402
from pipeline_runtime import load_pipeline_schema  # noqa: E402

SLUG = "pos-demo"


class PositionAndGraphTest(unittest.TestCase):
    def test_incomplete_step_may_repeat(self) -> None:
        schema = load_pipeline_schema("spec")
        allowed = allowed_next_steps(
            schema, {"step": "resolve-challenges", "result": "retry"}
        )
        assert allowed is not None
        self.assertIn("resolve-challenges", allowed)
        self.assertIn("check-feature", allowed)
        self.assertNotIn("write-feature", allowed)

    def test_foreign_pack_step_does_not_constrain(self) -> None:
        schema = load_pipeline_schema("calibration")
        allowed = allowed_next_steps(
            schema, {"step": "resolve-gaps", "result": "fail"}
        )
        self.assertIsNone(allowed)

    def test_challenge_ok_cannot_jump_to_check(self) -> None:
        schema = load_pipeline_schema("spec")
        allowed = allowed_next_steps(
            schema, {"step": "challenge-feature", "result": "ok"}
        )
        assert allowed is not None
        self.assertIn("resolve-challenges", allowed)
        self.assertIn("analyze-routing", allowed)
        self.assertNotIn("check-feature", allowed)

    def test_record_position_preserves_mtime(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="pos-mtime-"))
        try:
            fw = tmp / "Feature-writing" / SLUG
            fw.mkdir(parents=True)
            path = routing_state_path(tmp, SLUG)
            path.write_text(json.dumps(example_payload(SLUG)), encoding="utf-8")
            older = time.time() - 120
            os.utime(path, (older, older))
            before = path.stat().st_mtime
            self.assertTrue(record_position(tmp, SLUG, "check-feature", "ok"))
            self.assertEqual(path.stat().st_mtime, before)
            stored, err = load_routing_state(path, slug=SLUG)
            self.assertEqual(err, "")
            assert stored is not None
            self.assertEqual(stored["position"]["step"], "check-feature")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_dispatch_from_challenge_skips_check_feature(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="pos-disp-"))
        try:
            ctx = tmp / "Feature-context"
            ctx.mkdir()
            (ctx / f"{SLUG}.md").write_text("# ctx\n\nVerified.\n", encoding="utf-8")
            fw = tmp / "Feature-writing" / SLUG
            fw.mkdir(parents=True)
            spec = fw / f"{SLUG}.md"
            spec.write_text(f"# {SLUG}\n", encoding="utf-8")
            (fw / f"{SLUG}-gaps-resolved.md").write_text("# GAPS_MAP\n", encoding="utf-8")
            (fw / f"{SLUG}-challenges.md").write_text(
                "# CH\n\n| ID | § | Q | type | severity | status |\n"
                "|----|---|----|-----|----------|--------|\n"
                "| CH-01 | §1 | q | t | Major | resolved |\n",
                encoding="utf-8",
            )
            (fw / f"{SLUG}-decisions.md").write_text(
                "# DECISIONS\n\n"
                "| ID | Relates | Prompt | Options | Decision | Status | Date |\n"
                "|----|---------|--------|---------|----------|--------|------|\n"
                "| D-01 | CH-01 | topic | A) one | pick A | pending-apply | 2026-09-15 |\n",
                encoding="utf-8",
            )
            spec_at = time.time() - 180
            os.utime(spec, (spec_at, spec_at))
            payload = example_payload(SLUG)
            payload["fields"]["has_decisions"] = True
            payload["fields"]["has_gaps_map"] = True
            payload["fields"]["has_challenges"] = True
            payload["fields"]["decisions_pending_apply"] = 1
            payload["fields"]["needs_check_feature"] = True
            payload["position"] = {"step": "challenge-feature", "result": "ok"}
            path = routing_state_path(tmp, SLUG)
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            newest = time.time() + 60
            os.utime(path, (newest, newest))
            dispatch = build_dispatch(tmp, SLUG, "spec")
            self.assertEqual(dispatch["next_step"], "resolve-challenges")
            self.assertNotEqual(dispatch["next_step"], "check-feature")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

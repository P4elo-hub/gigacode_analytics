#!/usr/bin/env python3
"""Generic inner cycle: same agent, many params, concat, no routing between calls."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from inner_cycle import (  # noqa: E402
    ACTION_ASSEMBLE,
    ACTION_DONE,
    ACTION_TASK,
    apply_assemble,
    cycle_artifacts_open,
    next_inner_cycle,
)

SLUG = "brief-summary"


def _calls() -> list[dict]:
    return [
        {"agent": "spec-writer", "param": "goal", "artifact": f"{SLUG}.part-goal.md"},
        {"agent": "spec-writer", "param": "value", "artifact": f"{SLUG}.part-value.md"},
        {
            "agent": "spec-writer",
            "param": "stakeholders",
            "artifact": f"{SLUG}.part-stakeholders.md",
        },
    ]


class InnerCycleGenericTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="inner-cycle-"))
        self.folder = self.tmp / "Feature-writing" / SLUG
        self.folder.mkdir(parents=True)
        self.out = self.folder / f"{SLUG}.md"
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _next(self) -> dict:
        return next_inner_cycle(
            SLUG, self.folder, calls=_calls(), out=self.out, assemble="concat"
        )

    def test_walks_params_then_concat_then_done(self) -> None:
        seen: list[str] = []
        for _ in range(10):
            decision = self._next()
            if decision["action"] == ACTION_TASK:
                self.assertEqual(decision["subagent"], "spec-writer")
                seen.append(str(decision["param"]))
                Path(decision["part_file"]).write_text(
                    f"# {decision['param']}\n", encoding="utf-8"
                )
                continue
            if decision["action"] == ACTION_ASSEMBLE:
                self.assertIsNone(decision["subagent"])
                applied = apply_assemble(decision)
                self.assertFalse(applied["missing_parts"])
                continue
            self.assertEqual(decision["action"], ACTION_DONE)
            self.assertFalse(decision["open"])
            break
        else:
            self.fail("cycle did not reach done")
        self.assertEqual(seen, ["goal", "value", "stakeholders"])
        text = self.out.read_text(encoding="utf-8")
        self.assertIn("# goal", text)
        self.assertIn("# value", text)
        self.assertIn("# stakeholders", text)
        self.assertFalse(list(self.folder.glob(f"{SLUG}.part-*.md")))

    def test_second_cell_shape_is_just_another_call_list(self) -> None:
        decision = self._next()
        self.assertEqual(decision["param"], "goal")
        (self.folder / f"{SLUG}.part-goal.md").write_text("# goal\n", encoding="utf-8")
        decision = self._next()
        self.assertEqual(decision["param"], "value")

    def test_open_until_concat(self) -> None:
        cycle = {"item_file": "{slug}.part-{param}.md", "out": "{slug}.md"}
        (self.folder / f"{SLUG}.part-goal.md").write_text("# goal\n", encoding="utf-8")
        self.assertTrue(
            cycle_artifacts_open(self.folder, self.out, SLUG, cycle, "2099-01-01T00:00:00Z")
        )
        for name in ("value", "stakeholders"):
            (self.folder / f"{SLUG}.part-{name}.md").write_text(f"# {name}\n", encoding="utf-8")
        apply_assemble(self._next())
        self.assertFalse(
            cycle_artifacts_open(self.folder, self.out, SLUG, cycle, "2000-01-01T00:00:00Z")
        )


class CloseCycleCellTest(unittest.TestCase):
    def test_done_stamps_position_and_clears_marker(self) -> None:
        from inner_cycle import close_cycle_cell
        from pipeline_active_task import load_active_task, save_active_task
        from pipeline_position import resolve_position
        from pipeline_routing_state import example_payload, routing_state_path

        tmp = Path(tempfile.mkdtemp(prefix="cycle-close-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        slug = "cell-close"
        fw = tmp / "Feature-writing" / slug
        fw.mkdir(parents=True)
        path = routing_state_path(tmp, slug)
        path.write_text(
            json.dumps(example_payload(slug), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        save_active_task(
            tmp, slug=slug, step="write-feature", subagent="spec-writer", persistent=True
        )
        closed = close_cycle_cell(tmp, slug, "write-feature", pipeline_id="spec")
        self.assertTrue(closed["closed"])
        self.assertTrue(closed["position_recorded"])
        self.assertIsNone(load_active_task(tmp))
        standing = resolve_position(tmp, slug, "spec")
        self.assertEqual(standing["step"], "write-feature")
        self.assertEqual(standing["result"], "ok")

    def test_finished_marker_closes_even_when_dispatch_left_the_cell(self) -> None:
        from inner_cycle import close_finished_cycle_marker
        from pipeline_active_task import load_active_task, save_active_task
        from pipeline_position import resolve_position
        from pipeline_routing_state import example_payload, routing_state_path

        tmp = Path(tempfile.mkdtemp(prefix="cycle-marker-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        slug = "cell-close-done"
        fw = tmp / "Feature-writing" / slug
        fw.mkdir(parents=True)
        (fw / f"{slug}.md").write_text("# spec\n", encoding="utf-8")
        path = routing_state_path(tmp, slug)
        payload = example_payload(slug)
        payload["fields"]["has_spec"] = False
        payload["position"] = {
            "step": "analyze-routing",
            "result": "ok",
            "updated_at": "2026-09-16T07:45:00Z",
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        save_active_task(
            tmp, slug=slug, step="write-feature", subagent="spec-writer", persistent=True
        )
        closed = close_finished_cycle_marker(tmp, slug, pipeline_id="spec")
        self.assertIsNotNone(closed)
        self.assertTrue(closed["closed"])
        self.assertIsNone(load_active_task(tmp))
        standing = resolve_position(tmp, slug, "spec")
        self.assertEqual(standing["step"], "write-feature")


class InnerCycleGraphNodeTest(unittest.TestCase):
    def test_write_feature_cell_declares_cycle(self) -> None:
        from inner_cycle import cycle_config_for_step

        cfg = cycle_config_for_step("spec", "write-feature")
        self.assertTrue(cfg)
        self.assertEqual(cfg.get("assemble"), "write_feature")
        self.assertEqual(cfg.get("param"), "block_id")
        self.assertEqual(cfg.get("close"), "on_done")
        self.assertFalse(cycle_config_for_step("spec", "check-feature"))


if __name__ == "__main__":
    unittest.main()

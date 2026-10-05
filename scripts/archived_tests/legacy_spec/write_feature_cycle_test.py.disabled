#!/usr/bin/env python3
"""write_feature_cycle walks approved blocks: task → assemble → done."""

from __future__ import annotations

import io
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from pipeline_active_task import save_active_task, write_cycle_still_open  # noqa: E402
from pipeline_delegate import build_delegate  # noqa: E402
from pipeline_routing_state import example_payload, routing_state_path  # noqa: E402
from write_feature import part_filename  # noqa: E402
from write_feature_cycle import (  # noqa: E402
    ACTION_ASSEMBLE,
    ACTION_DONE,
    ACTION_TASK,
    apply_assemble,
    main as cycle_main,
    next_write_cycle,
    save_cycle_plan,
)

SLUG = "cycle-demo"
SECTIONS = "1.1,1.2-usecase,1.3-usecase"
BLOCKS = ("goal", "usecase-as-is", "usecase-to-be")


class WriteFeatureCycleNextTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="wf-cycle-"))
        self.folder = self.tmp / "Feature-writing" / SLUG
        self.folder.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _next(self) -> dict:
        return next_write_cycle(
            SLUG,
            self.folder,
            sections=SECTIONS,
            spec_file=self.folder / f"{SLUG}.md",
        )

    def _write_part(self, block_id: str) -> None:
        (self.folder / part_filename(SLUG, block_id)).write_text(
            f"# {block_id}\n", encoding="utf-8"
        )

    def test_empty_folder_asks_first_block(self) -> None:
        decision = self._next()
        self.assertEqual(decision["action"], ACTION_TASK)
        self.assertEqual(decision["block_id"], "goal")
        self.assertEqual(decision["subagent"], "spec-writer")
        self.assertEqual(decision["check"]["mode"], "check-part")
        self.assertTrue(decision["open"])
        self.assertEqual(list(decision["remaining"]), list(BLOCKS))

    def test_after_goal_asks_next_block(self) -> None:
        self._write_part("goal")
        decision = self._next()
        self.assertEqual(decision["action"], ACTION_TASK)
        self.assertEqual(decision["block_id"], "usecase-as-is")
        self.assertEqual(decision["remaining"], ["usecase-as-is", "usecase-to-be"])

    def test_boxed_loop_writes_spec(self) -> None:
        seen: list[str] = []
        for _ in range(10):
            decision = self._next()
            if decision["action"] == ACTION_TASK:
                seen.append(str(decision["block_id"]))
                Path(decision["part_file"]).write_text(
                    f"# {decision['block_id']}\n", encoding="utf-8"
                )
                continue
            if decision["action"] == ACTION_ASSEMBLE:
                applied = apply_assemble(decision)
                self.assertFalse(applied["missing_parts"])
                continue
            self.assertEqual(decision["action"], ACTION_DONE)
            self.assertFalse(decision["open"])
            break
        else:
            self.fail("cycle did not reach done")
        self.assertEqual(seen, list(BLOCKS))
        spec = self.folder / f"{SLUG}.md"
        self.assertTrue(spec.is_file())
        text = spec.read_text(encoding="utf-8")
        self.assertIn("# goal", text)
        self.assertIn("# usecase-as-is", text)
        self.assertIn("# usecase-to-be", text)
        self.assertFalse(list(self.folder.glob(f"{SLUG}.part-*.md")))

    def test_existing_spec_without_parts_is_done(self) -> None:
        (self.folder / f"{SLUG}.md").write_text("# already\n", encoding="utf-8")
        decision = self._next()
        self.assertEqual(decision["action"], ACTION_DONE)
        self.assertFalse(decision["open"])

    def test_assemble_rejected_unless_ready(self) -> None:
        with self.assertRaises(ValueError):
            apply_assemble(self._next())

    def test_saved_plan_without_cli_sections(self) -> None:
        save_cycle_plan(self.folder, sections=SECTIONS, brief="demo brief")
        decision = next_write_cycle(SLUG, self.folder, spec_file=self.folder / f"{SLUG}.md")
        self.assertEqual(decision["block_id"], "goal")

    def test_cli_assemble_after_parts(self) -> None:
        for block_id in BLOCKS:
            self._write_part(block_id)
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = cycle_main(
                [SLUG, "--workspace", str(self.tmp), "--sections", SECTIONS, "--assemble"]
            )
        self.assertEqual(code, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["action"], ACTION_DONE)
        self.assertTrue((self.folder / f"{SLUG}.md").is_file())
        self.assertEqual(self._next()["action"], ACTION_DONE)

    def test_cli_assemble_refuses_while_parts_missing(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = cycle_main(
                [SLUG, "--workspace", str(self.tmp), "--sections", SECTIONS, "--assemble"]
            )
        self.assertEqual(code, 1)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["action"], ACTION_TASK)

    def test_cycle_open_until_assemble(self) -> None:
        self._write_part("goal")
        active = save_active_task(
            self.tmp,
            slug=SLUG,
            step="write-feature",
            subagent="spec-writer",
            persistent=True,
        )
        self.assertTrue(write_cycle_still_open(self.tmp, SLUG, active))
        for block_id in ("usecase-as-is", "usecase-to-be"):
            self._write_part(block_id)
        apply_assemble(self._next())
        self.assertFalse(write_cycle_still_open(self.tmp, SLUG, active))


class WriteFeatureCycleDelegateTest(unittest.TestCase):
    def test_delegate_embeds_next_block(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="wf-cycle-del-"))
        try:
            ctx = tmp / "Feature-context" / f"{SLUG}.md"
            ctx.parent.mkdir(parents=True)
            ctx.write_text("# context\n", encoding="utf-8")
            fw = tmp / "Feature-writing" / SLUG
            fw.mkdir(parents=True)
            save_cycle_plan(fw, sections=SECTIONS)
            payload = example_payload(SLUG)
            payload["fields"]["has_spec"] = False
            payload["fields"]["has_context"] = True
            path = routing_state_path(tmp, SLUG)
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            newest = time.time() + 60
            older = time.time() - 120
            os.utime(path, (newest, newest))
            os.utime(ctx, (older, older))
            result = build_delegate(tmp, SLUG, cli="qwen", pipeline_id="spec")
            self.assertEqual(result.get("action"), "write_feature_cycle")
            cycle = result.get("cycle") or {}
            self.assertEqual(cycle.get("action"), ACTION_TASK)
            self.assertEqual(cycle.get("block_id"), "goal")
            self.assertEqual(cycle.get("subagent"), "spec-writer")
            self.assertIn("param=`goal`", result.get("instruction") or "")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_done_closes_cell_and_dispatch_leaves_write_feature(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="wf-cycle-done-"))
        try:
            ctx = tmp / "Feature-context" / f"{SLUG}.md"
            ctx.parent.mkdir(parents=True)
            ctx.write_text("# context\n\nVerified.\n", encoding="utf-8")
            fw = tmp / "Feature-writing" / SLUG
            fw.mkdir(parents=True)
            spec = fw / f"{SLUG}.md"
            spec.write_text(f"# {SLUG}\n", encoding="utf-8")
            payload = example_payload(SLUG)
            payload["fields"]["has_spec"] = False
            payload["fields"]["has_context"] = True
            payload["position"] = {
                "step": "analyze-routing",
                "result": "ok",
                "updated_at": "2026-09-16T07:45:00Z",
            }
            path = routing_state_path(tmp, SLUG)
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            spec_at = time.time()
            json_at = spec_at - 120
            os.utime(spec, (spec_at, spec_at))
            os.utime(path, (json_at, json_at))
            os.utime(ctx, (json_at - 60, json_at - 60))
            save_active_task(
                tmp,
                slug=SLUG,
                step="write-feature",
                subagent="spec-writer",
                persistent=True,
            )
            result = build_delegate(tmp, SLUG, cli="qwen", pipeline_id="spec")
            self.assertNotEqual(result.get("action"), "write_feature_cycle")
            self.assertEqual(result.get("action"), "task")
            dispatch = result.get("dispatch") or {}
            self.assertEqual(dispatch.get("next_step"), "analyze-routing")
            task = result.get("task") or {}
            self.assertEqual(task.get("subagent_type") or dispatch.get("next_subagent"), "routing-analyzer")
            from pipeline_active_task import load_active_task
            from pipeline_position import resolve_position

            standing = resolve_position(tmp, SLUG, "spec")
            self.assertEqual(standing["step"], "write-feature")
            self.assertEqual(standing["result"], "ok")
            active = load_active_task(tmp)
            self.assertIsNotNone(active)
            self.assertEqual(active["step"], "analyze-routing")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

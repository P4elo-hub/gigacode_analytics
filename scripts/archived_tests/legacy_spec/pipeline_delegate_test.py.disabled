#!/usr/bin/env python3
"""Tonight's crash: last_ok challenge-feature + needs_check + pending-apply.

Graph has challenge-feature → resolve-challenges, not → check-feature.
pending-apply must win so delegate does not return action=error.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from pipeline_active_task import save_active_task  # noqa: E402
from pipeline_delegate import build_delegate  # noqa: E402
from pipeline_routing_state import example_payload, routing_state_path  # noqa: E402

SLUG = "hook-pending-apply"


class PendingApplyAfterChallengeTest(unittest.TestCase):
    def test_delegate_follows_graph_to_resolve_challenges(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="delegate-pending-"))
        try:
            ctx = tmp / "Feature-context" / f"{SLUG}.md"
            ctx.parent.mkdir(parents=True)
            ctx.write_text("# context\n\nVerified.\n", encoding="utf-8")
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
            payload["fields"]["needs_check_feature_reason"] = (
                "SPEC новее GAPS_MAP — перепроверка после resolve-gaps"
            )
            path = routing_state_path(tmp, SLUG)
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            newest = time.time() + 60
            os.utime(path, (newest, newest))

            run_dir = tmp / "agent-logs" / SLUG / "runs" / "run-001"
            run_dir.mkdir(parents=True)
            (run_dir.parent.parent / "manifest.json").write_text(
                json.dumps({"slug": SLUG, "current_run": "run-001", "runs": ["run-001"]}, indent=2)
                + "\n",
                encoding="utf-8",
            )
            (run_dir / "run-log.jsonl").write_text(
                json.dumps(
                    {
                        "ts": "2026-09-15T18:14:04Z",
                        "step": "challenge-feature",
                        "subagent": "spec-challenger",
                        "result": "ok",
                        "attempt": 1,
                        "pipeline": "spec",
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            save_active_task(
                tmp,
                slug=SLUG,
                step="analyze-routing",
                subagent="routing-analyzer",
                cli="qwen",
                pipeline="spec",
            )
            result = build_delegate(tmp, SLUG, cli="qwen", pipeline_id="spec")
            self.assertTrue(result.get("ok"), msg=json.dumps(result, ensure_ascii=False))
            self.assertEqual(result.get("action"), "task")
            task = result.get("task") or {}
            self.assertEqual(task.get("step"), "resolve-challenges")
            self.assertEqual(task.get("subagent_type"), "challenge-resolver")
            self.assertNotEqual(result.get("action"), "error")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class AskUserResumeWithoutDelegateTest(unittest.TestCase):
    """needs-answer pause must authorize apply without a second delegate."""

    def _seed_needs_answer(self, tmp: Path) -> None:
        ctx = tmp / "Feature-context" / f"{SLUG}.md"
        ctx.parent.mkdir(parents=True)
        ctx.write_text("# context\n\nVerified.\n", encoding="utf-8")
        fw = tmp / "Feature-writing" / SLUG
        fw.mkdir(parents=True)
        spec = fw / f"{SLUG}.md"
        spec.write_text(f"# {SLUG}\n\n[GAP-01]\n", encoding="utf-8")
        (fw / f"{SLUG}-gaps-resolved.md").write_text("# GAPS_MAP\n", encoding="utf-8")
        (fw / f"{SLUG}-decisions.md").write_text(
            "# DECISIONS\n\n"
            "| ID | Relates | Prompt | Options | Decision | Status | Date |\n"
            "|----|---------|--------|---------|----------|--------|------|\n"
            "| D-01 | GAP-01 | topic | A) one |  | needs-answer | 2026-09-19 |\n",
            encoding="utf-8",
        )
        older = time.time() - 180
        for path in (spec, fw / f"{SLUG}-gaps-resolved.md", fw / f"{SLUG}-decisions.md"):
            os.utime(path, (older, older))
        payload = example_payload(SLUG, open_gaps=["GAP-01"])
        payload["fields"]["has_decisions"] = True
        payload["fields"]["has_gaps_map"] = True
        payload["fields"]["decisions_needs_answer"] = 1
        payload["fields"]["decisions_pending_apply"] = 0
        payload["position"] = {
            "step": "analyze-routing",
            "result": "ok",
            "updated_at": "2026-09-19T17:41:27Z",
        }
        path = routing_state_path(tmp, SLUG)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.utime(path, (time.time() + 60, time.time() + 60))

    def test_ask_user_reserves_apply_task(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="delegate-ask-resume-"))
        try:
            self._seed_needs_answer(tmp)
            result = build_delegate(tmp, SLUG, cli="qwen", pipeline_id="spec")
            self.assertTrue(result.get("ok"), msg=json.dumps(result, ensure_ascii=False))
            self.assertEqual(result.get("action"), "ask_user")
            task = result.get("task") or {}
            self.assertEqual(task.get("step"), "resolve-gaps")
            self.assertEqual(task.get("subagent_type"), "gap-resolver")
            active = result.get("active_task") or {}
            self.assertEqual(active.get("step"), "resolve-gaps")
            self.assertEqual(active.get("subagent"), "gap-resolver")
            instruction = result.get("instruction") or ""
            self.assertIn("НЕ вызывай `pipeline_delegate.py` между ответом и apply", instruction)
            self.assertIn("gap-resolver", instruction)
            self.assertNotIn("запиши Decision/Status → снова `pipeline_delegate.py`", instruction)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_hook_allows_apply_without_second_delegate(self) -> None:
        from pipeline_before_subagent import validate_task

        tmp = Path(tempfile.mkdtemp(prefix="delegate-ask-hook-"))
        try:
            self._seed_needs_answer(tmp)
            result = build_delegate(tmp, SLUG, cli="qwen", pipeline_id="spec")
            self.assertEqual(result.get("action"), "ask_user")
            allow = validate_task(tmp, "gap-resolver", pipeline_arg="spec")
            self.assertEqual(
                allow["hookSpecificOutput"]["permissionDecision"],
                "allow",
                msg=json.dumps(allow, ensure_ascii=False),
            )
            deny = validate_task(tmp, "spec-reviewer", pipeline_arg="spec")
            self.assertEqual(
                deny["hookSpecificOutput"]["permissionDecision"],
                "deny",
                msg=json.dumps(deny, ensure_ascii=False),
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class AskUserNodeFlagTest(unittest.TestCase):
    def test_resolvers_declare_ask(self) -> None:
        from pipeline_runtime import node_asks_user

        self.assertTrue(node_asks_user("spec", "resolve-gaps"))
        self.assertTrue(node_asks_user("spec", "resolve-challenges"))
        self.assertTrue(node_asks_user("spec", "resolve-code-alignment"))
        self.assertFalse(node_asks_user("spec", "check-feature"))
        self.assertFalse(node_asks_user("spec", "write-feature"))

    def test_needs_answer_pauses_only_on_ask_nodes(self) -> None:
        from pipeline_status import finalize_orchestrator_mode

        status = SimpleNamespace(
            ready=False,
            next_step="check-feature",
            decisions_needs_answer=1,
        )
        finalize_orchestrator_mode(status, "spec")
        self.assertEqual(status.orchestrator_mode, "delegate")

        status.next_step = "resolve-gaps"
        finalize_orchestrator_mode(status, "spec")
        self.assertEqual(status.orchestrator_mode, "ask_user")
        self.assertFalse(status.must_continue)


if __name__ == "__main__":
    unittest.main()

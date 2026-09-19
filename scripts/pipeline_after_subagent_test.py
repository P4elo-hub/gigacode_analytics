#!/usr/bin/env python3
"""infer_result must not treat quality-gates «fail 0» as a failed step.

Battle path: PreToolUse (spec-reviewer) → stand-in agent → SubagentStop hook
(`pipeline_after_subagent.py`), then stamp + dispatch. Same slice as Qwen.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from pipeline_after_subagent import infer_result, infer_run_outcome  # noqa: E402
from pipeline_routing_state import example_payload, load_routing_state, routing_state_path  # noqa: E402

AGENT = SCRIPTS / "fixtures" / "spec_reviewer_fail_zero_agent.py"
SLUG = "hook-fail-zero"


class InferResultTest(unittest.TestCase):
    def test_quality_gates_fail_zero_colon_is_ok(self) -> None:
        message = (
            "Ревизия завершена.\n"
            "`python3 scripts/quality_gates.py` → **PASS** (fail: 0, warn: 1).\n"
        )
        self.assertEqual(infer_result(message), "ok")

    def test_quality_gates_fail_zero_no_colon_is_ok(self) -> None:
        message = (
            "**Структурные gates (`quality_gates.py`):** PASS · fail 0 · warn 1. "
            "Warn `QG-CONTRACT-02`."
        )
        self.assertEqual(infer_result(message), "ok")

    def test_spec_quote_error_rate_is_ok(self) -> None:
        self.assertEqual(
            infer_result("| Error rate | [GAP-NFR-10] | Для событий сводки не задан |"),
            "ok",
        )

    def test_quality_report_fail_count_is_finished_not_abort(self) -> None:
        self.assertEqual(infer_result("quality_gates → FAIL · fail 3 · warn 0"), "ok")

    def test_ask_parent_retry_word_is_finished(self) -> None:
        self.assertEqual(infer_result("ASK_PARENT — retry after needs-answer"), "ok")

    def test_cli_timeout_wrapper_is_aborted(self) -> None:
        self.assertEqual(infer_result("Subagent failed: timeout"), "fail")

    def test_empty_is_ok(self) -> None:
        self.assertEqual(infer_result(""), "ok")

    def test_structured_timeout_status_is_aborted(self) -> None:
        self.assertEqual(infer_run_outcome({"status": "timeout"}), "fail")

    def test_structured_error_is_aborted(self) -> None:
        self.assertEqual(infer_run_outcome({"error": "killed"}), "fail")


class SpecReviewerSubagentStopBattleTest(unittest.TestCase):
    """Live 2026-09-15 loop: check-feature «PASS · fail 0» must stamp, not re-check."""

    def test_spec_reviewer_fail_zero_stamps_and_does_not_recheck(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="hook-fail-zero-"))
        try:
            self._materialize(tmp)
            self._seed_run_log(tmp, step="analyze-routing", subagent="routing-analyzer", result="ok")
            self._save_active_task(tmp)

            before = self._run_hook(
                tmp,
                SCRIPTS / "pipeline_before_subagent.py",
                {
                    "hook_event_name": "PreToolUse",
                    "tool_name": "task",
                    "tool_input": {"subagent_type": "spec-reviewer"},
                },
            )
            decision = before["hookSpecificOutput"]["permissionDecision"]
            self.assertEqual(decision, "allow", msg=json.dumps(before, ensure_ascii=False))

            last_message = self._run_spec_reviewer(tmp)
            self.assertIn("PASS · fail 0", last_message)
            self.assertEqual(infer_result(last_message), "ok")

            after = self._run_hook(
                tmp,
                SCRIPTS / "pipeline_after_subagent.py",
                {
                    "hook_event_name": "SubagentStop",
                    "agent_type": "spec-reviewer",
                    "last_assistant_message": last_message,
                },
                extra_args=["--cli", "qwen", "--pipeline", "spec"],
            )
            context = after["hookSpecificOutput"]["additionalContext"]
            self.assertIn("check-feature → spec-reviewer (ok)", context, msg=context)

            run_log = tmp / "agent-logs" / SLUG / "runs" / "run-001" / "run-log.jsonl"
            rows = [json.loads(line) for line in run_log.read_text(encoding="utf-8").splitlines() if line.strip()]
            check_rows = [row for row in rows if row.get("step") == "check-feature"]
            self.assertTrue(check_rows, msg="SubagentStop did not append check-feature")
            self.assertEqual(check_rows[-1].get("result"), "ok")
            self.assertEqual(check_rows[-1].get("subagent"), "spec-reviewer")

            stored, err = load_routing_state(routing_state_path(tmp, SLUG), slug=SLUG)
            self.assertEqual(err, "")
            assert stored is not None
            self.assertFalse(stored["fields"]["needs_check_feature"])
            self.assertIn("check-feature", stored.get("step_completion") or {})

            from pipeline_dispatch import build_dispatch

            dispatch = build_dispatch(tmp, SLUG, "spec")
            self.assertNotEqual(dispatch.get("next_step"), "check-feature")
            self.assertEqual(dispatch.get("next_step"), "resolve-gaps")
            self.assertEqual(dispatch.get("next_subagent"), "gap-resolver")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_real_spec_reviewer_failure_does_not_stamp(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="hook-real-fail-"))
        try:
            self._materialize(tmp)
            self._seed_run_log(tmp, step="analyze-routing", subagent="routing-analyzer", result="ok")
            self._save_active_task(tmp)
            after = self._run_hook(
                tmp,
                SCRIPTS / "pipeline_after_subagent.py",
                {
                    "hook_event_name": "SubagentStop",
                    "agent_type": "spec-reviewer",
                    "status": "timeout",
                    "last_assistant_message": "Subagent failed: timeout",
                },
                extra_args=["--cli", "qwen", "--pipeline", "spec"],
            )
            context = after["hookSpecificOutput"]["additionalContext"]
            self.assertIn("spec-reviewer (fail)", context, msg=context)
            stored, _ = load_routing_state(routing_state_path(tmp, SLUG), slug=SLUG)
            assert stored is not None
            self.assertTrue(stored["fields"]["needs_check_feature"])
            self.assertNotIn("check-feature", stored.get("step_completion") or {})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def _materialize(self, root: Path) -> None:
        ctx = root / "Feature-context" / f"{SLUG}.md"
        ctx.parent.mkdir(parents=True)
        ctx.write_text("# context\n\nVerified.\n", encoding="utf-8")
        fw = root / "Feature-writing" / SLUG
        fw.mkdir(parents=True)
        spec = fw / f"{SLUG}.md"
        spec.write_text(f"# {SLUG}\n\n[GAP-GOLDEN-01]\n", encoding="utf-8")
        (fw / f"{SLUG}-gaps-resolved.md").write_text("# GAPS_MAP\n", encoding="utf-8")
        (fw / f"{SLUG}-decisions.md").write_text(
            "# DECISIONS\n\n"
            "| ID | Relates | Prompt | Options | Decision | Status | Date |\n"
            "|----|---------|--------|---------|----------|--------|------|\n"
            "| D-01 | Q-01 | gap topic | A) one | pick A | pending-apply | 2026-09-12 |\n",
            encoding="utf-8",
        )
        spec_at = time.time() - 180
        os.utime(spec, (spec_at, spec_at))
        payload = example_payload(SLUG, open_gaps=["GAP-GOLDEN-01"])
        payload["fields"]["has_decisions"] = True
        payload["fields"]["has_gaps_map"] = True
        payload["fields"]["decisions_pending_apply"] = 1
        payload["fields"]["needs_check_feature"] = True
        payload["fields"]["needs_check_feature_reason"] = "нет check-feature после последней правки SPEC"
        path = routing_state_path(root, SLUG)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        newest = time.time() + 60
        os.utime(path, (newest, newest))

    def _seed_run_log(self, root: Path, *, step: str, subagent: str, result: str) -> None:
        run_dir = root / "agent-logs" / SLUG / "runs" / "run-001"
        run_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            "slug": SLUG,
            "current_run": "run-001",
            "runs": ["run-001"],
            "cli": "qwen",
        }
        (run_dir.parent.parent / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        row = {
            "ts": "2026-09-15T17:50:00Z",
            "step": step,
            "subagent": subagent,
            "result": result,
            "attempt": 1,
            "pipeline": "spec",
        }
        (run_dir / "run-log.jsonl").write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")

    def _save_active_task(self, root: Path) -> None:
        from pipeline_active_task import save_active_task

        save_active_task(
            root,
            slug=SLUG,
            step="check-feature",
            subagent="spec-reviewer",
            cli="qwen",
            pipeline="spec",
        )

    def _hook_env(self, root: Path) -> dict[str, str]:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(SCRIPTS)
        env["QWEN_PROJECT_DIR"] = str(root)
        return env

    def _run_hook(self, root: Path, script: Path, payload: dict, extra_args: list[str] | None = None) -> dict:
        cmd = [sys.executable, str(script), "--workspace", str(root), *(extra_args or [])]
        proc = subprocess.run(
            cmd,
            input=json.dumps(payload, ensure_ascii=False),
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
            env=self._hook_env(root),
        )
        self.assertEqual(
            proc.returncode,
            0,
            msg=f"{script.name} rc={proc.returncode}\nstdout={proc.stdout}\nstderr={proc.stderr}",
        )
        data = json.loads(proc.stdout)
        self.assertIsInstance(data, dict)
        return data

    def _run_spec_reviewer(self, root: Path) -> str:
        proc = subprocess.run(
            [sys.executable, str(AGENT), "--workspace", str(root), "--slug", SLUG],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
            env=self._hook_env(root),
        )
        self.assertEqual(
            proc.returncode,
            0,
            msg=f"spec-reviewer stand-in rc={proc.returncode}\nstderr={proc.stderr}",
        )
        self.assertIn("quality_gates rc=", proc.stderr)
        self.assertTrue((proc.stdout or "").strip(), msg="agent produced empty last message")
        return proc.stdout


class WriteFeatureCycleSubagentStopTest(unittest.TestCase):
    """One spec-writer block must not close write-feature or steal another slug."""

    SLUG = "write-cycle-hook"

    def test_mid_cycle_keeps_marker_and_position(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="hook-write-cycle-"))
        try:
            self._materialize_cycle(tmp)
            smoke = tmp / "Feature-writing" / "pipeline-viewer-smoke"
            smoke.mkdir(parents=True)
            (smoke / ".pipeline-active-task.json").write_text(
                json.dumps(
                    {
                        "slug": "pipeline-viewer-smoke",
                        "step": "resolve-gaps",
                        "subagent": "gap-resolver",
                        "started_at": "2099-01-01T00:00:00Z",
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            after = self._run_hook(
                tmp,
                SCRIPTS / "pipeline_after_subagent.py",
                {
                    "hook_event_name": "SubagentStop",
                    "agent_type": "spec-writer",
                    "last_assistant_message": "Блок goal записан в part-файл.",
                },
                extra_args=["--cli", "qwen", "--pipeline", "spec"],
            )
            context = after["hookSpecificOutput"]["additionalContext"]
            self.assertIn("cycle open", context, msg=context)

            from pipeline_active_task import load_active_task, load_active_task_latest

            active = load_active_task(tmp)
            self.assertIsNotNone(active)
            self.assertEqual(active["slug"], self.SLUG)
            self.assertEqual(active["step"], "write-feature")
            self.assertTrue(active.get("persistent"))
            latest = load_active_task_latest(tmp)
            self.assertEqual(latest["slug"], self.SLUG)

            stored, err = load_routing_state(routing_state_path(tmp, self.SLUG), slug=self.SLUG)
            self.assertEqual(err, "")
            assert stored is not None
            self.assertEqual((stored.get("position") or {}).get("step"), "analyze-routing")
            self.assertEqual((stored.get("position") or {}).get("result"), "ok")

            before = self._run_hook(
                tmp,
                SCRIPTS / "pipeline_before_subagent.py",
                {
                    "hook_event_name": "PreToolUse",
                    "tool_name": "task",
                    "tool_input": {"subagent_type": "spec-writer"},
                },
            )
            decision = before["hookSpecificOutput"]["permissionDecision"]
            reason = before["hookSpecificOutput"].get("permissionDecisionReason") or ""
            self.assertEqual(decision, "allow", msg=reason)
            self.assertNotIn("pipeline-viewer-smoke", reason)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_assemble_closes_cycle_and_stamps_position(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="hook-write-assemble-"))
        try:
            self._materialize_cycle(tmp)
            folder = tmp / "Feature-writing" / self.SLUG
            (folder / f"{self.SLUG}.part-goal.md").unlink()
            spec = folder / f"{self.SLUG}.md"
            spec.write_text(f"# {self.SLUG}\n", encoding="utf-8")
            after = self._run_hook(
                tmp,
                SCRIPTS / "pipeline_after_subagent.py",
                {
                    "hook_event_name": "SubagentStop",
                    "agent_type": "spec-writer",
                    "last_assistant_message": "Assemble готов. SPEC записан.",
                },
                extra_args=["--cli", "qwen", "--pipeline", "spec"],
            )
            context = after["hookSpecificOutput"]["additionalContext"]
            self.assertIn("position recorded", context, msg=context)

            from pipeline_active_task import load_active_task

            self.assertIsNone(load_active_task(tmp))
            stored, _ = load_routing_state(routing_state_path(tmp, self.SLUG), slug=self.SLUG)
            assert stored is not None
            self.assertEqual((stored.get("position") or {}).get("step"), "write-feature")
            self.assertEqual((stored.get("position") or {}).get("result"), "ok")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def _materialize_cycle(self, root: Path) -> None:
        ctx = root / "Feature-context" / f"{self.SLUG}.md"
        ctx.parent.mkdir(parents=True)
        ctx.write_text("# context\n\nVerified.\n", encoding="utf-8")
        fw = root / "Feature-writing" / self.SLUG
        fw.mkdir(parents=True)
        (fw / f"{self.SLUG}.part-goal.md").write_text("### goal\n\nЦель.\n", encoding="utf-8")
        payload = example_payload(self.SLUG)
        payload["fields"]["has_spec"] = False
        payload["fields"]["has_context"] = True
        payload["position"] = {
            "step": "analyze-routing",
            "result": "ok",
            "updated_at": "2026-09-16T07:45:00Z",
        }
        path = routing_state_path(root, self.SLUG)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self._seed_run_log(root, step="analyze-routing", subagent="routing-analyzer", result="ok")
        from pipeline_active_task import save_active_task

        save_active_task(
            root,
            slug=self.SLUG,
            step="write-feature",
            subagent="spec-writer",
            cli="qwen",
            pipeline="spec",
            persistent=True,
        )

    def _seed_run_log(self, root: Path, *, step: str, subagent: str, result: str) -> None:
        slug = self.SLUG
        run_dir = root / "agent-logs" / slug / "runs" / "run-001"
        run_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            "slug": slug,
            "current_run": "run-001",
            "runs": ["run-001"],
            "cli": "qwen",
        }
        (run_dir.parent.parent / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        row = {
            "ts": "2026-09-16T07:45:00Z",
            "step": step,
            "subagent": subagent,
            "result": result,
            "attempt": 1,
            "pipeline": "spec",
        }
        (run_dir / "run-log.jsonl").write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")

    def _hook_env(self, root: Path) -> dict[str, str]:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(SCRIPTS)
        env["QWEN_PROJECT_DIR"] = str(root)
        return env

    def _run_hook(self, root: Path, script: Path, payload: dict, extra_args: list[str] | None = None) -> dict:
        cmd = [sys.executable, str(script), "--workspace", str(root), *(extra_args or [])]
        proc = subprocess.run(
            cmd,
            input=json.dumps(payload, ensure_ascii=False),
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
            env=self._hook_env(root),
        )
        self.assertEqual(
            proc.returncode,
            0,
            msg=f"{script.name} rc={proc.returncode}\nstdout={proc.stdout}\nstderr={proc.stderr}",
        )
        data = json.loads(proc.stdout)
        self.assertIsInstance(data, dict)
        return data


if __name__ == "__main__":
    unittest.main()

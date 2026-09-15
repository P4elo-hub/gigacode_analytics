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


if __name__ == "__main__":
    unittest.main()

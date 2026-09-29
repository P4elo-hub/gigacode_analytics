"""Graph and dispatch contract for pack music-production."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from pipeline_dispatch import build_dispatch  # noqa: E402
from pipeline_dispatch_golden_test import run_case  # noqa: E402
from pipeline_pack import load_pack  # noqa: E402
from pipeline_runtime import load_pipeline_schema  # noqa: E402

PIPELINE = "music-production"
ASK = {"package-approval", "select-base", "revision-escalation", "final-approval"}
VERDICT_RULES = {
    "human_stop",
    "package_approve",
    "package_change_lyrics",
    "package_change_production",
    "base_select",
    "base_regenerate",
    "base_combine_direction",
    "base_change_lyrics",
    "base_change_production",
    "revision_accept",
    "revision_retry",
    "revision_rollback",
    "final_approve",
    "final_request_revision",
}
REQUIRED_CASES = {
    "package-approve-captured",
    "package-change-lyrics",
    "package-change-production",
    "package-stop",
    "base-select-captured",
    "base-regenerate-batch",
    "base-combine-direction",
    "base-change-lyrics",
    "base-change-production",
    "base-stop",
    "revision-escalation-budget",
    "revision-escalation-capability",
    "revision-accept",
    "revision-retry",
    "revision-rollback",
    "revision-stop",
    "final-approve-captured",
    "final-request-revision",
    "final-stop",
    "capture-pending-package",
    "capture-pending-base",
    "capture-pending-revision",
    "capture-pending-final",
    "revision-loop-plan",
    "revision-loop-edit",
    "revision-loop-compare",
}


class MusicGraphDispatchTest(unittest.TestCase):
    def test_human_gates_returns_and_pause(self) -> None:
        graph = load_pack(PIPELINE, ROOT)["graph"]
        nodes = {node["id"]: node for node in graph["nodes"]}
        for step in ASK:
            self.assertTrue(nodes[step].get("ask"), step)
        for node in graph["nodes"]:
            self.assertNotIn("cycle", node)
        edges = graph["edges"]
        conditions = {edge.get("condition") for edge in edges}
        self.assertIn("package_revise_lyrics", conditions)
        self.assertIn("package_revise_production", conditions)
        self.assertIn("human_stop", conditions)
        self.assertIn("decision_capture_pending", conditions)
        self.assertTrue(
            any(
                edge.get("from") == "revision-escalation"
                and edge.get("to") == "revision-escalation"
                for edge in edges
            )
        )
        self.assertTrue(
            any(edge.get("to") == "paused" and edge.get("condition") == "human_stop" for edge in edges)
        )
        capture_targets = {
            edge.get("to")
            for edge in edges
            if edge.get("from") == "capture-knowledge"
        }
        self.assertTrue(
            {
                "prompt-compile",
                "lyrics-write",
                "sound-design",
                "diagnose-defects",
                "plan-revision",
                "final-qc",
                "paused",
                "done",
            }
            <= capture_targets
        )

    def test_capture_outranks_verdicts_and_revision_loop(self) -> None:
        rules = {
            rule["when"]: int(rule["priority"])
            for rule in load_pack(PIPELINE, ROOT)["dispatch"]["rules"]
        }
        capture = rules["decision_capture_pending"]
        for name in VERDICT_RULES:
            self.assertLess(capture, rules[name], name)
        self.assertLess(rules["compare_needed"], rules["defect_open"])
        self.assertLess(rules["revision_plan_ready"], rules["defect_open"])
        self.assertLess(rules["comparison_accepted_clear"], rules["revision_budget_exhausted"])

    def test_compiled_schema_marks_human_gates(self) -> None:
        asked = {
            node["id"]
            for node in load_pipeline_schema(PIPELINE).get("nodes") or []
            if node.get("ask")
        }
        self.assertEqual(asked, ASK)

    def test_golden_cases(self) -> None:
        path = ROOT / "scripts" / "fixtures" / "dispatch_golden" / PIPELINE / "cases.json"
        cases = json.loads(path.read_text(encoding="utf-8"))
        ids = {case["id"] for case in cases}
        self.assertTrue(REQUIRED_CASES <= ids)
        for case in cases:
            ok, detail = run_case(case)
            self.assertTrue(ok, f"{case['id']}: {detail}")

    def test_revision_loop_does_not_return_before_compare(self) -> None:
        slug = "music-loop"
        run = Path("Music-runs") / slug
        brief = {
            "schema_version": "1.0",
            "track_id": slug,
            "created_at": "2026-09-28T12:00:00Z",
            "assignment": "fixture",
            "package_review_required": True,
            "reference_use_permitted": False,
            "budget": {
                "max_batch": 2,
                "max_defect_fix_attempts": 3,
                "max_iterations": 5,
                "max_api_wait_seconds": 120,
                "max_cost": 0,
            },
        }
        track = {
            "schema_version": "1.0",
            "track_id": slug,
            "created_at": "2026-09-28T14:00:00Z",
            "state": "REVISING",
            "current_version_id": "ver-001",
            "base_version_id": "ver-001",
            "revision_iteration": 0,
            "revision_budget_remaining": 3,
            "open_critical_defects": 1,
            "open_major_defects": 0,
        }
        signals = {
            "lyrics_verdict": "PASS",
            "package_verdict": "PASS",
            "revision_target": "",
            "comparison_outcome": "",
            "qc_result": "",
            "candidate_reviewed": False,
            "edit_done": False,
            "defect_fix_attempts": 0,
            "required_operation": "",
            "available_operations": ["generate-batch"],
            "comparisons_without_improvement": 0,
        }
        tmp = Path(tempfile.mkdtemp(prefix="music-loop-"))
        try:
            folder = tmp / run
            folder.mkdir(parents=True)
            (folder / "brief.json").write_text(json.dumps(brief), encoding="utf-8")
            (folder / "track-state.json").write_text(json.dumps(track), encoding="utf-8")
            for name in ("lyrics.json", "sound-direction.json", "song-package.json", "generation-request.json"):
                (folder / name).write_text("{}\n", encoding="utf-8")
            (folder / "routing-signals.json").write_text(json.dumps(signals), encoding="utf-8")

            first = build_dispatch(tmp, slug, PIPELINE)
            self.assertEqual(first["next_step"], "plan-revision", first.get("next_reason"))

            (folder / "revision-plan.json").write_text("{}\n", encoding="utf-8")
            second = build_dispatch(tmp, slug, PIPELINE)
            self.assertEqual(second["next_step"], "execute-edit", second.get("next_reason"))
            self.assertNotEqual(second["next_step"], "plan-revision")

            signals["edit_done"] = True
            (folder / "routing-signals.json").write_text(json.dumps(signals), encoding="utf-8")
            third = build_dispatch(tmp, slug, PIPELINE)
            self.assertEqual(third["next_step"], "compare-versions", third.get("next_reason"))
            self.assertNotEqual(third["next_step"], "plan-revision")
            self.assertNotIn("Открыт блокирующий дефект", third.get("next_reason") or "")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

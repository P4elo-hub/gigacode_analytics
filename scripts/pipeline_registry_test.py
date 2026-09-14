#!/usr/bin/env python3
"""Per-pipeline registry: scoped mapping, gated hooks, compile graph checks.

Smoke has a thin check (`pipeline-registry:scoped`). This file is the full suite.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
import warnings
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

from pipeline_active_task import save_active_task  # noqa: E402
from pipeline_before_subagent import validate_task  # noqa: E402
from pipeline_common import (  # noqa: E402
    load_pipeline_registry,
    pipeline_gated_subagents,
    pipeline_step_to_subagent,
    registry_for,
    subagent_for_step,
)
from pipeline_compile import collect_compile_warnings, validate_source  # noqa: E402
from pipeline_pack import build_catalog, merge_compiled_source  # noqa: E402
from pipeline_restart import apply_restart_plan, build_restart_plan  # noqa: E402

CAL_SLUG = "cal-registry-hook"


def _decision(payload: dict) -> str:
    return payload["hookSpecificOutput"]["permissionDecision"]


def _reason(payload: dict) -> str:
    return payload["hookSpecificOutput"]["permissionDecisionReason"]


class RegistryScopeTest(unittest.TestCase):
    def test_calibration_mapping_differs_from_spec(self) -> None:
        spec_map = pipeline_step_to_subagent("spec")
        cal_map = pipeline_step_to_subagent("calibration")
        self.assertNotEqual(spec_map, cal_map)
        self.assertEqual(registry_for("calibration")["step_to_subagent"], cal_map)
        self.assertIn("find-context", spec_map)
        self.assertNotIn("find-context", cal_map)

    def test_calibration_step_not_resolved_via_spec(self) -> None:
        self.assertEqual(subagent_for_step("capture-review", "spec"), "")
        self.assertEqual(subagent_for_step("capture-review", "calibration"), "review-capturer")
        self.assertEqual(subagent_for_step("find-context", "calibration"), "")
        self.assertEqual(subagent_for_step("find-context", "spec"), "context-researcher")

    def test_gated_is_per_pipeline_not_union(self) -> None:
        spec_gated = pipeline_gated_subagents("spec")
        cal_gated = pipeline_gated_subagents("calibration")
        self.assertEqual(pipeline_gated_subagents(), spec_gated)
        self.assertNotIn("review-capturer", spec_gated)
        self.assertIn("review-capturer", cal_gated)
        self.assertIn("gap-resolver", spec_gated)
        self.assertNotIn("gap-resolver", cal_gated)

    def test_no_top_level_mapping_copy(self) -> None:
        data = load_pipeline_registry()
        for field in (
            "step_to_subagent",
            "orchestrator_owned",
            "gated_subagents",
            "restartable_steps",
            "step_order",
        ):
            self.assertNotIn(field, data, field)
        spec = data["pipelines"]["spec"]["step_to_subagent"]
        self.assertNotEqual(data["pipelines"]["calibration"]["step_to_subagent"], spec)

    def test_legacy_export_warns(self) -> None:
        import pipeline_common as common

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", DeprecationWarning)
            mapping = common.STEP_TO_SUBAGENT
        self.assertTrue(any(issubclass(item.category, DeprecationWarning) for item in caught))
        self.assertEqual(mapping, pipeline_step_to_subagent("spec"))


class AgentCatalogTest(unittest.TestCase):
    def test_catalog_sees_three_cli_agent_dirs(self) -> None:
        catalog = build_catalog(ROOT)
        for cli in (".qwen", ".gigacode", ".opencode"):
            self.assertTrue((ROOT / cli / "agents" / "review-capturer.md").is_file(), cli)
            self.assertTrue((ROOT / cli / "agents" / "gap-resolver.md").is_file(), cli)
        agents = set(catalog["agents"])
        self.assertIn("review-capturer", agents)
        self.assertIn("gap-resolver", agents)
        self.assertIn("spec-writer", agents)


class CompileRegistryTest(unittest.TestCase):
    def test_real_packs_validate(self) -> None:
        errors = validate_source(merge_compiled_source(ROOT))
        registry_errors = [item for item in errors if "registry" in item or "subagent" in item]
        self.assertEqual(registry_errors, [])
        self.assertEqual(collect_compile_warnings(merge_compiled_source(ROOT)), [])

    def test_mapped_step_must_be_graph_node(self) -> None:
        data = merge_compiled_source(ROOT)
        data["registries"]["spec"] = dict(data["registries"]["spec"])
        step_map = dict(data["registries"]["spec"]["step_to_subagent"])
        step_map["not-a-node"] = "gap-resolver"
        data["registries"]["spec"]["step_to_subagent"] = step_map
        errors = validate_source(data)
        self.assertTrue(any("not-a-node" in item and "not in graph nodes" in item for item in errors))

    def test_cross_pipeline_mapping_warns(self) -> None:
        warnings_list = collect_compile_warnings(
            {
                "registries": {
                    "spec": {"step_to_subagent": {"shared-step": "spec-reviewer"}},
                    "calibration": {"step_to_subagent": {"shared-step": "review-capturer"}},
                }
            }
        )
        self.assertEqual(len(warnings_list), 1)
        self.assertTrue(warnings_list[0].startswith("warn:"))
        self.assertIn("shared-step", warnings_list[0])


class HookGatedIsolationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="registry-hook-"))
        feature = self.tmp / "Feature-writing" / CAL_SLUG
        feature.mkdir(parents=True)
        (feature / f"{CAL_SLUG}.md").write_text("# hook isolation\n", encoding="utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_snapshot_ok(self) -> None:
        run_dir = self.tmp / "agent-logs" / CAL_SLUG / "runs" / "run-001"
        run_dir.mkdir(parents=True)
        manifest = {"slug": CAL_SLUG, "runs": ["run-001"], "current_run": "run-001"}
        (self.tmp / "agent-logs" / CAL_SLUG / "manifest.json").write_text(
            json.dumps(manifest) + "\n", encoding="utf-8"
        )
        row = {
            "ts": "2026-01-01T00:00:00Z",
            "step": "snapshot-baseline",
            "subagent": "",
            "result": "ok",
        }
        (run_dir / "run-log.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")

    def test_review_capturer_not_gated_on_spec(self) -> None:
        payload = validate_task(self.tmp, "review-capturer", pipeline_arg="spec")
        self.assertEqual(_decision(payload), "allow")
        self.assertIn("не требует pipeline delegate", _reason(payload))

    def test_review_capturer_gated_on_calibration_active_task(self) -> None:
        self._write_snapshot_ok()
        save_active_task(
            self.tmp,
            slug=CAL_SLUG,
            step="capture-review",
            subagent="review-capturer",
            pipeline="calibration",
        )
        allow = validate_task(
            self.tmp,
            "review-capturer",
            slug_hint=CAL_SLUG,
            pipeline_arg="calibration",
        )
        deny = validate_task(
            self.tmp,
            "regression-analyst",
            slug_hint=CAL_SLUG,
            pipeline_arg="calibration",
        )
        self.assertEqual(_decision(allow), "allow", _reason(allow))
        self.assertEqual(_decision(deny), "deny", _reason(deny))
        self.assertNotIn("не требует pipeline delegate", _reason(allow))
        self.assertNotIn("не требует pipeline delegate", _reason(deny))


class CalibrationRestartTest(unittest.TestCase):
    SLUG = "cal-restart-plan"

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="cal-restart-"))
        fw = self.tmp / "Feature-writing" / self.SLUG
        fw.mkdir(parents=True)
        (fw / f"{self.SLUG}.md").write_text("# spec stays\n", encoding="utf-8")
        run = self.tmp / "Calibration" / self.SLUG / "runs" / "run-001"
        for name in ("baseline", "gold", "review", "proposals", "rerun"):
            (run / name).mkdir(parents=True)
        (run / "baseline" / "keep.txt").write_text("baseline\n", encoding="utf-8")
        (run / "gold" / f"{self.SLUG}.md").write_text("# gold\n", encoding="utf-8")
        (run / "review" / "human-review.md").write_text("# review\n", encoding="utf-8")
        (run / "review" / "delta-analysis.md").write_text("# delta\n", encoding="utf-8")
        (run / "proposals" / "proposals.md").write_text("# p\n", encoding="utf-8")
        (run / "scorecard.json").write_text("{}\n", encoding="utf-8")
        (run / "inputs.lock.json").write_text("{}\n", encoding="utf-8")
        manifest = {"slug": self.SLUG, "runs": ["run-001"], "current_run": "run-001"}
        (self.tmp / "Calibration" / self.SLUG / "manifest.json").write_text(
            json.dumps(manifest) + "\n", encoding="utf-8"
        )
        agent = self.tmp / "agent-logs" / self.SLUG / "runs" / "run-001"
        agent.mkdir(parents=True)
        (agent / "events.jsonl").write_text("{}\n", encoding="utf-8")
        (agent / "telemetry-analysis.md").write_text("# tel\n", encoding="utf-8")
        (self.tmp / "agent-logs" / self.SLUG / "manifest.json").write_text(
            json.dumps(manifest) + "\n", encoding="utf-8"
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_spec_step_not_restartable_on_calibration(self) -> None:
        with self.assertRaises(ValueError):
            build_restart_plan(self.tmp, self.SLUG, "find-context", pipeline_id="calibration")

    def test_capture_review_keeps_baseline_drops_gold(self) -> None:
        plan = build_restart_plan(
            self.tmp, self.SLUG, "capture-review", pipeline_id="calibration"
        )
        self.assertEqual(plan.pipeline_id, "calibration")
        self.assertEqual(plan.next_subagent, "review-capturer")
        rels = set(plan.remove_paths)
        keeps = set(plan.keep_paths)
        self.assertTrue(any("/gold" in p or p.endswith("/gold") for p in rels), rels)
        self.assertTrue(any("baseline" in p for p in keeps), keeps)
        self.assertTrue(any(p.endswith("inputs.lock.json") for p in keeps), keeps)
        self.assertFalse(any(p.startswith("Feature-writing") for p in rels), rels)
        self.assertTrue(plan.marker_path.startswith("Calibration/"))

    def test_analyze_telemetry_only_drops_analysis_md(self) -> None:
        plan = build_restart_plan(
            self.tmp, self.SLUG, "analyze-telemetry", pipeline_id="calibration"
        )
        rels = set(plan.remove_paths)
        self.assertTrue(any(p.endswith("telemetry-analysis.md") for p in rels), rels)
        self.assertFalse(any("events.jsonl" in p for p in rels), rels)
        self.assertFalse(any(p.startswith("Feature-writing") for p in rels), rels)

    def test_spec_restart_does_not_list_calibration(self) -> None:
        plan = build_restart_plan(self.tmp, self.SLUG, "check-feature")
        self.assertEqual(plan.pipeline_id, "spec")
        self.assertFalse(any(p.startswith("Calibration/") for p in plan.remove_paths))

    def test_apply_does_not_touch_spec(self) -> None:
        plan = build_restart_plan(
            self.tmp, self.SLUG, "capture-review", pipeline_id="calibration"
        )
        result = apply_restart_plan(self.tmp, plan)
        self.assertTrue(result["ok"], result)
        spec = self.tmp / "Feature-writing" / self.SLUG / f"{self.SLUG}.md"
        self.assertTrue(spec.is_file())
        gold = self.tmp / "Calibration" / self.SLUG / "runs" / "run-001" / "gold"
        self.assertFalse(gold.exists())
        baseline = self.tmp / "Calibration" / self.SLUG / "runs" / "run-001" / "baseline" / "keep.txt"
        self.assertTrue(baseline.is_file())
        marker = self.tmp / "Calibration" / self.SLUG / ".pipeline-restart.json"
        self.assertTrue(marker.is_file())
        payload = json.loads(marker.read_text(encoding="utf-8"))
        self.assertEqual(payload["pipeline_id"], "calibration")
        events = self.tmp / "agent-logs" / self.SLUG / "runs" / "run-001" / "events.jsonl"
        self.assertTrue(events.is_file())


if __name__ == "__main__":
    unittest.main()

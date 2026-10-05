#!/usr/bin/env python3
"""Registry and hook-gating checks for current runtime packs."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

from pipeline_active_task import save_active_task  # noqa: E402
from pipeline_before_subagent import validate_task  # noqa: E402
from pipeline_common import (  # noqa: E402
    known_pipeline_ids,
    pipeline_gated_subagents,
    pipeline_step_to_subagent,
    registry_for,
    subagent_for_step,
)
from pipeline_compile import collect_compile_warnings, validate_source  # noqa: E402
from pipeline_pack import merge_compiled_source  # noqa: E402

ACTIVE_PIPELINE = "spec-v2"


def _decision(payload: dict) -> str:
    return payload["hookSpecificOutput"]["permissionDecision"]


class RegistryScopeTest(unittest.TestCase):
    def test_active_pack_ids_are_current(self) -> None:
        ids = set(known_pipeline_ids())
        self.assertIn(ACTIVE_PIPELINE, ids)
        self.assertIn("calibration", ids)
        self.assertNotIn("spec", ids)

    def test_mappings_are_scoped_by_pipeline(self) -> None:
        active_map = pipeline_step_to_subagent(ACTIVE_PIPELINE)
        cal_map = pipeline_step_to_subagent("calibration")
        self.assertEqual(registry_for(ACTIVE_PIPELINE)["step_to_subagent"], active_map)
        self.assertNotEqual(active_map, cal_map)
        self.assertEqual(active_map.get("analyze-routing"), "routing-analyzer")
        self.assertEqual(cal_map.get("capture-review"), "review-capturer")

    def test_gated_subagents_are_not_union_of_all_packs(self) -> None:
        active_gated = pipeline_gated_subagents(ACTIVE_PIPELINE)
        cal_gated = pipeline_gated_subagents("calibration")
        self.assertIn("routing-analyzer", active_gated)
        self.assertNotIn("review-capturer", active_gated)
        self.assertIn("review-capturer", cal_gated)
        self.assertEqual(subagent_for_step("capture-review", "calibration"), "review-capturer")
        self.assertEqual(subagent_for_step("capture-review", ACTIVE_PIPELINE), "")


class CompileRegistryTest(unittest.TestCase):
    def test_real_packs_validate(self) -> None:
        data = merge_compiled_source(ROOT)
        errors = validate_source(data)
        registry_errors = [item for item in errors if "registry" in item or "subagent" in item]
        self.assertEqual(registry_errors, [])
        self.assertEqual(collect_compile_warnings(data), [])

    def test_mapped_step_must_be_graph_node(self) -> None:
        data = merge_compiled_source(ROOT)
        data["registries"][ACTIVE_PIPELINE] = dict(data["registries"][ACTIVE_PIPELINE])
        step_map = dict(data["registries"][ACTIVE_PIPELINE]["step_to_subagent"])
        step_map["not-a-node"] = "routing-analyzer"
        data["registries"][ACTIVE_PIPELINE]["step_to_subagent"] = step_map
        errors = validate_source(data)
        self.assertTrue(any("not-a-node" in item and "not in graph nodes" in item for item in errors))


class HookGatedIsolationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="registry-hook-"))
        self.slug = "cal-registry-hook"
        feature = self.tmp / "Feature-writing" / self.slug
        feature.mkdir(parents=True)
        (feature / f"{self.slug}.md").write_text("# hook isolation\n", encoding="utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_snapshot_ok(self) -> None:
        run_dir = self.tmp / "agent-logs" / self.slug / "runs" / "run-001"
        run_dir.mkdir(parents=True)
        manifest = {"slug": self.slug, "runs": ["run-001"], "current_run": "run-001"}
        (self.tmp / "agent-logs" / self.slug / "manifest.json").write_text(
            json.dumps(manifest) + "\n", encoding="utf-8"
        )
        row = {
            "ts": "2026-01-01T00:00:00Z",
            "step": "snapshot-baseline",
            "subagent": "",
            "result": "ok",
        }
        (run_dir / "run-log.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")

    def test_foreign_pack_subagent_is_not_gated_by_active_pack(self) -> None:
        payload = validate_task(self.tmp, "review-capturer", pipeline_arg=ACTIVE_PIPELINE)
        self.assertEqual(_decision(payload), "allow", json.dumps(payload, ensure_ascii=False))

    def test_calibration_subagent_is_gated_when_calibration_selected(self) -> None:
        self._write_snapshot_ok()
        save_active_task(
            self.tmp,
            slug=self.slug,
            step="capture-review",
            subagent="review-capturer",
            pipeline="calibration",
        )
        allow = validate_task(self.tmp, "review-capturer", slug_hint=self.slug, pipeline_arg="calibration")
        deny = validate_task(self.tmp, "regression-analyst", slug_hint=self.slug, pipeline_arg="calibration")
        self.assertEqual(_decision(allow), "allow", json.dumps(allow, ensure_ascii=False))
        self.assertEqual(_decision(deny), "deny", json.dumps(deny, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()

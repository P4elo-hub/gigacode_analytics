#!/usr/bin/env python3
"""Phase 12: routing-state schema, overlay always-on for spec, validate ids."""

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
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

from pipeline_pack import load_pack_module  # noqa: E402
from pipeline_routing_state import (  # noqa: E402
    PIPELINE_POC_ID,
    SCHEMA_VERSION,
    STATUS_OVERLAY_FIELDS,
    apply_routing_state_fields,
    example_payload,
    load_routing_state,
    overlay_collector,
    routing_state_path,
    sync_routing_state_after_step,
    validate_payload,
)


class SchemaOverlayTest(unittest.TestCase):
    def test_example_payload_valid(self) -> None:
        payload = example_payload("demo", open_gaps=["GAP-1"])
        self.assertEqual(validate_payload(payload, slug="demo"), [])
        self.assertEqual(payload["schema_version"], SCHEMA_VERSION)
        self.assertTrue(set(STATUS_OVERLAY_FIELDS) <= set(payload["fields"]))

    def test_router_owned_fields_rejected(self) -> None:
        payload = example_payload("demo")
        payload["fields"]["next_step"] = "resolve-gaps"
        errors = validate_payload(payload, slug="demo")
        self.assertTrue(any("next_step" in item for item in errors))

    def test_overlay_sets_open_gaps_not_next_step(self) -> None:
        status = SimpleNamespace(open_gaps=[], next_step="keep")
        apply_routing_state_fields(status, {"open_gaps": ["GAP-1"], "next_step": "hack"})
        self.assertEqual(status.open_gaps, ["GAP-1"])
        self.assertEqual(status.next_step, "keep")

    def test_overlay_challenges_dict(self) -> None:
        status = SimpleNamespace(challenges=SimpleNamespace(open=0, deferred=0))
        apply_routing_state_fields(status, {"challenges": {"open": 2}})
        self.assertEqual(status.challenges.open, 2)

    def test_load_missing_and_invalid(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="rs-"))
        try:
            path = routing_state_path(tmp, "demo")
            payload, error = load_routing_state(path, slug="demo")
            self.assertIsNone(payload)
            self.assertEqual(error, "missing")
            path.parent.mkdir(parents=True)
            path.write_text("{", encoding="utf-8")
            payload, error = load_routing_state(path, slug="demo")
            self.assertIsNone(payload)
            self.assertIn("invalid JSON", error)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_overlay_collector_marks_invalid(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="rs-"))
        try:
            slug = "demo"
            path = routing_state_path(tmp, slug)
            path.parent.mkdir(parents=True)
            path.write_text("{", encoding="utf-8")
            status = SimpleNamespace()
            overlay_collector(tmp, slug, status, {"routing_state": path})
            self.assertTrue(status.routing_state_invalid)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class SpecCollectorsThinTest(unittest.TestCase):
    def test_spec_collectors_overlay_only(self) -> None:
        collectors = load_pack_module("spec", "collectors")
        self.assertIsNotNone(collectors)
        self.assertEqual(set(collectors.COLLECTORS), {"routing_state"})
        self.assertIn("needs-check-feature", collectors.INVARIANTS)
        graph = (ROOT / "pipelines" / "spec" / "graph.yaml").read_text(encoding="utf-8")
        self.assertIn("\n  - id: analyze-routing\n", graph)
        status = (ROOT / "pipelines" / "spec" / "status.yaml").read_text(encoding="utf-8")
        self.assertIn("collector_mode: routing_state", status)


class SpecOverlayAlwaysOnTest(unittest.TestCase):
    def test_live_overlay_uses_json(self) -> None:
        from feature_status import FeatureStatus
        from pipeline_routing_state import overlay_context
        from pipeline_status import populate_status

        tmp = Path(tempfile.mkdtemp(prefix="rs-gate-"))
        slug = "demo"
        try:
            fw = tmp / "Feature-writing" / slug
            fw.mkdir(parents=True)
            spec = fw / f"{slug}.md"
            spec.write_text("# spec\n\n[GAP-SPEC]\n", encoding="utf-8")
            path = routing_state_path(tmp, slug)
            path.write_text(
                json.dumps(example_payload(slug, open_gaps=["GAP-JSON"])),
                encoding="utf-8",
            )
            newer = time.time() + 60
            os.utime(path, (newer, newer))
            status_live = FeatureStatus(slug=slug)
            populate_status(status_live, tmp, slug, "spec")
            self.assertEqual(status_live.open_gaps, ["GAP-JSON"])
            status_off = FeatureStatus(slug=slug)
            with overlay_context(mode="off"):
                populate_status(status_off, tmp, slug, "spec")
            self.assertEqual(status_off.open_gaps, [])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_live_overlay_keeps_deferred_json_gaps(self) -> None:
        from feature_status import FeatureStatus
        from pipeline_status import populate_status

        tmp = Path(tempfile.mkdtemp(prefix="rs-defer-"))
        slug = "demo"
        try:
            fw = tmp / "Feature-writing" / slug
            fw.mkdir(parents=True)
            (fw / f"{slug}.md").write_text(
                "# spec\n\n[GAP-NFR-06]\n\n| GAP-NFR-06 | Gap | Отложено (D-14) |\n",
                encoding="utf-8",
            )
            path = routing_state_path(tmp, slug)
            path.write_text(
                json.dumps(example_payload(slug, open_gaps=["GAP-NFR-06", "GAP-KEEP"])),
                encoding="utf-8",
            )
            os.utime(path, (time.time() + 60, time.time() + 60))
            status = FeatureStatus(slug=slug)
            populate_status(status, tmp, slug, "spec")
            self.assertEqual(sorted(status.open_gaps), ["GAP-KEEP", "GAP-NFR-06"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_overlay_cannot_hide_existing_spec(self) -> None:
        from feature_status import FeatureStatus
        from pipeline_status import populate_status

        tmp = Path(tempfile.mkdtemp(prefix="rs-has-spec-"))
        slug = "demo"
        try:
            fw = tmp / "Feature-writing" / slug
            fw.mkdir(parents=True)
            (fw / f"{slug}.md").write_text("# spec\n", encoding="utf-8")
            payload = example_payload(slug)
            payload["fields"]["has_spec"] = False
            path = routing_state_path(tmp, slug)
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            os.utime(path, (time.time() + 60, time.time() + 60))
            status = FeatureStatus(slug=slug)
            populate_status(status, tmp, slug, "spec")
            self.assertTrue(status.has_spec)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_overlay_recomputes_relates_from_decisions_not_json(self) -> None:
        from feature_status import FeatureStatus
        from pipeline_status import populate_status

        tmp = Path(tempfile.mkdtemp(prefix="rs-relates-"))
        slug = "demo"
        try:
            fw = tmp / "Feature-writing" / slug
            fw.mkdir(parents=True)
            (tmp / "Feature-context").mkdir(parents=True, exist_ok=True)
            (tmp / "Feature-context" / f"{slug}.md").write_text("# ctx\n", encoding="utf-8")
            (fw / f"{slug}.md").write_text("# spec\n\n[GAP-LEFTOVER]\n", encoding="utf-8")
            (fw / f"{slug}-decisions.md").write_text(
                "# DECISIONS\n\n"
                "| ID | Relates | Prompt | Options | Decision | Status | Date |\n"
                "|----|---------|--------|---------|----------|--------|------|\n"
                "| D-01 | CH-13 | leftover? | A) apply | A | pending-apply | 2026-09-19 |\n",
                encoding="utf-8",
            )
            payload = example_payload(slug, open_gaps=["GAP-LEFTOVER"])
            payload["fields"]["has_context"] = True
            payload["fields"]["has_spec"] = True
            payload["fields"]["has_decisions"] = True
            payload["fields"]["decisions_pending_apply"] = 1
            payload["fields"]["decisions_pending_apply_gaps"] = 1
            payload["fields"]["decisions_pending_apply_challenges"] = 0
            path = routing_state_path(tmp, slug)
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            os.utime(path, (time.time() + 60, time.time() + 60))
            status = FeatureStatus(slug=slug)
            populate_status(status, tmp, slug, "spec")
            self.assertEqual(status.decisions_pending_apply_gaps, 0)
            self.assertEqual(status.decisions_pending_apply_challenges, 1)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class SpecValidateRoutingStateTest(unittest.TestCase):
    def setUp(self) -> None:
        extra = load_pack_module("spec", "validate")
        assert extra is not None
        self.extra = extra

    def _advice(self, root: Path, slug: str) -> list:
        report = SimpleNamespace(advice=[], next_step="")

        def add(_report, *, id, severity, title, detail, fix):
            report.advice.append((id, severity))

        status = SimpleNamespace(
            decisions_pending_apply=0,
            decisions_needs_answer=0,
            has_challenges=False,
            has_alignment=False,
            has_gaps_map=False,
            needs_check_feature=False,
            needs_check_feature_reason="",
            pipeline_id="spec",
        )
        self.extra.extra_advice(root, slug, status, {"orchestrator_mode": "delegate"}, report, add)
        return report.advice

    def test_missing_and_stale_ids_are_block(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="rs-spec-val-"))
        slug = "demo"
        try:
            missing = self._advice(tmp, slug)
            self.assertIn(("routing-state-missing", "block"), missing)
            path = routing_state_path(tmp, slug)
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(example_payload(slug)), encoding="utf-8")
            spec = tmp / "Feature-writing" / slug / f"{slug}.md"
            spec.write_text("# spec\n", encoding="utf-8")
            older = time.time() - 120
            os.utime(path, (older, older))
            stale = self._advice(tmp, slug)
            self.assertIn(("routing-state-stale", "block"), stale)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class PocValidateTest(unittest.TestCase):
    def setUp(self) -> None:
        extra = load_pack_module(PIPELINE_POC_ID, "validate")
        assert extra is not None
        self.extra = extra

    def _advice_ids(self, root: Path, slug: str, stale: list[str]) -> set[str]:
        report = SimpleNamespace(advice=[])

        def add(_report, *, id, severity, title, detail, fix):
            report.advice.append(id)

        status = SimpleNamespace(stale=stale)
        self.extra.extra_advice(root, slug, status, {}, report, add)
        return set(report.advice)

    def test_missing_and_stale_ids(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="rs-val-"))
        slug = "demo"
        try:
            self.assertEqual(self._advice_ids(tmp, slug, []), {"routing-state-missing"})
            path = routing_state_path(tmp, slug)
            path.parent.mkdir(parents=True)
            path.write_text(
                json.dumps(example_payload(slug)),
                encoding="utf-8",
            )
            spec = tmp / "Feature-writing" / slug / f"{slug}.md"
            spec.write_text("# spec\n", encoding="utf-8")
            older = time.time() - 120
            os.utime(path, (older, older))
            self.assertEqual(self._advice_ids(tmp, slug, ["routing_state"]), {"routing-state-stale"})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class SpecDispatchMissingJsonTest(unittest.TestCase):
    def test_empty_slug_goes_to_analyze_routing(self) -> None:
        from pipeline_dispatch import build_dispatch

        tmp = Path(tempfile.mkdtemp(prefix="rs-spec-empty-"))
        slug = "demo"
        try:
            dispatch = build_dispatch(tmp, slug, "spec")
            self.assertEqual(dispatch["next_step"], "analyze-routing")
            self.assertEqual(dispatch["next_subagent"], "routing-analyzer")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_context_without_json_goes_to_analyze_routing(self) -> None:
        from pipeline_dispatch import build_dispatch

        tmp = Path(tempfile.mkdtemp(prefix="rs-spec-ctx-"))
        slug = "demo"
        try:
            ctx = tmp / "Feature-context"
            ctx.mkdir(parents=True)
            (ctx / f"{slug}.md").write_text("# ctx\n\nVerified.\n", encoding="utf-8")
            dispatch = build_dispatch(tmp, slug, "spec")
            self.assertEqual(dispatch["next_step"], "analyze-routing")
            self.assertEqual(dispatch["next_subagent"], "routing-analyzer")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class StepSyncTest(unittest.TestCase):
    """Gate stamp vs mutate → analyzer. Golden twins: spec 26–29."""

    def test_check_feature_step_stamps_json_and_unblocks_dispatch(self) -> None:
        from pipeline_dispatch import build_dispatch

        tmp = Path(tempfile.mkdtemp(prefix="rs-sync-"))
        slug = "demo"
        try:
            ctx = tmp / "Feature-context" / f"{slug}.md"
            ctx.parent.mkdir(parents=True)
            ctx.write_text("# context\n\nVerified.\n", encoding="utf-8")
            fw = tmp / "Feature-writing" / slug
            fw.mkdir(parents=True)
            spec = fw / f"{slug}.md"
            gaps = fw / f"{slug}-gaps-resolved.md"
            spec.write_text("# spec\n\n[GAP-1]\n", encoding="utf-8")
            gaps.write_text("# gaps\n", encoding="utf-8")
            decisions = fw / f"{slug}-decisions.md"
            decisions.write_text(
                "# DECISIONS\n\n| ID | Relates | Prompt | Options | Decision | Status | Date |\n"
                "|----|---------|--------|---------|----------|--------|------|\n"
                "| D-01 | Q-01 | gap | A) one | pick | pending-apply | 2026-09-12 |\n",
                encoding="utf-8",
            )
            spec_at = time.time() - 180
            os.utime(spec, (spec_at, spec_at))
            path = routing_state_path(tmp, slug)
            payload = example_payload(slug, open_gaps=["GAP-1"])
            payload["fields"]["has_decisions"] = True
            payload["fields"]["has_gaps_map"] = True
            payload["fields"]["decisions_pending_apply"] = 1
            payload["fields"]["needs_check_feature"] = True
            payload["fields"]["needs_check_feature_reason"] = "нет check-feature после последней правки SPEC"
            path.write_text(json.dumps(payload), encoding="utf-8")

            self.assertTrue(
                sync_routing_state_after_step(tmp, slug, "check-feature", "ok", pipeline_id="spec")
            )
            stored, _ = load_routing_state(path, slug=slug)
            assert stored is not None
            self.assertFalse(stored["fields"]["needs_check_feature"])
            self.assertEqual(stored["fields"]["needs_check_feature_reason"], "")
            self.assertIn("check-feature", stored.get("step_completion") or {})

            dispatch = build_dispatch(tmp, slug, "spec")
            self.assertEqual(dispatch["next_step"], "resolve-gaps")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_sync_enabled_for_routing_poc_pack(self) -> None:
        from pipeline_routing_state import routing_state_sync_enabled

        self.assertTrue(routing_state_sync_enabled("spec"))
        self.assertTrue(routing_state_sync_enabled("routing-poc"))

    def test_analyze_routing_step_does_not_sync(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="rs-skip-"))
        slug = "demo"
        try:
            path = routing_state_path(tmp, slug)
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(example_payload(slug)), encoding="utf-8")
            before = path.read_text(encoding="utf-8")
            self.assertFalse(
                sync_routing_state_after_step(tmp, slug, "analyze-routing", "ok", pipeline_id="spec")
            )
            self.assertEqual(path.read_text(encoding="utf-8"), before)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_mutating_step_does_not_sync_and_dispatch_goes_to_analyzer(self) -> None:
        from pipeline_dispatch import build_dispatch

        tmp = Path(tempfile.mkdtemp(prefix="rs-mutate-"))
        slug = "demo"
        try:
            ctx = tmp / "Feature-context" / f"{slug}.md"
            ctx.parent.mkdir(parents=True)
            ctx.write_text("# context\n\nVerified.\n", encoding="utf-8")
            fw = tmp / "Feature-writing" / slug
            fw.mkdir(parents=True)
            spec = fw / f"{slug}.md"
            spec.write_text("# spec\n", encoding="utf-8")
            path = routing_state_path(tmp, slug)
            path.write_text(json.dumps(example_payload(slug)), encoding="utf-8")
            older = time.time() - 120
            os.utime(path, (older, older))
            before = path.read_text(encoding="utf-8")
            self.assertFalse(
                sync_routing_state_after_step(tmp, slug, "write-feature", "ok", pipeline_id="spec")
            )
            self.assertEqual(path.read_text(encoding="utf-8"), before)
            dispatch = build_dispatch(tmp, slug, "spec")
            self.assertEqual(dispatch["next_step"], "analyze-routing")
            self.assertEqual(dispatch["next_subagent"], "routing-analyzer")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_check_feature_that_mutated_spec_leaves_json_for_analyzer(self) -> None:
        from pipeline_dispatch import build_dispatch

        tmp = Path(tempfile.mkdtemp(prefix="rs-gate-mutate-"))
        slug = "demo"
        try:
            ctx = tmp / "Feature-context" / f"{slug}.md"
            ctx.parent.mkdir(parents=True)
            ctx.write_text("# context\n\nVerified.\n", encoding="utf-8")
            fw = tmp / "Feature-writing" / slug
            fw.mkdir(parents=True)
            spec = fw / f"{slug}.md"
            spec.write_text("# spec\n", encoding="utf-8")
            path = routing_state_path(tmp, slug)
            path.write_text(json.dumps(example_payload(slug)), encoding="utf-8")
            older = time.time() - 120
            os.utime(path, (older, older))
            self.assertFalse(
                sync_routing_state_after_step(tmp, slug, "check-feature", "ok", pipeline_id="spec")
            )
            dispatch = build_dispatch(tmp, slug, "spec")
            self.assertEqual(dispatch["next_step"], "analyze-routing")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_poc_resolve_gaps_does_not_sync(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="rs-poc-mutate-"))
        slug = "demo"
        try:
            fw = tmp / "Feature-writing" / slug
            fw.mkdir(parents=True)
            spec = fw / f"{slug}.md"
            spec.write_text("# spec\n", encoding="utf-8")
            path = routing_state_path(tmp, slug)
            path.write_text(json.dumps(example_payload(slug)), encoding="utf-8")
            before = path.read_text(encoding="utf-8")
            self.assertFalse(
                sync_routing_state_after_step(
                    tmp, slug, "resolve-gaps", "ok", pipeline_id=PIPELINE_POC_ID
                )
            )
            self.assertEqual(path.read_text(encoding="utf-8"), before)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class PocDispatchTest(unittest.TestCase):
    def test_fake_json_open_gaps_next_step(self) -> None:
        from pipeline_dispatch import build_dispatch
        from pipeline_runtime import known_pipeline_ids

        self.assertIn(PIPELINE_POC_ID, known_pipeline_ids())
        tmp = Path(tempfile.mkdtemp(prefix="rs-disp-"))
        slug = "demo"
        try:
            spec = tmp / "Feature-writing" / slug / f"{slug}.md"
            spec.parent.mkdir(parents=True)
            spec.write_text("# spec\n", encoding="utf-8")
            path = routing_state_path(tmp, slug)
            path.write_text(json.dumps(example_payload(slug, open_gaps=["GAP-1"])), encoding="utf-8")
            base = time.time() - 7200
            os.utime(spec, (base, base))
            os.utime(path, (base + 120, base + 120))
            dispatch = build_dispatch(tmp, slug, PIPELINE_POC_ID)
            self.assertEqual(dispatch["next_step"], "resolve-gaps")
            self.assertEqual(dispatch["next_subagent"], "gap-resolver")
            self.assertFalse(dispatch["ready"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

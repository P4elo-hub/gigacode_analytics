#!/usr/bin/env python3
"""Phase 10: routing-state schema, overlay collector, POC validate ids."""

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
    validate_payload,
)

SPEC_COLLECTORS = (
    "decisions_table",
    "spec_gaps",
    "context_questions",
    "challenges_table",
    "alignment_frontmatter",
    "needs_check_feature",
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


class SpecCollectorsUntouchedTest(unittest.TestCase):
    def test_spec_collectors_still_registered(self) -> None:
        collectors = load_pack_module("spec", "collectors")
        self.assertIsNotNone(collectors)
        keys = set(collectors.COLLECTORS)
        self.assertTrue(set(SPEC_COLLECTORS) <= keys)
        spec_src = (ROOT / "pipelines" / "spec" / "collectors.py").read_text(encoding="utf-8")
        self.assertNotIn("overlay_collector", spec_src)
        graph = (ROOT / "pipelines" / "spec" / "graph.yaml").read_text(encoding="utf-8")
        self.assertNotIn("analyze-routing", graph)


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

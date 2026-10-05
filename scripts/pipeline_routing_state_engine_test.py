#!/usr/bin/env python3
"""Routing-state payload primitives shared by routing-state packs."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from pipeline_routing_state import (  # noqa: E402
    SCHEMA_VERSION,
    STATUS_OVERLAY_FIELDS,
    apply_routing_state_fields,
    example_payload,
    load_routing_state,
    overlay_collector,
    routing_state_path,
    validate_payload,
)


class RoutingStatePayloadTest(unittest.TestCase):
    def test_example_payload_valid(self) -> None:
        payload = example_payload("demo", open_gaps=["GAP-1"])
        self.assertEqual(validate_payload(payload, slug="demo"), [])
        self.assertEqual(payload["schema_version"], SCHEMA_VERSION)
        self.assertTrue(set(STATUS_OVERLAY_FIELDS) <= set(payload["fields"]))

    def test_router_owned_fields_rejected(self) -> None:
        payload = example_payload("demo")
        payload["fields"]["next_step"] = "resolve-gaps"
        errors = validate_payload(payload, slug="demo")
        self.assertTrue(any("next_step" in item for item in errors), errors)

    def test_overlay_sets_domain_fields_but_not_router_fields(self) -> None:
        status = SimpleNamespace(open_gaps=[], next_step="keep")
        apply_routing_state_fields(status, {"open_gaps": ["GAP-1"], "next_step": "hack"})
        self.assertEqual(status.open_gaps, ["GAP-1"])
        self.assertEqual(status.next_step, "keep")

    def test_load_missing_and_invalid_json(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="rs-engine-"))
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

    def test_overlay_collector_marks_invalid_payload(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="rs-engine-"))
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

    def test_payload_roundtrip_from_disk(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="rs-engine-"))
        try:
            slug = "demo"
            path = routing_state_path(tmp, slug)
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(example_payload(slug), ensure_ascii=False), encoding="utf-8")
            payload, error = load_routing_state(path, slug=slug)
            self.assertEqual(error, "")
            self.assertIsNotNone(payload)
            self.assertEqual(payload["slug"], slug)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

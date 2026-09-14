#!/usr/bin/env python3
"""Predicate catalog: core/domain names, reasons, compile typo, golden stubs.

Not part of pipeline_smoke_test.py (full catalog suite; smoke stays 31/31).
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

from pipeline_compile import validate_dispatch, validate_source  # noqa: E402
from pipeline_pack import load_pack, load_pack_module, merge_compiled_source  # noqa: E402
from pipeline_predicates import (  # noqa: E402
    catalog_names,
    core_predicate_names,
    predicates_for,
    reason_for,
    validate_catalog,
)

GOLDEN = SCRIPTS / "fixtures" / "predicate_golden" / "spec" / "cases.json"
SPEC_NODES = {
    "find-context",
    "write-feature",
    "analyze-routing",
    "check-feature",
    "resolve-gaps",
    "challenge-feature",
    "resolve-challenges",
    "check-feature-code",
    "resolve-code-alignment",
}
SPEC_RESTART = list(SPEC_NODES)


def _dispatch_when_names(pipeline_id: str) -> list[str]:
    rules = (load_pack(pipeline_id).get("dispatch") or {}).get("rules") or []
    return [str(rule["when"]) for rule in rules if isinstance(rule, dict) and rule.get("when")]


def _stub_status(fields: dict) -> SimpleNamespace:
    base = {
        "has_context": False,
        "has_spec": False,
        "has_alignment": False,
        "has_challenges": False,
        "open_gaps": [],
        "stale": [],
        "verdict": "",
        "alignment_iteration": 0,
        "alignment_stale": False,
        "critical_major_mismatch": 0,
        "decisions_needs_answer": 0,
        "decisions_needs_answer_alignment": 0,
        "decisions_pending_apply": 0,
        "decisions_pending_apply_alignment": 0,
        "challenges": SimpleNamespace(open=0),
    }
    base.update(fields)
    return SimpleNamespace(**base)


class SpecCatalogTest(unittest.TestCase):
    def test_dispatch_when_in_catalog(self) -> None:
        catalog = catalog_names("spec")
        missing = [name for name in _dispatch_when_names("spec") if name not in catalog]
        self.assertEqual(missing, [], f"dispatch when not in catalog: {missing}")

    def test_domain_names_match_predicates(self) -> None:
        domain = load_pack_module("spec", "predicates")
        self.assertIsNotNone(domain)
        declared = set(domain.DOMAIN_PREDICATE_NAMES)
        impl = set(domain.PREDICATES)
        self.assertEqual(declared, impl)

    def test_domain_predicates_callable_with_reason(self) -> None:
        domain = load_pack_module("spec", "predicates")
        stub = _stub_status({})
        for name, fn in domain.PREDICATES.items():
            self.assertTrue(callable(fn), name)
            text = domain.reason_for_predicate(name, stub)
            self.assertTrue(str(text).strip(), f"empty reason for {name}")

    def test_constants_from_status_yaml(self) -> None:
        src = (ROOT / "pipelines" / "spec" / "predicates.py").read_text(encoding="utf-8")
        self.assertNotIn("artifact_paths", src)
        const = load_pack("spec")["status"]["constants"]
        self.assertEqual(int(const["alignment_max_iterations"]), 3)
        self.assertEqual(const["verdict_fail"], "FAIL")
        domain = load_pack_module("spec", "predicates")
        stub = _stub_status(
            {
                "has_alignment": True,
                "alignment_iteration": int(const["alignment_max_iterations"]),
                "verdict": const["verdict_fail"],
            }
        )
        self.assertTrue(domain.PREDICATES["alignment_limit_exhausted"](Path("."), "x", stub))

    def test_core_counters_and_artifact_reasons(self) -> None:
        names = core_predicate_names("spec")
        self.assertIn("not_has_context", names)
        self.assertIn("decisions_needs_answer_gt_0", names)
        self.assertIn("decisions_pending_apply_gt_0", names)
        self.assertNotIn("file_missing", names)
        text = reason_for("not_has_context", _stub_status({}), "spec")
        self.assertEqual(text, "нет проверенного контекста")
        router_src = (SCRIPTS / "pipeline_router.py").read_text(encoding="utf-8")
        for name in _dispatch_when_names("spec"):
            self.assertNotIn(name, router_src, name)

    def test_unknown_when_fails_compile(self) -> None:
        errors = validate_dispatch(
            "spec",
            {"rules": [{"when": "typo_open_gaps", "priority": 1, "next": "resolve-gaps"}]},
            SPEC_RESTART,
            SPEC_NODES,
        )
        self.assertTrue(any("unknown when" in item and "typo_open_gaps" in item for item in errors))

    def test_validate_source_spec_catalog_ok(self) -> None:
        errors = validate_source(merge_compiled_source(ROOT))
        catalog_errors = [item for item in errors if "predicate" in item.lower() or "reason_for" in item]
        self.assertEqual(catalog_errors, [])
        self.assertEqual(validate_catalog("spec", load_pack("spec")["dispatch"]), [])


class PredicateGoldenTest(unittest.TestCase):
    def test_status_stub_cases(self) -> None:
        payload = json.loads(GOLDEN.read_text(encoding="utf-8"))
        preds = predicates_for(payload["pipeline_id"])
        for case in payload["cases"]:
            with self.subTest(case["id"]):
                fn = preds[case["when"]]
                status = _stub_status(case.get("status") or {})
                self.assertEqual(fn(Path("."), "stub", status), case["expect"], case["id"])


if __name__ == "__main__":
    unittest.main()

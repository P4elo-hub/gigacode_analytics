#!/usr/bin/env python3
"""Session 2: Apply/codegen universality — synthetic pack, not analytics/spec-v2."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
VIEWER = ROOT / "pipeline-viewer"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(VIEWER))

from pack_authoring_api import (  # noqa: E402
    assemble_pack_payload,
    apply_assembled,
    collectors_is_generic_overlay,
    invent_condition_id,
    merge_routing_state_status,
    overlay_collectors_text,
    stub_graph_whens,
    validate_assembled,
)
from pipeline_edge_conditions import (  # noqa: E402
    dispatch_rules_from_edge_conditions,
    evaluate_edge_condition,
)
from pipeline_pack import load_yaml  # noqa: E402
from pipeline_pack_authoring import ROUTING_STATE_COLLECTORS, init_pack  # noqa: E402
from pipeline_compile import merge_compiled_source, validate_source  # noqa: E402

ALPHA_TEXT = "нужен шаг альфа"
BETA_TEXT = "нужен шаг бета"
PACK_ID = "codegen-smoke"


def _stub_agents(root: Path, *names: str) -> None:
    """Non-empty agent catalog enables compile checks; stub mapped subagents."""
    for cli in (".qwen", ".gigacode", ".opencode"):
        folder = root / cli / "agents"
        folder.mkdir(parents=True, exist_ok=True)
        for name in names:
            path = folder / f"{name}.md"
            if not path.is_file():
                path.write_text(f"---\nname: {name}\n---\n# {name}\n", encoding="utf-8")


def _smoke_graph(orch: str) -> dict:
    return {
        "label": "codegen-smoke",
        "orchestrator": orch,
        "nodes": [
            {"id": orch, "label": orch, "kind": "orchestrator"},
            {
                "id": "analyze-routing",
                "label": "analyze-routing",
                "subagent": "routing-analyzer",
                "kind": "analyzer",
            },
            {"id": "step-alpha", "label": "step-alpha", "subagent": None, "kind": "step"},
            {"id": "step-beta", "label": "step-beta", "subagent": None, "kind": "step"},
            {"id": "done", "label": "done", "kind": "terminal"},
        ],
        "edges": [
            {
                "id": "e-orch-ar",
                "from": orch,
                "to": "analyze-routing",
                "kind": "branch",
                "label": "routing-state missing/stale",
                "condition": "routing_state_needs_refresh",
                "condition_label": "routing-state missing/stale",
            },
            {
                "id": "e-alpha",
                "from": "analyze-routing",
                "to": "step-alpha",
                "kind": "branch",
                "condition_label": ALPHA_TEXT,
            },
            {
                "id": "e-beta",
                "from": "analyze-routing",
                "to": "step-beta",
                "kind": "branch",
                "condition_label": BETA_TEXT,
            },
            {
                "id": "e-alpha-done",
                "from": "step-alpha",
                "to": "done",
                "kind": "main",
            },
            {
                "id": "e-beta-done",
                "from": "step-beta",
                "to": "done",
                "kind": "main",
            },
        ],
    }


def _pick_next(conditions: dict, field_values: dict) -> object:
    """Highest-priority edge_condition whose expr is true (dispatch semantics)."""
    status = SimpleNamespace(
        has_routing_state=True,
        routing_state_invalid=False,
        routing_state_error="",
        stale=[],
        has_main=True,
        **field_values,
    )
    rules = dispatch_rules_from_edge_conditions(conditions)
    for rule in rules:
        when = str(rule.get("when") or "")
        spec = conditions.get(when) or {}
        expr = spec.get("expr")
        if expr is None:
            continue
        if evaluate_edge_condition(expr, status, conditions=conditions):
            if rule.get("outcome"):
                return rule.get("outcome")
            return rule.get("next")
    return None


class CodegenSmokeUniversalityTest(unittest.TestCase):
    def test_free_text_bool_when_triple_and_overlay_collectors(self) -> None:
        alpha_id = invent_condition_id(ALPHA_TEXT, set())
        beta_id = invent_condition_id(BETA_TEXT, set())
        self.assertEqual(alpha_id, "has_nuzhen_shag_alfa")
        self.assertEqual(beta_id, "has_nuzhen_shag_beta")

        with tempfile.TemporaryDirectory(prefix="codegen-smoke-") as tmp:
            root = Path(tmp)
            init_pack(PACK_ID, "routing-state", root)
            status = load_yaml(root / "pipelines" / PACK_ID / "status.yaml")
            self.assertEqual(
                ((status.get("artifacts") or {}).get("routing_state") or {}).get("path"),
                "{task_id}/routing-state.json",
            )
            rc_stub = load_yaml(root / "pipelines" / PACK_ID / "routing_conditions.yaml")
            self.assertEqual(
                ((status.get("artifacts") or {}).get("routing_reports") or {}).get("path"),
                "{task_id}/.pipeline/routing-reports/index.json",
            )
            self.assertEqual(rc_stub.get("stale_vs"), ["main", "routing_reports"])
            self.assertNotIn("spec", rc_stub.get("stale_vs") or [])
            _stub_agents(root, "routing-analyzer")
            orch = f"{PACK_ID}-orchestrator"
            body = {"id": PACK_ID, "graph": _smoke_graph(orch)}

            with patch("pipeline_pack.repo_root", return_value=root):
                assembled, overlay_errors, notes = assemble_pack_payload(body, root)
                self.assertEqual(overlay_errors, [], overlay_errors)
                checked = validate_assembled(assembled, root, overlay_errors)
                self.assertTrue(checked["ok"], checked.get("errors"))

                schema_path = root / "scripts" / "pipeline_schema.json"
                registry_path = root / "scripts" / "generated" / "pipeline_registry.json"
                registry_path.parent.mkdir(parents=True, exist_ok=True)
                with patch("pack_authoring_api.SCHEMA_PATH", schema_path):
                    with patch("pack_authoring_api.REGISTRY_PATH", registry_path):
                        applied = apply_assembled(assembled, root)

            collectors = (root / "pipelines" / PACK_ID / "collectors.py").read_text(encoding="utf-8")
            self.assertEqual(collectors, overlay_collectors_text())
            self.assertEqual(collectors, ROUTING_STATE_COLLECTORS)
            self.assertTrue(collectors_is_generic_overlay(collectors))
            self.assertNotIn("GAP", collectors)
            self.assertNotIn("open_gaps", collectors)

            predicates = root / "pipelines" / PACK_ID / "predicates.py"
            self.assertFalse(predicates.exists())

            rc = load_yaml(root / "pipelines" / PACK_ID / "routing_conditions.yaml")
            fields = rc.get("status_fields") or {}
            conditions = rc.get("edge_conditions") or {}
            dispatch = load_yaml(root / "pipelines" / PACK_ID / "dispatch.yaml")
            when_ids = {str(rule.get("when")) for rule in (dispatch.get("rules") or []) if rule.get("when")}

            for wid in (alpha_id, beta_id):
                self.assertIn(wid, fields, f"missing status_fields.{wid}")
                self.assertIn(wid, conditions, f"missing edge_conditions.{wid}")
                self.assertIn(wid, when_ids, f"missing dispatch when:{wid}")
                self.assertEqual(
                    (conditions[wid].get("expr") or {}).get("op"),
                    "truthy",
                    wid,
                )
                self.assertTrue(str((fields[wid] or {}).get("instruction") or "").strip(), wid)

            self.assertEqual(_pick_next(conditions, {alpha_id: True, beta_id: False}), "step-alpha")
            self.assertEqual(_pick_next(conditions, {alpha_id: False, beta_id: True}), "step-beta")
            both_false = _pick_next(conditions, {alpha_id: False, beta_id: False})
            self.assertNotIn(both_false, {"step-alpha", "step-beta"}, both_false)

            # Compile layer on temp pack (agents catalog from real workspace is OK).
            with patch("pipeline_pack.repo_root", return_value=root):
                errors = validate_source(merge_compiled_source(root))
            self.assertEqual(errors, [], errors)

            # Applied notes mention overlay runtime.
            joined = " ".join(applied.get("notes") or []) + " " + " ".join(notes)
            self.assertTrue("collectors" in joined or collectors)

    def test_ui_dispatch_priority_and_delete_persist(self) -> None:
        alpha_id = invent_condition_id(ALPHA_TEXT, set())
        beta_id = invent_condition_id(BETA_TEXT, set())
        with tempfile.TemporaryDirectory(prefix="dispatch-ui-") as tmp:
            root = Path(tmp)
            init_pack(PACK_ID, "routing-state", root)
            _stub_agents(root, "routing-analyzer")
            orch = f"{PACK_ID}-orchestrator"
            body = {"id": PACK_ID, "graph": _smoke_graph(orch)}

            with patch("pipeline_pack.repo_root", return_value=root):
                assembled, overlay_errors, _ = assemble_pack_payload(body, root)
                self.assertEqual(overlay_errors, [], overlay_errors)
                self.assertTrue(validate_assembled(assembled, root, overlay_errors)["ok"])

                rules = list((assembled.get("dispatch") or {}).get("rules") or [])
                by_when = {str(r.get("when")): dict(r) for r in rules}
                self.assertIn(alpha_id, by_when)
                self.assertIn(beta_id, by_when)
                # Swap priorities + drop beta from the table.
                by_when[alpha_id]["priority"] = 999
                del by_when[beta_id]
                body2 = {
                    "id": PACK_ID,
                    "graph": assembled["graph"],
                    "dispatch": {"rules": list(by_when.values())},
                }
                assembled2, errs2, notes2 = assemble_pack_payload(body2, root)
                self.assertEqual(errs2, [], errs2)
                self.assertTrue(validate_assembled(assembled2, root, errs2)["ok"])

            rules2 = {
                str(r.get("when")): r
                for r in (assembled2.get("dispatch") or {}).get("rules") or []
            }
            self.assertIn(alpha_id, rules2)
            self.assertEqual(int(rules2[alpha_id]["priority"]), 999)
            self.assertNotIn(beta_id, rules2)

            rc = assembled2.get("routing_conditions") or {}
            conditions = rc.get("edge_conditions") or {}
            self.assertEqual(
                int((conditions[alpha_id].get("dispatch") or {}).get("priority")),
                999,
            )
            self.assertNotIn(beta_id, conditions)
            edge_ids = []
            for edge in (assembled2.get("graph") or {}).get("edges") or []:
                if edge.get("condition"):
                    edge_ids.append(edge["condition"])
                for item in edge.get("conditions") or []:
                    edge_ids.append(item if isinstance(item, str) else (item or {}).get("id"))
            self.assertNotIn(beta_id, edge_ids)
            self.assertTrue(any("999" in n or "таблица" in n or "удал" in n for n in notes2), notes2)

    def test_changed_arrow_text_rewrites_routing_condition(self) -> None:
        cond = "has_alpha"
        old = "нужен шаг альфа"
        new = "нужен шаг альфа (исключение — не повторять шаг)"
        payload = {
            "graph": {
                "nodes": [],
                "edges": [
                    {
                        "id": "e-alpha",
                        "from": "analyze-routing",
                        "to": "step-alpha",
                        "condition": cond,
                        "condition_label": new,
                    }
                ],
            },
            "routing_conditions": {
                "status_fields": {cond: {"type": "bool", "instruction": old}},
                "edge_conditions": {
                    cond: {
                        "expr": {"field": cond, "op": "truthy"},
                        "dispatch": {"priority": 180, "next": "step-alpha"},
                        "label": old,
                        "reason": old,
                    }
                },
            },
            "dispatch": {"rules": [{"priority": 180, "when": cond, "next": "step-alpha"}]},
        }
        stub_graph_whens(payload)
        spec = payload["routing_conditions"]["edge_conditions"][cond]
        self.assertEqual(spec["label"], new)
        self.assertEqual(spec["reason"], new)
        self.assertEqual(spec["expr"], {"field": cond, "op": "truthy"})
        self.assertEqual(spec["dispatch"], {"priority": 180, "next": "step-alpha"})
        self.assertEqual(payload["routing_conditions"]["status_fields"][cond]["instruction"], new)
        self.assertEqual(payload["dispatch"]["rules"][0]["priority"], 180)

    def test_validate_injects_routing_reports_like_apply(self) -> None:
        payload = {
            "status": {
                "collector_mode": "routing_state",
                "collectors": [{"id": "routing_state", "source": "routing_state"}],
                "artifacts": {
                    "main": {"path": "{task_id}/main.md", "exists_as": "has_main"},
                    "routing_state": {
                        "path": "{task_id}/routing-state.json",
                        "exists_as": "has_routing_state",
                    },
                },
            },
            "routing_conditions": {"stale_vs": ["main"]},
            "graph": {"nodes": [{"id": "analyze-routing"}]},
        }
        notes = merge_routing_state_status(payload)
        artifacts = (payload["status"].get("artifacts") or {})
        self.assertEqual(
            (artifacts.get("routing_reports") or {}).get("path"),
            "{task_id}/.pipeline/routing-reports/index.json",
        )
        self.assertIn(
            {
                "id": "routing_state",
                "when": "artifact_older_than",
                "left": "routing_state",
                "right": "routing_reports",
            },
            payload["status"].get("stale") or [],
        )
        self.assertEqual(payload["routing_conditions"]["stale_vs"], ["main", "routing_reports"])
        self.assertTrue(any("routing_reports" in item for item in notes), notes)


if __name__ == "__main__":
    unittest.main()

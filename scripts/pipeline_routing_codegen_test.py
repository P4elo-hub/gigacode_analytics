#!/usr/bin/env python3
"""Phase 13: PlantUML / graph → routing_conditions codegen."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

from pipeline_edge_conditions import (  # noqa: E402
    dispatch_rules_from_edge_conditions,
    edge_conditions_map,
    evaluate_edge_condition,
)
from pipeline_pack import load_pack, load_yaml  # noqa: E402
from pipeline_routing_codegen import (  # noqa: E402
    apply_plan,
    main as codegen_main,
    parse_plantuml,
    planned_changes,
)

PUML = SCRIPTS / "fixtures" / "routing_codegen" / "spec-sample.puml"
EXPECTED = SCRIPTS / "fixtures" / "routing_codegen" / "expected-edge_conditions.yaml"


def _norm_edge_block(block: dict) -> dict:
    out: dict = {}
    for name, spec in (block or {}).items():
        if not isinstance(spec, dict):
            continue
        item = dict(spec)
        disp = dict(item.get("dispatch") or {})
        if "priority" in disp:
            disp["priority"] = int(disp["priority"])
        if disp.get("next") in {"null", ""}:
            disp["next"] = None
        item["dispatch"] = disp
        out[name] = item
    return out


def _blank_pack(root: Path, pipeline_id: str = "demo-codegen") -> Path:
    folder = root / "pipelines" / pipeline_id
    folder.mkdir(parents=True)
    (folder / "graph.yaml").write_text(
        "\n".join(
            [
                "label: demo",
                "orchestrator: spec-orchestrator",
                "nodes:",
                "  - id: spec-orchestrator",
                "    kind: orchestrator",
                "  - id: find-context",
                "    kind: step",
                "  - id: analyze-routing",
                "    kind: step",
                "  - id: check-feature",
                "    kind: step",
                "  - id: resolve-gaps",
                "    kind: step",
                "  - id: check-feature-code",
                "    kind: step",
                "  - id: done",
                "    kind: terminal",
                "edges:",
                "  - from: spec-orchestrator",
                "    to: find-context",
                "  - from: spec-orchestrator",
                "    to: analyze-routing",
                "  - from: check-feature",
                "    to: resolve-gaps",
                "  - from: check-feature-code",
                "    to: done",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (folder / "dispatch.yaml").write_text("invariants: []\nrules: []\n", encoding="utf-8")
    (folder / "status.yaml").write_text("task_kind: slug\nartifacts: {}\n", encoding="utf-8")
    (folder / "registry.yaml").write_text(
        "step_to_subagent: {}\norchestrator_owned: [find-context]\n"
        "gated_subagents: []\nrestartable_steps: [find-context]\n",
        encoding="utf-8",
    )
    return folder


class PlantumlParseTest(unittest.TestCase):
    def test_sample_has_four_labeled_edges(self) -> None:
        edges = parse_plantuml(PUML.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(edges), 3)
        ids = [edge["condition"] for edge in edges]
        self.assertEqual(
            ids,
            [
                "not_has_context",
                "routing_state_needs_refresh",
                "open_gaps",
                "alignment_pass",
            ],
        )


class CodegenSnapshotTest(unittest.TestCase):
    def test_plantuml_snapshot_and_second_apply_noop(self) -> None:
        expected = load_yaml(EXPECTED).get("edge_conditions") or {}
        with tempfile.TemporaryDirectory(prefix="rt-cg-") as tmp:
            root = Path(tmp)
            _blank_pack(root)
            plan = planned_changes("demo-codegen", root, parse_plantuml(PUML.read_text(encoding="utf-8")))
            self.assertEqual(_norm_edge_block(plan["new_conditions"]), _norm_edge_block(expected))
            notes = apply_plan(plan, write=True)
            self.assertTrue(any(item.startswith("wrote") for item in notes))
            rc = load_yaml(root / "pipelines" / "demo-codegen" / "routing_conditions.yaml")
            self.assertEqual(_norm_edge_block(rc.get("edge_conditions") or {}), _norm_edge_block(expected))
            dispatch = load_yaml(root / "pipelines" / "demo-codegen" / "dispatch.yaml")
            loaded_rules = []
            for rule in dispatch.get("rules") or []:
                item = {
                    "priority": int(rule["priority"]),
                    "when": rule["when"],
                    "next": None if rule.get("next") in {None, "null"} else rule.get("next"),
                }
                if rule.get("outcome"):
                    item["outcome"] = rule["outcome"]
                loaded_rules.append(item)
            self.assertEqual(loaded_rules, plan["rules"])
            rc_text = (root / "pipelines" / "demo-codegen" / "routing_conditions.yaml").read_text(encoding="utf-8")
            disp_text = (root / "pipelines" / "demo-codegen" / "dispatch.yaml").read_text(encoding="utf-8")
            plan2 = planned_changes("demo-codegen", root, parse_plantuml(PUML.read_text(encoding="utf-8")))
            notes2 = apply_plan(plan2, write=True)
            self.assertTrue(all("unchanged" in item or item.startswith("dry-run") for item in notes2))
            self.assertEqual(
                (root / "pipelines" / "demo-codegen" / "routing_conditions.yaml").read_text(encoding="utf-8"),
                rc_text,
            )
            self.assertEqual(
                (root / "pipelines" / "demo-codegen" / "dispatch.yaml").read_text(encoding="utf-8"),
                disp_text,
            )


class SpecIdempotentTest(unittest.TestCase):
    def test_spec_plantuml_apply_noop(self) -> None:
        rc_path = ROOT / "pipelines" / "spec" / "routing_conditions.yaml"
        disp_path = ROOT / "pipelines" / "spec" / "dispatch.yaml"
        rc_before = rc_path.read_text(encoding="utf-8")
        disp_before = disp_path.read_text(encoding="utf-8")
        self.assertEqual(codegen_main(["--pipeline", "spec", "--from-plantuml", str(PUML), "--apply"]), 0)
        self.assertEqual(rc_path.read_text(encoding="utf-8"), rc_before)
        self.assertEqual(disp_path.read_text(encoding="utf-8"), disp_before)
        self.assertEqual(codegen_main(["--pipeline", "spec", "--from-plantuml", str(PUML), "--apply"]), 0)
        self.assertEqual(rc_path.read_text(encoding="utf-8"), rc_before)
        self.assertEqual(disp_path.read_text(encoding="utf-8"), disp_before)

    def test_spec_dispatch_rules_match_edge_conditions(self) -> None:
        pack = load_pack("spec")
        expected = dispatch_rules_from_edge_conditions(edge_conditions_map("spec"))
        actual = []
        for rule in pack["dispatch"]["rules"]:
            item = {"priority": int(rule["priority"]), "when": rule["when"], "next": rule.get("next")}
            if rule.get("outcome"):
                item["outcome"] = rule["outcome"]
            actual.append(item)
        self.assertEqual(expected, actual)


class InterpreterParityTest(unittest.TestCase):
    def test_open_gaps_expr(self) -> None:
        from types import SimpleNamespace

        spec = edge_conditions_map("spec")["open_gaps"]
        self.assertTrue(
            evaluate_edge_condition(spec["expr"], SimpleNamespace(open_gaps=["GAP-1"]))
        )
        self.assertFalse(evaluate_edge_condition(spec["expr"], SimpleNamespace(open_gaps=[])))

    def test_alignment_pass_uses_constants(self) -> None:
        from types import SimpleNamespace

        spec = edge_conditions_map("spec")["alignment_pass"]
        const = {"verdict_pass": "PASS", "verdict_pass_with_gaps": "PASS WITH GAPS"}
        self.assertTrue(
            evaluate_edge_condition(
                spec["expr"], SimpleNamespace(verdict="PASS WITH GAPS"), constants=const
            )
        )
        self.assertFalse(
            evaluate_edge_condition(spec["expr"], SimpleNamespace(verdict="FAIL"), constants=const)
        )


if __name__ == "__main__":
    unittest.main()

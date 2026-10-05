#!/usr/bin/env python3
"""Pack-local routing codegen checks without mutating live packs."""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
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
from pipeline_routing_codegen import apply_plan, main as codegen_main, parse_plantuml, planned_changes  # noqa: E402

PUML = SCRIPTS / "fixtures" / "routing_codegen" / "spec-sample.puml"
EXPECTED = SCRIPTS / "fixtures" / "routing_codegen" / "expected-edge_conditions.yaml"
ACTIVE_PIPELINE = "spec-v2"


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
                "orchestrator: demo-orchestrator",
                "nodes:",
                "  - id: demo-orchestrator",
                "    kind: orchestrator",
                "  - id: find-context",
                "    kind: step",
                "  - id: analyze-routing",
                "    kind: analyzer",
                "  - id: check-feature",
                "    kind: step",
                "  - id: resolve-gaps",
                "    kind: step",
                "  - id: check-feature-code",
                "    kind: step",
                "  - id: done",
                "    kind: terminal",
                "edges:",
                "  - from: demo-orchestrator",
                "    to: find-context",
                "  - from: demo-orchestrator",
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
    def test_sample_has_expected_condition_ids(self) -> None:
        edges = parse_plantuml(PUML.read_text(encoding="utf-8"))
        self.assertEqual(
            [edge["condition"] for edge in edges],
            ["not_has_context", "routing_state_needs_refresh", "open_gaps", "alignment_pass"],
        )


class CodegenSnapshotTest(unittest.TestCase):
    def test_plantuml_snapshot_and_second_apply_noop_in_temp_pack(self) -> None:
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
            notes2 = apply_plan(planned_changes("demo-codegen", root, parse_plantuml(PUML.read_text())), write=True)
            self.assertTrue(all("unchanged" in item or item.startswith("dry-run") for item in notes2))

    def test_live_pack_codegen_dry_run_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rt-cg-live-") as tmp:
            root = Path(tmp)
            shutil.copytree(ROOT / "pipelines" / ACTIVE_PIPELINE, root / "pipelines" / ACTIVE_PIPELINE)
            rc_path = root / "pipelines" / ACTIVE_PIPELINE / "routing_conditions.yaml"
            dispatch_path = root / "pipelines" / ACTIVE_PIPELINE / "dispatch.yaml"
            before = (rc_path.read_text(encoding="utf-8"), dispatch_path.read_text(encoding="utf-8"))
            with redirect_stdout(StringIO()):
                rc = codegen_main(
                    ["--pipeline", ACTIVE_PIPELINE, "--from-plantuml", str(PUML), "--dry-run", "--root", str(root)]
                )
            self.assertEqual(rc, 0)
            after = (rc_path.read_text(encoding="utf-8"), dispatch_path.read_text(encoding="utf-8"))
            self.assertEqual(after, before)

    def test_dispatch_rules_match_edge_conditions_for_active_pack(self) -> None:
        pack = load_pack(ACTIVE_PIPELINE)
        expected = dispatch_rules_from_edge_conditions(edge_conditions_map(ACTIVE_PIPELINE))
        actual = [
            {
                "priority": int(rule["priority"]),
                "when": rule["when"],
                "next": rule.get("next"),
                **({"outcome": rule["outcome"]} if rule.get("outcome") else {}),
            }
            for rule in pack["dispatch"]["rules"]
        ]
        self.assertEqual(expected, actual)


class InterpreterParityTest(unittest.TestCase):
    def test_edge_condition_exprs_evaluate(self) -> None:
        from types import SimpleNamespace

        open_gaps = edge_conditions_map(ACTIVE_PIPELINE)["has_open_gaps_ne_pustye_posle_revyu_bez_pending_apply"]
        self.assertTrue(
            evaluate_edge_condition(
                open_gaps["expr"],
                SimpleNamespace(has_open_gaps_ne_pustye_posle_revyu_bez_pending_apply=True),
            )
        )
        self.assertFalse(
            evaluate_edge_condition(
                open_gaps["expr"],
                SimpleNamespace(has_open_gaps_ne_pustye_posle_revyu_bez_pending_apply=False),
            )
        )


if __name__ == "__main__":
    unittest.main()

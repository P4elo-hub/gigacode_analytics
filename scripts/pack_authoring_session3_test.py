#!/usr/bin/env python3
"""Session 3: orchestrator md (no silent overwrite) + after_step loops (no bool when:)."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
VIEWER = ROOT / "pipeline-viewer"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(VIEWER))

from pack_authoring_api import (  # noqa: E402
    assemble_pack_payload,
    apply_assembled,
    ensure_orchestrator_md,
    invent_condition_id,
    render_orchestrator_md,
    runnable_checklist,
    validate_assembled,
)
from pipeline_pack import load_yaml  # noqa: E402
from pipeline_pack_authoring import init_pack  # noqa: E402

PACK_ID = "session3-smoke"
ALPHA_TEXT = "нужен шаг альфа"


def _graph(orch: str, *, after_step: bool = True) -> dict:
    loop_edge: dict = {
        "id": "e-alpha-ar",
        "from": "step-alpha",
        "to": "analyze-routing",
        "kind": "loop",
        "label": "после завершения шага",
    }
    if after_step:
        loop_edge["after_step"] = True
    else:
        loop_edge["condition_label"] = "Агент закончил своё выполнение"
    return {
        "label": PACK_ID,
        "orchestrator": orch,
        "nodes": [
            {"id": orch, "label": orch, "kind": "orchestrator"},
            {
                "id": "analyze-routing",
                "label": "analyze-routing",
                "subagent": "routing-analyzer",
                "kind": "step",
            },
            {"id": "step-alpha", "label": "step-alpha", "subagent": None, "kind": "step"},
            {"id": "done", "label": "done", "kind": "terminal"},
        ],
        "edges": [
            {
                "id": "e-orch-ar",
                "from": orch,
                "to": "analyze-routing",
                "kind": "branch",
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
            loop_edge,
            {"id": "e-done", "from": "step-alpha", "to": "done", "kind": "main"},
        ],
    }


def _stub_agents(root: Path, *names: str) -> None:
    for cli in (".qwen", ".gigacode", ".opencode"):
        folder = root / cli / "agents"
        folder.mkdir(parents=True, exist_ok=True)
        for name in names:
            path = folder / f"{name}.md"
            if not path.is_file():
                path.write_text(f"---\nname: {name}\n---\n# {name}\n", encoding="utf-8")


class Session3AuthoringTest(unittest.TestCase):
    def test_orchestrator_md_create_no_silent_overwrite(self) -> None:
        with tempfile.TemporaryDirectory(prefix="orch-md-") as tmp:
            root = Path(tmp)
            notes = ensure_orchestrator_md(PACK_ID, root)
            path = root / ".qwen" / "agents" / f"{PACK_ID}-orchestrator.md"
            self.assertTrue(path.is_file())
            self.assertTrue(any("created" in n for n in notes), notes)
            text = path.read_text(encoding="utf-8")
            self.assertIn(PACK_ID, text)
            self.assertEqual(text, render_orchestrator_md(PACK_ID, root))

            path.write_text(text + "\n# hand edit\n", encoding="utf-8")
            notes2 = ensure_orchestrator_md(PACK_ID, root, overwrite=False)
            self.assertTrue(any("left untouched" in n for n in notes2), notes2)
            self.assertIn("# hand edit", path.read_text(encoding="utf-8"))

            notes3 = ensure_orchestrator_md(PACK_ID, root, overwrite=True)
            self.assertTrue(any("overwritten" in n for n in notes3), notes3)
            self.assertNotIn("# hand edit", path.read_text(encoding="utf-8"))

    def test_after_step_loop_does_not_invent_bool_when(self) -> None:
        alpha_id = invent_condition_id(ALPHA_TEXT, set())
        with tempfile.TemporaryDirectory(prefix="after-step-") as tmp:
            root = Path(tmp)
            init_pack(PACK_ID, "routing-state", root)
            _stub_agents(root, "routing-analyzer")
            skill_dst = root / ".qwen" / "skills" / "analyze-routing"
            skill_dst.mkdir(parents=True)
            (skill_dst / "SKILL.md").write_text("# analyze-routing\n", encoding="utf-8")
            orch = f"{PACK_ID}-orchestrator"
            body = {"id": PACK_ID, "graph": _graph(orch, after_step=True)}

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

            graph = load_yaml(root / "pipelines" / PACK_ID / "graph.yaml")
            loop = next(e for e in graph["edges"] if e.get("id") == "e-alpha-ar")
            self.assertTrue(loop.get("after_step") is True)
            self.assertEqual(loop.get("kind"), "loop")
            self.assertNotIn("condition", loop)
            self.assertNotIn("conditions", loop)

            rc = load_yaml(root / "pipelines" / PACK_ID / "routing_conditions.yaml")
            fields = rc.get("status_fields") or {}
            self.assertIn(alpha_id, fields)
            for key in fields:
                self.assertNotIn("zakonchil", key)
                self.assertFalse(key.startswith("has_agent_zakonchil"))

            orch_path = root / ".qwen" / "agents" / f"{PACK_ID}-orchestrator.md"
            self.assertTrue(orch_path.is_file())
            checklist = applied.get("checklist") or runnable_checklist(applied["pack"], root)
            by_id = {item["id"]: item for item in checklist}
            self.assertTrue(by_id["yaml"]["ok"], by_id)
            self.assertTrue(by_id["collectors"]["ok"], by_id)
            self.assertTrue(by_id["orchestrator"]["ok"], by_id)
            self.assertTrue(by_id["analyzer"]["ok"], by_id)
            self.assertTrue(any("after_step" in n for n in notes), notes)


if __name__ == "__main__":
    unittest.main()

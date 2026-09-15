#!/usr/bin/env python3
"""Runtime --pack-dir overlay: lab pack is not a compiled pipeline id."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

from pipeline_pack import (  # noqa: E402
    discover_pipeline_ids,
    load_pack_module,
    pack_folder,
    reset_pack_dir,
    set_pack_dir,
)
from pipeline_runtime import load_pipeline_schema  # noqa: E402

LAB_PACK = ROOT / "pipeline-lab" / "pack"


class PackDirOverlayTest(unittest.TestCase):
    def tearDown(self) -> None:
        reset_pack_dir()

    def test_discover_pipeline_ids_ignores_lab(self) -> None:
        ids = discover_pipeline_ids(ROOT)
        self.assertIn("spec", ids)
        self.assertNotIn("pack", ids)
        self.assertNotIn("pipeline-lab", ids)
        self.assertTrue(all("/" not in pid for pid in ids))
        self.assertFalse((ROOT / "pipelines" / "graph-lab").exists())

    def test_pack_dir_loads_modules_from_lab_folder(self) -> None:
        prod = load_pack_module("spec", "collectors")
        self.assertIsNotNone(prod)
        self.assertEqual(Path(prod.__file__).resolve().parent, (ROOT / "pipelines" / "spec").resolve())

        set_pack_dir(LAB_PACK, "spec")
        lab = load_pack_module("spec", "collectors")
        self.assertIsNotNone(lab)
        self.assertEqual(Path(lab.__file__).resolve().parent, LAB_PACK.resolve())
        self.assertEqual(pack_folder("spec"), LAB_PACK.resolve())
        self.assertEqual(pack_folder("calibration"), ROOT / "pipelines" / "calibration")

    def test_pack_dir_schema_comes_from_overlay_yaml(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="pack-dir-schema-"))
        try:
            shutil.copytree(LAB_PACK, tmp / "pack")
            graph = tmp / "pack" / "graph.yaml"
            text = graph.read_text(encoding="utf-8")
            graph.write_text(
                text.replace("label: Spec pipeline (SIHIST)", "label: Lab overlay spec", 1),
                encoding="utf-8",
            )
            set_pack_dir(tmp / "pack", "spec")
            schema = load_pipeline_schema("spec")
            self.assertEqual(schema.get("label"), "Lab overlay spec")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        reset_pack_dir()
        schema = load_pipeline_schema("spec")
        self.assertEqual(schema.get("label"), "Spec pipeline (SIHIST)")

    def test_delegate_cli_pack_dir_json_contract(self) -> None:
        env = {**os.environ, "PYTHONPATH": str(SCRIPTS)}
        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "pipeline_delegate.py"),
                "lab-empty",
                "--cli",
                "qwen",
                "--pipeline",
                "spec",
                "--pack-dir",
                str(LAB_PACK),
            ],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload.get("ok"), payload)
        self.assertEqual(payload.get("pipeline_id"), "spec")
        self.assertEqual(payload.get("action"), "task")
        task = payload.get("task") or {}
        dispatch = payload.get("dispatch") or {}
        self.assertEqual(task.get("step"), dispatch.get("next_step"))
        self.assertEqual(task.get("step"), "analyze-routing")
        self.assertEqual(task.get("subagent_type"), "routing-analyzer")
        active = ROOT / "pipeline-lab" / ".pipeline-active-task.json"
        self.assertTrue(active.is_file(), "workspace must stay under pipeline-lab/")
        prod_active = ROOT / ".pipeline-active-task.json"
        if prod_active.is_file():
            data = json.loads(prod_active.read_text(encoding="utf-8"))
            self.assertNotEqual(data.get("slug"), "lab-empty")

    def test_delegate_without_pack_dir_uses_compiled_spec(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="pack-dir-prod-"))
        try:
            (tmp / "Feature-writing" / "lab-empty").mkdir(parents=True)
            env = {**os.environ, "PYTHONPATH": str(SCRIPTS)}
            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "pipeline_delegate.py"),
                    "lab-empty",
                    "--cli",
                    "qwen",
                    "--pipeline",
                    "spec",
                    "--root",
                    str(tmp),
                ],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload.get("action"), "task")
            self.assertEqual((payload.get("task") or {}).get("step"), "analyze-routing")
            self.assertEqual((payload.get("task") or {}).get("subagent_type"), "routing-analyzer")
            self.assertTrue((tmp / ".pipeline-active-task.json").is_file())
            self.assertFalse((tmp / "pipelines").exists())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

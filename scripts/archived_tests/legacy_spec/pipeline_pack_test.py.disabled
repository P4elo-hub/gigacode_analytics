#!/usr/bin/env python3
"""Phase 8 authoring: pack JSON schema, catalog contract, init-pack, roundtrip."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

from pipeline_compile import compile_outputs, main as compile_main, validate_source  # noqa: E402
from pipeline_pack import (  # noqa: E402
    CATALOG_KEYS,
    CATALOG_PIPELINE_ITEM_KEYS,
    CATALOG_PREDICATES_KEYS,
    CATALOG_ROUTING_CONDITION_KEYS,
    CATALOG_RUNTIME_KEYS,
    CATALOG_VERSION,
    PACK_SCHEMA_RELPATH,
    apply_pack_json,
    build_catalog,
    export_pack_json,
    merge_compiled_source,
)
from pipeline_pack_authoring import (  # noqa: E402
    SCHEMA_PATH,
    TEMPLATES,
    build_template_payload,
    init_pack,
    init_pack_golden_hints,
    load_pack_schema,
    validate_pack_json,
)

PACK_JSON = SCRIPTS / "fixtures" / "pack_smoke" / "minimal" / "pack.json"


class CatalogContractTest(unittest.TestCase):
    def test_catalog_keys_and_types(self) -> None:
        catalog = build_catalog(ROOT)
        self.assertTrue(set(CATALOG_KEYS) <= set(catalog), set(CATALOG_KEYS) - set(catalog))
        self.assertEqual(catalog["catalog_version"], CATALOG_VERSION)
        self.assertEqual(catalog["pack_schema"], PACK_SCHEMA_RELPATH)
        self.assertIsInstance(catalog["pipelines"], list)
        self.assertIsInstance(catalog["agents"], list)
        self.assertIsInstance(catalog["skills"], list)
        self.assertIsInstance(catalog["steps"], dict)
        self.assertIsInstance(catalog["runtime"], dict)
        self.assertIsInstance(catalog["pack_files"], list)
        self.assertIsInstance(catalog["optional_python"], list)
        self.assertTrue(set(CATALOG_PREDICATES_KEYS) <= set(catalog["predicates"]))
        self.assertIsInstance(catalog["predicates"]["core"], list)
        self.assertIsInstance(catalog["predicates"]["by_pipeline"], dict)
        self.assertIn("routing_conditions", catalog)
        spec_rc = catalog["routing_conditions"]["spec"]
        self.assertTrue(set(CATALOG_ROUTING_CONDITION_KEYS) <= set(spec_rc), spec_rc)
        field_ids = {item["id"] for item in spec_rc["fields"]}
        self.assertIn("open_gaps", field_ids)
        edge_ids = {item["id"] for item in spec_rc["edge_conditions"]}
        self.assertIn("open_gaps", edge_ids)
        self.assertIn("not_has_context", edge_ids)
        self.assertIn("spec", catalog["steps"])
        self.assertIn("calibration", catalog["steps"])
        ids = {item["id"] for item in catalog["pipelines"]}
        self.assertIn("spec", ids)
        self.assertIn("calibration", ids)
        for item in catalog["pipelines"]:
            self.assertTrue(set(CATALOG_PIPELINE_ITEM_KEYS) <= set(item), item)
        for pid, contract in catalog["runtime"].items():
            self.assertTrue(set(CATALOG_RUNTIME_KEYS) <= set(contract), pid)
            self.assertIsInstance(contract["loop"], list)
            self.assertEqual(len(contract["loop"]), 5)
            self.assertIn(f"--pipeline {pid}", contract["loop"][0])

    def test_catalog_cli_same_keys(self) -> None:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(SCRIPTS)
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "pipeline_compile.py"), "--catalog"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
            env=env,
        )
        catalog = json.loads(result.stdout)
        self.assertTrue(set(CATALOG_KEYS) <= set(catalog))


class PackSchemaTest(unittest.TestCase):
    def test_schema_file_minimal_contract(self) -> None:
        schema = load_pack_schema()
        self.assertEqual(schema["required"], ["id", "graph", "status", "registry"])
        self.assertIn("dispatch", schema["properties"])
        self.assertNotIn("dispatch", schema["required"])
        self.assertIn("routing_conditions", schema["properties"])
        self.assertNotIn("routing_conditions", schema["required"])
        self.assertTrue(SCHEMA_PATH.is_file())
        edge_props = schema["properties"]["graph"]["properties"]["edges"]["items"]["properties"]
        self.assertIn("condition", edge_props)
        self.assertIn("condition_label", edge_props)

    def test_minimal_pack_json_validates(self) -> None:
        payload = json.loads(PACK_JSON.read_text(encoding="utf-8"))
        self.assertEqual(validate_pack_json(payload), [])

    def test_spec_and_calibration_export_validate(self) -> None:
        for pid in ("spec", "calibration"):
            exported = export_pack_json(pid, ROOT)
            self.assertEqual(validate_pack_json(exported), [], pid)

    def test_missing_graph_is_readable(self) -> None:
        errors = validate_pack_json({"id": "demo-pack", "status": {}, "registry": {}})
        self.assertTrue(any("graph" in item for item in errors), errors)

    def test_bad_id_rejected(self) -> None:
        payload = json.loads(PACK_JSON.read_text(encoding="utf-8"))
        payload["id"] = "Not_Kebab"
        errors = validate_pack_json(payload)
        self.assertTrue(any("must match" in item and "id" in item for item in errors), errors)

    def test_orchestrator_must_be_node(self) -> None:
        payload = json.loads(PACK_JSON.read_text(encoding="utf-8"))
        payload["graph"]["orchestrator"] = "missing-orch"
        errors = validate_pack_json(payload)
        self.assertTrue(any("orchestrator" in item and "not a node" in item for item in errors), errors)

    def test_from_json_rejects_before_write(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pack-json-") as tmp:
            root = Path(tmp)
            with self.assertRaises(ValueError) as ctx:
                apply_pack_json({"id": "broken-pack"}, root)
            self.assertIn("invalid pack JSON", str(ctx.exception))
            self.assertFalse((root / "pipelines" / "broken-pack").exists())

    def test_from_json_cli_readable_error(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pack-cli-") as tmp:
            bad = Path(tmp) / "bad.json"
            bad.write_text('{"id": "nope"}', encoding="utf-8")
            rc = compile_main(["--from-json", str(bad)])
            self.assertEqual(rc, 1)


class PackRoundtripTest(unittest.TestCase):
    def test_from_json_compiles_in_temp(self) -> None:
        payload = json.loads(PACK_JSON.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory(prefix="pack-rt-") as tmp:
            root = Path(tmp)
            apply_pack_json(payload, root)
            data = merge_compiled_source(root)
            errors = validate_source(data)
            schema_text, registry_text = compile_outputs(data)
            schema = json.loads(schema_text)
            registry = json.loads(registry_text)
            self.assertEqual(errors, [])
            self.assertIn("smoke-minimal", schema["pipelines"])
            self.assertIn("smoke-minimal", registry["pipelines"])
            self.assertNotIn("smoke-minimal", registry.get("dispatch") or {})

    def test_export_json_roundtrip(self) -> None:
        payload = json.loads(PACK_JSON.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory(prefix="pack-ex-") as tmp:
            root = Path(tmp)
            apply_pack_json(payload, root)
            exported = export_pack_json("smoke-minimal", root)
            self.assertEqual(validate_pack_json(exported), [])
            exported["id"] = "smoke-roundtrip"
            apply_pack_json(exported, root)
            schema_text, _ = compile_outputs(merge_compiled_source(root))
            self.assertIn("smoke-roundtrip", json.loads(schema_text)["pipelines"])


class InitPackTest(unittest.TestCase):
    def test_templates_defined(self) -> None:
        self.assertEqual(TEMPLATES, ("minimal", "orchestrator-only", "full-dispatch", "routing-state"))

    def test_full_dispatch_init_hints_golden(self) -> None:
        hints = init_pack_golden_hints("demo-dispatch", "full-dispatch")
        joined = "\n".join(hints)
        self.assertIn("cases.json", joined)
        self.assertIn("COVERAGE.md", joined)
        self.assertIn("demo-dispatch", joined)

    def test_init_minimal_compiles(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pack-init-") as tmp:
            root = Path(tmp)
            written = init_pack("demo-min", "minimal", root)
            names = {path.name for path in written}
            self.assertEqual(names, {"graph.yaml", "dispatch.yaml", "status.yaml", "registry.yaml"})
            errors = validate_source(merge_compiled_source(root))
            self.assertEqual(errors, [])
            schema_text, _ = compile_outputs(merge_compiled_source(root))
            self.assertIn("demo-min", schema_text)

    def test_init_orchestrator_only_compiles(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pack-init-") as tmp:
            root = Path(tmp)
            init_pack("demo-orch", "orchestrator-only", root)
            data = merge_compiled_source(root)
            errors = validate_source(data)
            self.assertEqual(errors, [])
            _, registry_text = compile_outputs(data)
            registry = json.loads(registry_text)
            self.assertNotIn("demo-orch", registry.get("dispatch") or {})

    def test_init_full_dispatch_compiles_with_pack_root(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pack-init-") as tmp:
            root = Path(tmp)
            init_pack("demo-dispatch", "full-dispatch", root)
            with patch("pipeline_pack.repo_root", return_value=root):
                data = merge_compiled_source(root)
                errors = validate_source(data)
                schema_text, registry_text = compile_outputs(data)
            self.assertEqual(errors, [])
            self.assertIn("demo-dispatch", schema_text)
            registry = json.loads(registry_text)
            self.assertIn("demo-dispatch", registry.get("dispatch") or {})

    def test_init_routing_state_writes_stub_and_analyze_routing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pack-init-") as tmp:
            root = Path(tmp)
            written = init_pack("demo-rs", "routing-state", root)
            names = {path.name for path in written}
            self.assertIn("routing_conditions.yaml", names)
            self.assertIn("collectors.py", names)
            with patch("pipeline_pack.repo_root", return_value=root):
                data = merge_compiled_source(root)
                errors = validate_source(data)
            self.assertEqual(errors, [])
            graph = (root / "pipelines" / "demo-rs" / "graph.yaml").read_text(encoding="utf-8")
            self.assertIn("analyze-routing", graph)
            rc = (root / "pipelines" / "demo-rs" / "routing_conditions.yaml").read_text(encoding="utf-8")
            self.assertIn("edge_conditions", rc)

    def test_init_refuses_existing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pack-init-") as tmp:
            root = Path(tmp)
            init_pack("demo-dup", "minimal", root)
            with self.assertRaises(FileExistsError):
                init_pack("demo-dup", "minimal", root)

    def test_schema_ok_unknown_when_fails_compile(self) -> None:
        payload = build_template_payload("demo-when", "full-dispatch")
        payload["dispatch"]["rules"][0]["when"] = "not_a_real_predicate"
        self.assertEqual(validate_pack_json(payload), [])
        with tempfile.TemporaryDirectory(prefix="pack-when-") as tmp:
            root = Path(tmp)
            apply_pack_json(payload, root)
            errors = validate_source(merge_compiled_source(root))
            self.assertTrue(any("unknown when" in item for item in errors), errors)

    def test_unknown_subagent_tells_author_to_add_agent(self) -> None:
        payload = build_template_payload("demo-agent", "minimal")
        payload["registry"]["orchestrator_owned"] = []
        payload["registry"]["step_to_subagent"] = {"only-step": "not-a-real-agent-xyz"}
        with tempfile.TemporaryDirectory(prefix="pack-init-") as tmp:
            root = Path(tmp)
            apply_pack_json(payload, root)
            errors = validate_source(merge_compiled_source(root))
            self.assertTrue(
                any("add agent 'not-a-real-agent-xyz'" in item for item in errors),
                errors,
            )


if __name__ == "__main__":
    unittest.main()

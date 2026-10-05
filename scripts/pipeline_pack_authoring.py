"""Pack authoring: JSON schema validate, templates, --init-pack."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pipeline_pack import packs_dir

SCHEMA_PATH = Path(__file__).resolve().parent / "pipeline_pack_schema.json"
PACK_ID_RE = re.compile(r"^[a-z][a-z0-9-]*$")
TEMPLATES = ("minimal", "orchestrator-only", "full-dispatch", "routing-state")
ROUTING_STATE_ARTIFACT_PATH = "{task_id}/routing-state.json"


def load_pack_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def normalize_pack_payload(payload: dict) -> dict:
    data = dict(payload)
    if not data.get("id") and data.get("pipeline_id"):
        data["id"] = str(data["pipeline_id"])
    return data


def validate_pack_json(payload: object) -> list[str]:
    """Layer 1: pack JSON shape. Empty list = schema-ok; compile may still fail.

    Uses a subset walker over pipeline_pack_schema.json (no jsonschema dep).
    Does not check ``when:`` catalog names or agent files — that is
    ``pipeline_compile.validate_source`` (layer 2).
    """
    if not isinstance(payload, dict):
        return ["pack JSON: payload must be an object"]
    data = normalize_pack_payload(payload)
    errors = _validate_schema(data, load_pack_schema(), "pack JSON")
    graph = data.get("graph")
    if isinstance(graph, dict):
        nodes = graph.get("nodes") if isinstance(graph.get("nodes"), list) else []
        node_ids = {n.get("id") for n in nodes if isinstance(n, dict) and n.get("id")}
        orch = graph.get("orchestrator")
        if orch and orch not in node_ids:
            errors.append(f"pack JSON: graph.orchestrator {orch!r} is not a node id")
    return errors


def _json_type(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _type_ok(value: object, allowed: list[str]) -> bool:
    got = _json_type(value)
    if got in allowed:
        return True
    if got == "integer" and "number" in allowed:
        return True
    return False


def _validate_schema(instance: object, schema: dict, path: str) -> list[str]:
    """Subset JSON Schema (type, required, properties, items, minItems, minLength, pattern).

    The $schema URL in pipeline_pack_schema.json is the frontend contract.
    This walker is the no-dependency runtime. Optional: pip install jsonschema.
    """
    errors: list[str] = []
    raw_type = schema.get("type")
    allowed = raw_type if isinstance(raw_type, list) else [raw_type] if raw_type else []
    if allowed and not _type_ok(instance, allowed):
        return [f"{path}: expected {'|'.join(allowed)}, got {_json_type(instance)}"]
    if instance is None:
        return errors
    if "pattern" in schema and isinstance(instance, str):
        if re.search(schema["pattern"], instance) is None:
            errors.append(f"{path}: must match {schema['pattern']}, got {instance!r}")
    if "minLength" in schema and isinstance(instance, str) and len(instance) < int(schema["minLength"]):
        errors.append(f"{path}: too short")
    if isinstance(instance, dict):
        for key in schema.get("required") or []:
            if key not in instance:
                errors.append(f"{path}: missing required field {key!r}")
        props = schema.get("properties") or {}
        for key, child in instance.items():
            if key in props and isinstance(props[key], dict):
                errors.extend(_validate_schema(child, props[key], f"{path}.{key}"))
    if isinstance(instance, list):
        min_items = schema.get("minItems")
        if min_items is not None and len(instance) < int(min_items):
            errors.append(f"{path}: expected at least {min_items} items")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, child in enumerate(instance):
                errors.extend(_validate_schema(child, item_schema, f"{path}[{index}]"))
    return errors


def build_template_payload(pipeline_id: str, template: str = "minimal") -> dict[str, Any]:
    if template not in TEMPLATES:
        raise ValueError(f"unknown template {template!r}; known: {', '.join(TEMPLATES)}")
    if not PACK_ID_RE.fullmatch(pipeline_id):
        raise ValueError(f"pack id must be kebab-case, got {pipeline_id!r}")
    if template == "full-dispatch":
        return _template_full_dispatch(pipeline_id)
    if template == "routing-state":
        return _template_routing_state(pipeline_id)
    if template == "orchestrator-only":
        return _template_orchestrator_only(pipeline_id)
    return _template_minimal(pipeline_id)


def init_pack(pipeline_id: str, template: str = "minimal", root: Path | None = None) -> list[Path]:
    folder = packs_dir(root) / pipeline_id
    if folder.exists():
        raise FileExistsError(f"pack already exists: {folder}")
    from pipeline_pack import apply_pack_json

    payload = build_template_payload(pipeline_id, template)
    written = apply_pack_json(payload, root)
    if template == "routing-state":
        collectors = folder / "collectors.py"
        collectors.write_text(ROUTING_STATE_COLLECTORS, encoding="utf-8")
        written.append(collectors)
    return written


def init_pack_golden_hints(pipeline_id: str, template: str) -> list[str]:
    """Phase 9: remind authors to add dispatch golden (or a no-dispatch waiver)."""
    golden = f"scripts/fixtures/dispatch_golden/{pipeline_id}"
    if template in {"full-dispatch", "routing-state"}:
        return [
            f"then: add {golden}/cases.json (+ COVERAGE.md) — "
            "dispatch golden is required (see scripts/PIPELINE-GOLDEN.md)",
        ]
    return [
        f"then: add {golden}/cases.json or {golden}/WAIVER.md "
        "(no-dispatch) — see scripts/PIPELINE-GOLDEN.md",
    ]


def _graph(pipeline_id: str, label: str, step_id: str) -> dict:
    orch = f"{pipeline_id}-orchestrator"
    return {
        "label": label,
        "orchestrator": orch,
        "nodes": [
            {"id": orch, "label": orch, "kind": "orchestrator"},
            {"id": step_id, "label": step_id, "subagent": None, "kind": "step"},
            {"id": "done", "label": "done", "kind": "terminal"},
        ],
        "edges": [
            {"id": "e-start", "from": orch, "to": step_id, "kind": "main"},
            {"id": "e-done", "from": step_id, "to": "done", "kind": "main"},
        ],
    }


def _registry(step_id: str) -> dict:
    return {
        "step_to_subagent": {},
        "orchestrator_owned": [step_id],
        "gated_subagents": [],
        "restartable_steps": [step_id],
    }


def _template_minimal(pipeline_id: str) -> dict:
    return {
        "id": pipeline_id,
        "graph": _graph(pipeline_id, f"{pipeline_id} pipeline", "only-step"),
        "dispatch": {"invariant_after_priority": 0, "invariants": [], "rules": []},
        "status": {
            "task_kind": "slug",
            "artifacts": {},
            "collectors": [],
            "stale": [],
            "orchestrator": {},
            "messages": {
                "ready": f"{pipeline_id} ready",
                "stopped": f"{pipeline_id} stopped",
            },
        },
        "registry": _registry("only-step"),
    }


def _template_orchestrator_only(pipeline_id: str) -> dict:
    payload = _template_minimal(pipeline_id)
    payload["graph"] = _graph(pipeline_id, f"{pipeline_id} pipeline", "first-step")
    payload["dispatch"] = {
        "invariant_after_priority": 0,
        "invariants": [],
        "fallback": {
            "next": None,
            "outcome": "ready",
            "reason": f"{pipeline_id} graph only — dispatch not configured",
        },
        "rules": [],
    }
    payload["status"]["messages"] = {
        "ready": f"{pipeline_id} pack has no dispatch rules.",
        "ready_title": f"{pipeline_id} без dispatch",
        "ready_detail": f"{pipeline_id} pack has no dispatch rules.",
        "ready_fix": "Оркестратор ведёт шаги по markdown; delegate проверяет рёбра графа.",
        "stopped": f"{pipeline_id} пайплайн остановлен.",
    }
    payload["registry"] = _registry("first-step")
    return payload


def _template_full_dispatch(pipeline_id: str) -> dict:
    payload = _template_orchestrator_only(pipeline_id)
    payload["status"]["artifacts"] = {
        "main": {
            "path": "{task_id}/main.md",
            "exists_as": "has_main",
            "missing_reason": "Нет артефакта main — создай файл или поправь status.yaml artifacts.main.path",
        }
    }
    payload["status"]["messages"]["ready"] = f"{pipeline_id} ready"
    payload["dispatch"] = {
        "invariant_after_priority": 0,
        "invariants": [],
        "fallback": {
            "next": None,
            "outcome": "ready",
            "reason": f"{pipeline_id} complete",
        },
        "rules": [
            {"priority": 10, "when": "not_has_main", "next": "first-step"},
        ],
    }
    return payload


# Canonical overlay collectors.py for every routing-state authoring pack.
# Domain field names live only in routing_conditions.yaml / routing-state.json.
ROUTING_STATE_COLLECTORS = '''"""Overlay collector for a routing-state pack (Phase 13 template)."""

from pipeline_routing_state import overlay_collector

COLLECTORS = {"routing_state": overlay_collector}
'''

# Back-compat alias for older imports / tests.
_ROUTING_STATE_COLLECTORS = ROUTING_STATE_COLLECTORS


def _routing_state_stale_vs(status: dict) -> list[str]:
    artifacts = status.get("artifacts") if isinstance(status.get("artifacts"), dict) else {}
    artifact_ids = [str(key) for key in artifacts if str(key) != "routing_state"]
    if "main" in artifact_ids:
        return ["main"]
    return artifact_ids[:1]


def _routing_conditions_stub(
    pipeline_id: str,
    first_step: str = "first-step",
    stale_vs: list[str] | None = None,
) -> dict:
    return {
        "schema_version": 1,
        "status_fields": {},
        "engine_fields": [
            "has_routing_state",
            "routing_state_invalid",
            "routing_state_error",
            "stale",
        ],
        "edge_conditions": {
            "routing_state_needs_refresh": {
                "expr": {
                    "any": [
                        {"field": "has_routing_state", "op": "falsy"},
                        {"field": "stale", "op": "contains", "value": "routing_state"},
                    ]
                },
                "dispatch": {"priority": 5, "next": "analyze-routing"},
                "label": "routing-state missing/stale",
                "reason": "нет routing-state.json — нужен analyze-routing",
            },
            "not_has_main": {
                "core": True,
                "expr": {"field": "has_main", "op": "falsy"},
                "dispatch": {"priority": 10, "next": first_step},
                "label": "no main",
                "reason": "Нет артефакта main",
            },
        },
        "stale_vs": list(stale_vs or []),
        "validate_ids": ["routing-state-missing", "routing-state-stale"],
        "when_to_run_analyzer": ["routing-state missing"],
        "overlay": {"live_default": "routing_state"},
    }


def ensure_routing_state_authoring(payload: dict) -> dict:
    """If collector_mode is routing_state, add analyze-routing + routing_conditions stub."""
    data = dict(payload)
    status = data.get("status") if isinstance(data.get("status"), dict) else {}
    if str(status.get("collector_mode") or "") != "routing_state":
        return data
    graph = dict(data.get("graph") or {})
    nodes = [dict(node) if isinstance(node, dict) else node for node in (graph.get("nodes") or [])]
    ids = {node.get("id") for node in nodes if isinstance(node, dict)}
    orch = graph.get("orchestrator")
    if "analyze-routing" not in ids:
        nodes.append(
            {
                "id": "analyze-routing",
                "label": "analyze-routing",
                "subagent": "routing-analyzer",
                "kind": "analyzer",
            }
        )
        graph["nodes"] = nodes
        edges = [dict(edge) if isinstance(edge, dict) else edge for edge in (graph.get("edges") or [])]
        if orch:
            edges.append(
                {
                    "id": "e-orch-ar",
                    "from": orch,
                    "to": "analyze-routing",
                    "kind": "branch",
                    "label": "routing-state missing/stale",
                    "condition": "routing_state_needs_refresh",
                }
            )
            graph["edges"] = edges
        data["graph"] = graph
    artifacts = dict(status.get("artifacts") or {})
    if "routing_state" not in artifacts:
        artifacts["routing_state"] = {
            "path": ROUTING_STATE_ARTIFACT_PATH,
            "exists_as": "has_routing_state",
            "missing_reason": "нет routing-state.json — нужен analyze-routing",
        }
        status["artifacts"] = artifacts
        data["status"] = status
    if not data.get("routing_conditions"):
        first = "first-step"
        for node in nodes:
            if isinstance(node, dict) and node.get("kind") == "step" and node.get("id") not in {
                "analyze-routing",
            }:
                first = str(node.get("id") or first)
                break
        data["routing_conditions"] = _routing_conditions_stub(
            str(data.get("id") or ""),
            first,
            _routing_state_stale_vs(status),
        )
    return data


def _template_routing_state(pipeline_id: str) -> dict:
    payload = _template_full_dispatch(pipeline_id)
    payload["status"]["collector_mode"] = "routing_state"
    payload["status"]["collectors"] = [{"id": "routing_state", "source": "routing_state"}]
    payload["status"]["artifacts"]["routing_state"] = {
        "path": ROUTING_STATE_ARTIFACT_PATH,
        "exists_as": "has_routing_state",
        "missing_reason": "нет routing-state.json — нужен analyze-routing",
    }
    orch = payload["graph"]["orchestrator"]
    payload["graph"]["nodes"].insert(
        1,
        {
            "id": "analyze-routing",
            "label": "analyze-routing",
            "subagent": "routing-analyzer",
            "kind": "analyzer",
        },
    )
    payload["graph"]["edges"].append(
        {
            "id": "e-orch-ar",
            "from": orch,
            "to": "analyze-routing",
            "kind": "branch",
            "label": "routing-state missing/stale",
            "condition": "routing_state_needs_refresh",
        }
    )
    payload["registry"]["step_to_subagent"] = {"analyze-routing": "routing-analyzer"}
    payload["registry"]["gated_subagents"] = ["routing-analyzer"]
    payload["registry"]["restartable_steps"] = ["analyze-routing", "first-step"]
    payload["routing_conditions"] = _routing_conditions_stub(
        pipeline_id,
        stale_vs=_routing_state_stale_vs(payload["status"]),
    )
    payload["dispatch"]["rules"] = [
        {"priority": 5, "when": "routing_state_needs_refresh", "next": "analyze-routing"},
        {"priority": 10, "when": "not_has_main", "next": "first-step"},
    ]
    payload["dispatch"]["fallback"] = {
        "next": "analyze-routing",
        "reason": "routing-state не готов",
    }
    return payload


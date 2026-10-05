"""Resolve pipeline_id, load per-pipeline schema / dispatch, expose runtime_contract().

Canonical orchestrator loop (any pack):
delegate → action → append_run_log → ingest → validate, all with ``--pipeline <id>``.
See PIPELINE-RUNTIME.md.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pipeline_common import load_pipeline_registry

SCRIPTS = Path(__file__).resolve().parent
SCHEMA_PATH = SCRIPTS / "pipeline_schema.json"
DEFAULT_PIPELINE_ID = "spec-v2"


@lru_cache(maxsize=1)
def load_schema_root() -> dict:
    if not SCHEMA_PATH.is_file():
        raise FileNotFoundError(
            f"Missing {SCHEMA_PATH} — run: python3 scripts/pipeline_compile.py --apply"
        )
    payload = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    pipelines = payload.get("pipelines")
    if not isinstance(payload, dict) or not isinstance(pipelines, dict):
        raise ValueError(f"Invalid schema: {SCHEMA_PATH}")
    return payload


def known_pipeline_ids() -> tuple[str, ...]:
    return tuple(load_schema_root()["pipelines"].keys())


def normalize_pipeline_id(pipeline_id: str) -> str:
    known = known_pipeline_ids()
    if pipeline_id not in known:
        raise ValueError(f"unknown pipeline_id: {pipeline_id!r}; known: {', '.join(known)}")
    return pipeline_id


def resolve_pipeline_id(
    pipeline_arg: str | None = None,
    active_task: dict | None = None,
    *,
    default: str | None = None,
) -> str:
    """CLI flag wins, then active-task.pipeline; no silent runtime default."""
    if pipeline_arg and pipeline_arg not in {"", "auto"}:
        return normalize_pipeline_id(pipeline_arg)
    if active_task:
        marked = active_task.get("pipeline") or active_task.get("pipeline_id")
        if marked:
            return normalize_pipeline_id(str(marked))
    if default not in {None, "", "auto"}:
        return normalize_pipeline_id(str(default))
    raise ValueError("pipeline id required: pass --pipeline <id> or set active-task.pipeline")


def load_pipeline_schema(pipeline_id: str) -> dict:
    from pipeline_pack import load_pack, resolve_pack_dir, resolve_pack_pipeline_id

    pipe_id = normalize_pipeline_id(pipeline_id)
    override = resolve_pack_dir()
    override_id = resolve_pack_pipeline_id()
    if override is not None and (override_id is None or pipe_id == override_id):
        return load_pack(pipe_id)["graph"]
    return load_schema_root()["pipelines"][pipe_id]


def outgoing_steps(schema: dict, from_step: str) -> set[str]:
    """Step ids reachable in one edge from ``from_step``."""
    return {
        str(edge.get("to") or "")
        for edge in schema.get("edges") or []
        if edge.get("from") == from_step and edge.get("to")
    }


def node_asks_user(pipeline_id: str, step: str) -> bool:
    """True when the graph node declares ``ask: true`` (human handshake on this cell)."""
    if not step:
        return False
    for node in load_pipeline_schema(pipeline_id).get("nodes") or []:
        if str(node.get("id") or "") == step:
            return bool(node.get("ask"))
    return False


def load_pipeline_dispatch(pipeline_id: str) -> dict | None:
    """Compiled dispatch.<id>, or None when that pipeline has no rules."""
    registry = load_pipeline_registry()
    dispatch = registry.get("dispatch")
    if not isinstance(dispatch, dict):
        return None
    block = dispatch.get(pipeline_id)
    return block if isinstance(block, dict) else None


def dispatch_supported(pipeline_id: str) -> bool:
    block = load_pipeline_dispatch(pipeline_id)
    if not isinstance(block, dict):
        return False
    return bool(block.get("rules") or block.get("invariants"))


def runtime_contract(pipeline_id: str | None = None) -> dict:
    """Canonical orchestrator loop for a pack (docs / ``pipeline_compile.py --catalog``)."""
    if not pipeline_id:
        raise ValueError("pipeline id required for runtime_contract")
    pipe_id = normalize_pipeline_id(pipeline_id)
    schema = load_pipeline_schema(pipe_id)
    pack_validate = Path(__file__).resolve().parent.parent / "pipelines" / pipe_id / "validate.py"
    return {
        "pipeline_id": pipe_id,
        "orchestrator": schema.get("orchestrator") or "",
        "dispatch_supported": dispatch_supported(pipe_id),
        "loop": [
            f"python3 scripts/pipeline_delegate.py <task_id> --cli qwen --pipeline {pipe_id}",
            "action → task | ask_user | write_feature_cycle | orchestrator_only | ready | stopped | error",
            (
                "python3 scripts/append_run_log.py --slug <task_id> --step <step> "
                f"--subagent <agent> --result ok --pipeline {pipe_id}"
            ),
            f"python3 scripts/ingest_session_telemetry.py <task_id> --cli qwen --pipeline {pipe_id}",
            f"python3 scripts/pipeline_validate.py <task_id> --pipeline {pipe_id}",
        ],
        "validate": {
            "engine": "scripts/pipeline_validate.py",
            "pack": f"pipelines/{pipe_id}/validate.py",
            "extra_advice": pack_validate.is_file(),
        },
    }

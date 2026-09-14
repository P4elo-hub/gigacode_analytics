"""Resolve pipeline_id and load per-pipeline schema / dispatch."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pipeline_common import load_pipeline_registry

SCRIPTS = Path(__file__).resolve().parent
SCHEMA_PATH = SCRIPTS / "pipeline_schema.json"
DEFAULT_PIPELINE_ID = "spec"


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
    default: str = DEFAULT_PIPELINE_ID,
) -> str:
    """CLI flag wins, then active-task.pipeline, then default (spec)."""
    if pipeline_arg and pipeline_arg not in {"", "auto"}:
        return normalize_pipeline_id(pipeline_arg)
    if active_task:
        marked = active_task.get("pipeline")
        if marked:
            return normalize_pipeline_id(str(marked))
    return normalize_pipeline_id(default)


def load_pipeline_schema(pipeline_id: str) -> dict:
    pipe_id = normalize_pipeline_id(pipeline_id)
    return load_schema_root()["pipelines"][pipe_id]


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

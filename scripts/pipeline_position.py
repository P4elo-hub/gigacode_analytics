#!/usr/bin/env python3
"""Where the pipeline is standing: last step + result.

Hook writes ``position`` into routing-state.json (mtime preserved so stale
detection still sees analyzer/artifact times). Router also falls back to the
last run-log row. Analyzer must not invent this.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from artifact_paths import routing_state_path
from pipeline_common import read_run_log
from pipeline_runtime import DEFAULT_PIPELINE_ID, load_pipeline_schema, outgoing_steps


def last_run_log_position(root: Path, slug: str) -> dict | None:
    """Last run-log row that names a pipeline step (ok, fail, or retry)."""
    for entry in reversed(read_run_log(root, slug)):
        step = str(entry.get("step") or "").strip()
        if step:
            return {
                "step": step,
                "result": str(entry.get("result") or "").strip() or "ok",
            }
    return None


def position_from_payload(payload: dict | None) -> dict | None:
    if not isinstance(payload, dict):
        return None
    raw = payload.get("position")
    if not isinstance(raw, dict):
        return None
    step = str(raw.get("step") or "").strip()
    if not step:
        return None
    return {
        "step": step,
        "result": str(raw.get("result") or "").strip() or "ok",
    }


def resolve_position(root: Path, slug: str, pipeline_id: str = DEFAULT_PIPELINE_ID) -> dict | None:
    del pipeline_id
    from pipeline_routing_state import load_routing_state

    payload, _err = load_routing_state(routing_state_path(root, slug), slug=slug)
    json_pos = position_from_payload(payload)
    if json_pos:
        return json_pos
    return last_run_log_position(root, slug)


def allowed_next_steps(schema: dict, position: dict | None) -> set[str] | None:
    """Outgoing graph edges; incomplete step may repeat itself. None = no constraint."""
    if not position:
        return None
    origin = str(position.get("step") or "").strip()
    if not origin:
        return None
    nodes = {str(node.get("id") or "") for node in schema.get("nodes") or []}
    if origin not in nodes:
        return None
    allowed = set(outgoing_steps(schema, origin))
    result = str(position.get("result") or "")
    if result and result != "ok":
        allowed.add(origin)
    return allowed


def record_position(root: Path, slug: str, step: str, result: str) -> bool:
    """Write position into routing-state.json without changing mtime."""
    path = routing_state_path(root, slug)
    if not path.is_file() or not step:
        return False
    from pipeline_routing_state import load_routing_state

    payload, error = load_routing_state(path, slug=slug)
    if payload is None or error:
        return False
    mtime = path.stat().st_mtime
    payload["position"] = {
        "step": step,
        "result": result or "ok",
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.utime(path, (mtime, mtime))
    return True


def graph_allowed_next(root: Path, slug: str, pipeline_id: str = DEFAULT_PIPELINE_ID) -> set[str] | None:
    schema = load_pipeline_schema(pipeline_id)
    return allowed_next_steps(schema, resolve_position(root, slug, pipeline_id))

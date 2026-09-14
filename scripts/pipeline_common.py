"""Shared pipeline registry helpers — scoped to the active pipeline pack."""

from __future__ import annotations

import json
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from agent_logs import load_manifest, run_log_path
from pipeline_pack import DEFAULT_PIPELINE_ID

REGISTRY_PATH = Path(__file__).resolve().parent / "generated" / "pipeline_registry.json"


@lru_cache(maxsize=1)
def load_pipeline_registry() -> dict:
    if not REGISTRY_PATH.is_file():
        raise FileNotFoundError(
            f"Missing {REGISTRY_PATH} — run: python3 scripts/pipeline_compile.py --apply"
        )
    payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid registry: {REGISTRY_PATH}")
    return payload


def known_pipeline_ids() -> tuple[str, ...]:
    data = load_pipeline_registry()
    pipes = data.get("pipelines")
    if isinstance(pipes, dict) and any(isinstance(v, dict) and "step_to_subagent" in v for v in pipes.values()):
        return tuple(pipes.keys())
    nodes = data.get("nodes") or {}
    if isinstance(nodes, dict) and nodes:
        return tuple(nodes.keys())
    return (DEFAULT_PIPELINE_ID,)


def registry_for(pipeline_id: str = DEFAULT_PIPELINE_ID) -> dict:
    data = load_pipeline_registry()
    pipes = data.get("pipelines") or {}
    if isinstance(pipes, dict) and pipeline_id in pipes:
        block = pipes[pipeline_id]
        if isinstance(block, dict) and "step_to_subagent" in block:
            return block
    if pipeline_id == DEFAULT_PIPELINE_ID:
        return data
    raise KeyError(f"unknown pipeline registry: {pipeline_id}")


def pipeline_gated_subagents(pipeline_id: str | None = None) -> frozenset[str]:
    data = load_pipeline_registry()
    pipes = data.get("pipelines") or {}
    if pipeline_id:
        try:
            return frozenset(registry_for(pipeline_id).get("gated_subagents") or [])
        except KeyError:
            pass
    gated: set[str] = set()
    if isinstance(pipes, dict):
        for block in pipes.values():
            if isinstance(block, dict) and "gated_subagents" in block:
                gated.update(block.get("gated_subagents") or [])
    if not gated:
        gated.update(data.get("gated_subagents") or [])
    return frozenset(gated)


def pipeline_restartable_steps(pipeline_id: str = DEFAULT_PIPELINE_ID) -> tuple[str, ...]:
    return tuple(registry_for(pipeline_id).get("restartable_steps") or [])


def pipeline_step_order(pipeline_id: str = DEFAULT_PIPELINE_ID) -> dict[str, int]:
    reg = registry_for(pipeline_id)
    order = reg.get("step_order")
    if isinstance(order, dict) and order:
        return {str(k): int(v) for k, v in order.items()}
    steps = pipeline_restartable_steps(pipeline_id)
    return {name: index for index, name in enumerate(steps)}


def pipeline_step_to_subagent(pipeline_id: str = DEFAULT_PIPELINE_ID) -> dict[str, str]:
    return dict(registry_for(pipeline_id).get("step_to_subagent") or {})


def pipeline_orchestrator_owned(pipeline_id: str = DEFAULT_PIPELINE_ID) -> frozenset[str]:
    return frozenset(registry_for(pipeline_id).get("orchestrator_owned") or [])


def pipeline_delegate_modes(pipeline_id: str = DEFAULT_PIPELINE_ID) -> dict:
    return dict(registry_for(pipeline_id).get("delegate_modes") or {})


# Backward-compat aliases: spec pack (legacy imports).
_spec = load_pipeline_registry()
STEP_TO_SUBAGENT: dict[str, str] = dict(
    (_spec.get("pipelines") or {}).get(DEFAULT_PIPELINE_ID, {}).get("step_to_subagent")
    or _spec.get("step_to_subagent")
    or {}
)
ORCHESTRATOR_OWNED_STEPS = frozenset(
    (_spec.get("pipelines") or {}).get(DEFAULT_PIPELINE_ID, {}).get("orchestrator_owned")
    or _spec.get("orchestrator_owned")
    or []
)


def command_to_step(command: str) -> str:
    token = command.strip().split()[0] if command.strip() else ""
    return token.lstrip("/") if token.startswith("/") else token


def step_to_command(step: str, slug: str) -> str:
    return f"/{step} {slug}"


def subagent_for_step(step: str, pipeline_id: str = DEFAULT_PIPELINE_ID) -> str:
    if step in pipeline_orchestrator_owned(pipeline_id):
        return ""
    return pipeline_step_to_subagent(pipeline_id).get(step, "")


def parse_run_log_ts(ts: str) -> float:
    normalized = ts.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized).timestamp()


def read_run_log(root: Path, slug: str, run_id: str | None = None) -> list[dict]:
    manifest = load_manifest(root, slug)
    rid = run_id or manifest.get("current_run")
    if not rid:
        return []
    path = run_log_path(root, slug, rid)
    if not path.is_file():
        return []
    entries: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def last_successful_step_ts(
    root: Path,
    slug: str,
    step: str,
    *,
    run_id: str | None = None,
) -> float | None:
    for entry in reversed(read_run_log(root, slug, run_id)):
        if entry.get("step") != step or entry.get("result") != "ok":
            continue
        ts = entry.get("ts")
        if not ts:
            continue
        try:
            return parse_run_log_ts(ts)
        except ValueError:
            continue
    return None

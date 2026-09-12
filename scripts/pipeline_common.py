"""Shared pipeline step mapping and run-log helpers."""

from __future__ import annotations

import json
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from agent_logs import load_manifest, run_log_path

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


def pipeline_gated_subagents() -> frozenset[str]:
    return frozenset(load_pipeline_registry()["gated_subagents"])


def pipeline_restartable_steps() -> tuple[str, ...]:
    return tuple(load_pipeline_registry()["restartable_steps"])


def pipeline_step_order() -> dict[str, int]:
    return dict(load_pipeline_registry()["step_order"])


_registry = load_pipeline_registry()
STEP_TO_SUBAGENT: dict[str, str] = dict(_registry["step_to_subagent"])

# write-feature is orchestrator-owned (spec-writer loop), not a single subagent task.
ORCHESTRATOR_OWNED_STEPS = frozenset(_registry["orchestrator_owned"])


def command_to_step(command: str) -> str:
    """`/check-feature slug` → `check-feature`."""
    token = command.strip().split()[0] if command.strip() else ""
    return token.lstrip("/") if token.startswith("/") else token


def step_to_command(step: str, slug: str) -> str:
    return f"/{step} {slug}"


def subagent_for_step(step: str) -> str:
    if step in ORCHESTRATOR_OWNED_STEPS:
        return ""
    return STEP_TO_SUBAGENT.get(step, "")


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

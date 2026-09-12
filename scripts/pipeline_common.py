"""Shared pipeline step mapping and run-log helpers."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from agent_logs import load_manifest, run_log_path

STEP_TO_SUBAGENT: dict[str, str] = {
    "find-context": "context-researcher",
    "check-feature": "spec-reviewer",
    "resolve-gaps": "gap-resolver",
    "challenge-feature": "spec-challenger",
    "resolve-challenges": "challenge-resolver",
    "check-feature-code": "code-auditor",
    "resolve-code-alignment": "alignment-resolver",
}

# write-feature is orchestrator-owned (spec-writer loop), not a single subagent task.
ORCHESTRATOR_OWNED_STEPS = frozenset({"write-feature"})


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

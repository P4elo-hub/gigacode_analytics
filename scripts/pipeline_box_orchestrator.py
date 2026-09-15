#!/usr/bin/env python3
"""PreToolUse: main-session orchestrator must not inspect the pipeline engine.

Subagents (hook input has agent_id) may read pack YAML. The conductor only runs
allowlisted runtime scripts and feature artifacts.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ALLOWED_RUNTIME_SCRIPTS = (
    "pipeline_delegate.py",
    "append_run_log.py",
    "ingest_session_telemetry.py",
    "pipeline_validate.py",
    "write_feature.py",
    "refresh_context.py",
)

ENGINE_MARKERS = (
    "pipelines/",
    "scripts/pipeline_",
    "scripts\\pipeline_",
    "scripts/PIPELINE-",
    "pipeline_schema.json",
    "routing_conditions.yaml",
    "pipeline_predicates",
    "pipeline_router.py",
    "pipeline_pack.py",
    "pipeline_edge_conditions",
    "pipeline_dispatch.py",
    "pipeline_set_active_task.py",
)

DENY_REASON = (
    "Оркестратор не читает движок. Выполни JSON pipeline_delegate.py. "
    "Повтор того же шага — не баг. Не открывай pipelines/ и scripts/pipeline_*."
)

_ALLOWED_SCRIPT_RE = re.compile(
    r"(?:[^\s'\"=]*)scripts[/\\](?:"
    + "|".join(re.escape(name) for name in ALLOWED_RUNTIME_SCRIPTS)
    + r")",
    re.IGNORECASE,
)


def parse_hook_input(raw: str) -> dict:
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def flatten_strings(obj: object) -> str:
    parts: list[str] = []

    def walk(value: object) -> None:
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(obj)
    return "\n".join(parts)


def strip_allowed_scripts(text: str) -> str:
    return _ALLOWED_SCRIPT_RE.sub("", text)


def inspects_engine(tool_input: object) -> bool:
    haystack = strip_allowed_scripts(flatten_strings(tool_input))
    lowered = haystack.lower()
    return any(marker.lower() in lowered for marker in ENGINE_MARKERS)


def is_subagent(hook_input: dict) -> bool:
    agent_id = hook_input.get("agent_id") or hook_input.get("agentId")
    return bool(str(agent_id or "").strip())


def allow_output(reason: str) -> dict:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": reason,
        }
    }


def deny_output(reason: str) -> dict:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def box_orchestrator_hook(hook_input: dict) -> dict:
    if is_subagent(hook_input):
        return allow_output("subagent may read pack YAML")
    tool_input = hook_input.get("tool_input")
    if inspects_engine(tool_input):
        return deny_output(DENY_REASON)
    return allow_output("orchestrator runtime path")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stdin-file", type=Path, help="Hook input file (default: stdin)")
    args = parser.parse_args(argv)

    if args.stdin_file:
        raw = args.stdin_file.read_text(encoding="utf-8")
    else:
        raw = sys.stdin.read()

    payload = box_orchestrator_hook(parse_hook_input(raw))
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

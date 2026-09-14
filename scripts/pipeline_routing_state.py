"""Routing-state JSON: schema, load, overlay onto status (no LLM, no next_step).

Analyzer writes the file; populate_status collectors call apply_routing_state.
Router still reads status fields only. Spec collectors stay until Phase 12.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from artifact_paths import routing_state_path

SCHEMA_VERSION = 1
PIPELINE_POC_ID = "routing-poc"
STALE_ID = "routing_state"
ROUTER_OWNED = frozenset(
    {
        "next_step",
        "next_command",
        "next_subagent",
        "next_reason",
        "orchestrator_mode",
        "must_continue",
        "ready",
        "pipeline_id",
        "slug",
    }
)
BOOL_FIELDS = frozenset(
    {
        "has_context",
        "has_spec",
        "has_decisions",
        "has_gaps_map",
        "has_challenges",
        "has_challenges_map",
        "has_alignment",
        "alignment_stale",
        "needs_check_feature",
    }
)
INT_FIELDS = frozenset(
    {
        "decisions_needs_answer",
        "decisions_pending_apply",
        "decisions_needs_answer_alignment",
        "decisions_pending_apply_alignment",
        "alignment_iteration",
        "critical_major_mismatch",
    }
)
LIST_FIELDS = frozenset({"open_gaps", "open_questions", "stale"})
STR_FIELDS = frozenset({"verdict", "needs_check_feature_reason"})
CHALLENGES_KEYS = (
    "open",
    "deferred",
    "resolved",
    "covered",
    "open_critical",
    "open_major",
)
STATUS_OVERLAY_FIELDS = tuple(
    sorted(BOOL_FIELDS | INT_FIELDS | LIST_FIELDS | STR_FIELDS | {"challenges"})
)

__all__ = [
    "SCHEMA_VERSION",
    "PIPELINE_POC_ID",
    "STALE_ID",
    "STATUS_OVERLAY_FIELDS",
    "routing_state_path",
    "example_payload",
    "validate_payload",
    "load_routing_state",
    "apply_routing_state_fields",
    "apply_routing_state_file",
    "overlay_collector",
]


def example_payload(slug: str, *, open_gaps: list[str] | None = None) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "slug": slug,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fields": {
            "has_context": True,
            "has_spec": True,
            "has_decisions": False,
            "has_gaps_map": False,
            "has_challenges": False,
            "has_challenges_map": False,
            "has_alignment": False,
            "decisions_needs_answer": 0,
            "decisions_pending_apply": 0,
            "decisions_needs_answer_alignment": 0,
            "decisions_pending_apply_alignment": 0,
            "open_gaps": list(open_gaps or []),
            "open_questions": [],
            "challenges": {key: 0 for key in CHALLENGES_KEYS},
            "verdict": "",
            "alignment_iteration": 0,
            "critical_major_mismatch": 0,
            "alignment_stale": False,
            "stale": [],
            "needs_check_feature": False,
            "needs_check_feature_reason": "",
        },
    }


def validate_payload(payload: Any, *, slug: str | None = None) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["routing-state must be a JSON object"]
    version = payload.get("schema_version")
    if version != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}, got {version!r}")
    if slug and payload.get("slug") not in (None, "", slug):
        errors.append(f"slug mismatch: file {payload.get('slug')!r} vs {slug!r}")
    fields = payload.get("fields")
    if not isinstance(fields, dict):
        errors.append("fields must be a mapping")
        return errors
    for key in ROUTER_OWNED:
        if key in fields:
            errors.append(f"fields must not set router-owned {key!r}")
    return errors


def load_routing_state(path: Path, *, slug: str | None = None) -> tuple[dict | None, str]:
    if not path.is_file():
        return None, "missing"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"invalid JSON: {exc}"
    errors = validate_payload(payload, slug=slug)
    if errors:
        return None, "; ".join(errors)
    return payload, ""


def _assign_challenges(status, value: dict) -> None:
    current = getattr(status, "challenges", None)
    if current is None:
        setattr(status, "challenges", SimpleNamespace(**{k: int(value.get(k, 0) or 0) for k in CHALLENGES_KEYS}))
        return
    for key in CHALLENGES_KEYS:
        if hasattr(current, key):
            setattr(current, key, int(value.get(key, 0) or 0))


def apply_routing_state_fields(status, fields: dict) -> None:
    for key, value in fields.items():
        if key in ROUTER_OWNED:
            continue
        if key == "challenges" and isinstance(value, dict):
            _assign_challenges(status, value)
            continue
        setattr(status, key, value)


def apply_routing_state_file(status, path: Path, *, slug: str | None = None) -> str:
    payload, error = load_routing_state(path, slug=slug)
    status.routing_state_invalid = bool(error)
    status.routing_state_error = error
    if payload is None:
        return error
    apply_routing_state_fields(status, payload.get("fields") or {})
    return ""


def overlay_collector(root: Path, task_id: str, status, paths: dict[str, Path]) -> None:
    """Pack collector: read routing_state artifact → status fields."""
    path = paths.get("routing_state") or routing_state_path(root, task_id)
    apply_routing_state_file(status, path, slug=task_id)

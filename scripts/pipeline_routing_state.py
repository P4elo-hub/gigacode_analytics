"""Routing-state JSON: schema, load, overlay onto status (no LLM, no next_step).

Analyzer writes the file; populate_status collectors call apply_routing_state.
Router still reads status fields only. Spec collectors stay until Phase 12.
"""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterator

from artifact_paths import routing_state_path

SCHEMA_VERSION = 1
PIPELINE_POC_ID = "routing-poc"
STALE_ID = "routing_state"
OVERLAY_ENV = "PIPELINE_ROUTING_STATE_OVERLAY"
REPLAY_ENV = "PIPELINE_ROUTING_STATE_REPLAY"
SPEC_STALE_VS = (
    "spec",
    "context",
    "decisions",
    "challenges",
    "alignment",
    "gaps_map",
    "challenges_map",
)
POC_STALE_VS = ("spec",)
ENGINE_RECOMPUTED_FIELDS = frozenset({"stale", "alignment_stale"})
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

_overlay_force: str | None = None
_replay_path: Path | None = None

__all__ = [
    "SCHEMA_VERSION",
    "PIPELINE_POC_ID",
    "STALE_ID",
    "SPEC_STALE_VS",
    "POC_STALE_VS",
    "STATUS_OVERLAY_FIELDS",
    "CHALLENGES_KEYS",
    "routing_state_path",
    "example_payload",
    "validate_payload",
    "load_routing_state",
    "apply_routing_state_fields",
    "apply_routing_state_file",
    "overlay_collector",
    "spec_overlay_collector",
    "overlay_context",
    "serialize_status_fields",
    "routing_state_is_stale",
    "add_routing_state_advice",
    "load_spec_routing_conditions",
    "default_replay_path",
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
        if key in ROUTER_OWNED or key in ENGINE_RECOMPUTED_FIELDS:
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


def _mtime(path: Path | None) -> float | None:
    if path is None or not path.is_file():
        return None
    return path.stat().st_mtime


def routing_state_is_stale(
    paths: dict[str, Path],
    *,
    stale_vs: tuple[str, ...] = SPEC_STALE_VS,
    routing_path: Path | None = None,
) -> bool:
    left = _mtime(routing_path or paths.get(STALE_ID))
    if left is None:
        return False
    for name in stale_vs:
        right = _mtime(paths.get(name))
        if right is not None and left < right:
            return True
    return False


def default_replay_path(root: Path, slug: str) -> Path:
    return root / "scripts" / "fixtures" / "routing_state_replay" / f"{slug}.json"


def load_spec_routing_conditions(root: Path | None = None) -> dict:
    """Parse shadow YAML keys without requiring PyYAML (folded scalars)."""
    from pipeline_pack import repo_root

    path = (root or repo_root()) / "pipelines" / "spec" / "routing_conditions.yaml"
    text = path.read_text(encoding="utf-8")
    fields: dict[str, dict] = {}
    stale_vs: list[str] = []
    validate_ids: list[str] = []
    section = ""
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if line == "status_fields:":
            section = "fields"
            continue
        if line == "stale_vs:":
            section = "stale_vs"
            continue
        if line == "validate_ids:":
            section = "validate_ids"
            continue
        if section == "fields" and line.startswith("  ") and not line.startswith("    ") and line.endswith(":"):
            name = line.strip().rstrip(":")
            if name and not name.startswith("-"):
                fields[name] = {}
            continue
        if section in {"stale_vs", "validate_ids"} and line.startswith("  - "):
            value = line.strip()[2:].strip()
            if section == "stale_vs":
                stale_vs.append(value)
            else:
                validate_ids.append(value)
            continue
        if section and not line.startswith(" "):
            section = ""
    return {"status_fields": fields, "stale_vs": stale_vs, "validate_ids": validate_ids}


@contextmanager
def overlay_context(*, mode: str | None = None, replay: Path | str | None = None) -> Iterator[None]:
    """Force spec overlay on/off and optionally read JSON from a replay file."""
    global _overlay_force, _replay_path
    prev_mode, prev_replay = _overlay_force, _replay_path
    if mode is not None:
        _overlay_force = mode
    if replay is not None:
        _replay_path = Path(replay)
    try:
        yield
    finally:
        _overlay_force = prev_mode
        _replay_path = prev_replay


def _env_overlay_mode() -> str | None:
    raw = os.environ.get(OVERLAY_ENV, "").strip().lower()
    if raw in ("0", "false", "off", "collectors", "a"):
        return "off"
    if raw in ("1", "true", "on", "overlay", "b"):
        return "on"
    return None


def _effective_routing_state_path(root: Path, task_id: str, paths: dict[str, Path]) -> Path:
    replay = _replay_path
    if replay is None:
        env_replay = os.environ.get(REPLAY_ENV, "").strip()
        replay = Path(env_replay) if env_replay else None
    if replay is not None:
        return replay
    return paths.get("routing_state") or routing_state_path(root, task_id)


def spec_overlay_should_apply(root: Path, task_id: str, paths: dict[str, Path]) -> bool:
    mode = _overlay_force or _env_overlay_mode()
    if mode == "off":
        return False
    if mode == "on":
        return True
    path = _effective_routing_state_path(root, task_id, paths)
    payload, error = load_routing_state(path, slug=task_id)
    if payload is None or error:
        return False
    return not routing_state_is_stale(paths, routing_path=path)


def spec_overlay_collector(root: Path, task_id: str, status, paths: dict[str, Path]) -> None:
    """Spec dual-run overlay. Live default: only when JSON is valid and fresh."""
    if not spec_overlay_should_apply(root, task_id, paths):
        return
    path = _effective_routing_state_path(root, task_id, paths)
    apply_routing_state_file(status, path, slug=task_id)


def serialize_status_fields(status) -> dict:
    fields: dict[str, Any] = {}
    for key in example_payload("x")["fields"]:
        if key == "challenges":
            ch = getattr(status, "challenges", None)
            fields["challenges"] = {
                name: int(getattr(ch, name, 0) or 0) if ch is not None else 0
                for name in CHALLENGES_KEYS
            }
            continue
        value = getattr(status, key, None)
        if key in BOOL_FIELDS:
            fields[key] = bool(value)
        elif key in INT_FIELDS:
            fields[key] = int(value or 0)
        elif key in LIST_FIELDS:
            fields[key] = list(value or [])
        elif key in STR_FIELDS:
            fields[key] = "" if value is None else str(value)
        else:
            fields[key] = value
    return fields


def add_routing_state_advice(
    root: Path,
    task_id: str,
    report,
    add,
    *,
    stale_vs: tuple[str, ...] = SPEC_STALE_VS,
    paths: dict[str, Path] | None = None,
) -> None:
    path = routing_state_path(root, task_id)
    if not path.is_file():
        add(
            report,
            id="routing-state-missing",
            severity="warn",
            title="Нет routing-state.json",
            detail=f"Ожидался {path.as_posix()}",
            fix="Запусти /analyze-routing — extra_advice, dispatch не блокируется.",
        )
        return
    _payload, error = load_routing_state(path, slug=task_id)
    if error:
        add(
            report,
            id="routing-state-missing",
            severity="warn",
            title="routing-state.json нечитаем",
            detail=error,
            fix="Перезапусти analyze-routing — JSON должен соответствовать schema_version 1.",
        )
        return
    if paths is None:
        from pipeline_status import resolve_artifact_paths

        paths = resolve_artifact_paths(root, task_id, "spec")
    if routing_state_is_stale(paths, stale_vs=stale_vs, routing_path=path):
        compared = ", ".join(stale_vs)
        add(
            report,
            id="routing-state-stale",
            severity="warn",
            title="routing-state.json устарел",
            detail=f"mtime routing-state старше {compared}",
            fix="Запусти /analyze-routing — extra_advice, dispatch не блокируется.",
        )

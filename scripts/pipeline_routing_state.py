"""Routing-state JSON: schema, load, overlay onto status (no LLM, no next_step).

Analyzer writes the file; populate_status overlay collector applies fields.
Router still reads status fields only. Spec live path is overlay (Phase 12).
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
# Artifact exists_as (has_spec, has_context, …) is re-applied from disk after
# overlay in populate_status — JSON cannot hide a file that is on disk.
# Top-level JSON metadata (hook/analyzer); router ignores.
SYNC_METADATA_KEYS = frozenset({"step_completion", "position", "routing_reports"})
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
        "decisions_needs_answer_gaps",
        "decisions_pending_apply_gaps",
        "decisions_needs_answer_challenges",
        "decisions_pending_apply_challenges",
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
    "SYNC_METADATA_KEYS",
    "load_routing_state_sync_config",
    "routing_state_sync_enabled",
    "stale_vs_for_pipeline",
    "sync_routing_state_after_step",
]


def example_payload(slug: str, *, open_gaps: list[str] | None = None) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "slug": slug,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "step_completion": {},
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
            "decisions_needs_answer_gaps": 0,
            "decisions_pending_apply_gaps": 0,
            "decisions_needs_answer_challenges": 0,
            "decisions_pending_apply_challenges": 0,
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
    completion = payload.get("step_completion")
    if completion is not None and not isinstance(completion, dict):
        errors.append("step_completion must be a mapping")
    position = payload.get("position")
    if position is not None:
        if not isinstance(position, dict) or not str(position.get("step") or "").strip():
            errors.append("position must be a mapping with step")
    reports = payload.get("routing_reports")
    if reports is not None:
        if not isinstance(reports, dict):
            errors.append("routing_reports must be a mapping")
        else:
            try:
                last_seq = int(reports.get("last_seq") or 0)
            except (TypeError, ValueError):
                errors.append("routing_reports.last_seq must be an integer")
            else:
                if last_seq < 0:
                    errors.append("routing_reports.last_seq must be non-negative")
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
    status.routing_state_invalid = bool(error) and error != "missing"
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
    """Phase 12: overlay is the spec live default. mode=off is tests/baseline only."""
    del root, task_id, paths
    mode = _overlay_force or _env_overlay_mode()
    if mode == "off":
        return False
    if mode == "on":
        return True
    try:
        from pipeline_status import load_status_spec

        spec = load_status_spec("spec")
    except Exception:
        return True
    collector_mode = str(spec.get("collector_mode") or "routing_state")
    return collector_mode == "routing_state"


def load_routing_state_sync_config(pipeline_id: str) -> dict | None:
    """Pack hook sync config when collector_mode is routing_state (authoring YAML)."""
    from pipeline_pack import load_pack, repo_root

    spec = load_pack(pipeline_id, repo_root()).get("status") or {}
    if str(spec.get("collector_mode") or "") != "routing_state":
        return None
    raw = spec.get("routing_state_sync")
    if raw is False:
        return None
    defaults: dict[str, Any] = {
        "skip_after_steps": ["analyze-routing"],
        "sync_after_steps": [],
    }
    if isinstance(raw, dict):
        return {**defaults, **raw}
    return defaults


def routing_state_sync_enabled(pipeline_id: str) -> bool:
    return load_routing_state_sync_config(pipeline_id) is not None


def stale_vs_for_pipeline(pipeline_id: str) -> tuple[str, ...]:
    """Artifact names whose mtime makes routing-state stale (pack YAML)."""
    from pipeline_pack import load_pack, repo_root

    pack = load_pack(pipeline_id, repo_root())
    rc = pack.get("routing_conditions") or {}
    vs = rc.get("stale_vs")
    if isinstance(vs, list) and vs:
        return tuple(str(item) for item in vs)
    rights: list[str] = []
    for rule in (pack.get("status") or {}).get("stale") or []:
        if not isinstance(rule, dict):
            continue
        if str(rule.get("id") or "") != STALE_ID:
            continue
        right = str(rule.get("right") or "")
        if right and right not in rights:
            rights.append(right)
    if rights:
        return tuple(rights)
    return POC_STALE_VS if pipeline_id == PIPELINE_POC_ID else SPEC_STALE_VS


def _hook_sync_allowed(cfg: dict, step: str) -> bool:
    if step in {str(item) for item in (cfg.get("skip_after_steps") or [])}:
        return False
    allowed = cfg.get("sync_after_steps")
    if not isinstance(allowed, list) or not allowed:
        return False
    return step in {str(item) for item in allowed}


def sync_routing_state_after_step(
    root: Path,
    slug: str,
    step: str,
    result: str,
    *,
    pipeline_id: str,
) -> bool:
    """Stamp routing-state.json after a gate step that did not mutate artifacts.

    Mutating steps are not synced: JSON stays older than files → stale →
    analyze-routing. If a listed gate step still left artifacts newer than JSON,
    skip the stamp so the analyzer runs.
    """
    cfg = load_routing_state_sync_config(pipeline_id)
    if cfg is None or result != "ok":
        return False
    if not _hook_sync_allowed(cfg, step):
        return False

    path = routing_state_path(root, slug)
    payload, error = load_routing_state(path, slug=slug)
    if payload is None or error:
        return False

    from pipeline_pack import load_pack_module
    from pipeline_status import resolve_artifact_paths

    paths = resolve_artifact_paths(root, slug, pipeline_id)
    if routing_state_is_stale(
        paths,
        stale_vs=stale_vs_for_pipeline(pipeline_id),
        routing_path=path,
    ):
        return False

    sync_mod = load_pack_module(pipeline_id, "routing_state_sync")
    if sync_mod is None or not callable(getattr(sync_mod, "refresh_fields", None)):
        return False

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    completion = dict(payload.get("step_completion") or {})
    completion[step] = now
    payload["step_completion"] = completion

    fields = payload.setdefault("fields", {})
    refreshed = sync_mod.refresh_fields(root, slug, paths, completion, dict(fields))
    if isinstance(refreshed, dict):
        fields.update(refreshed)

    payload["generated_at"] = now
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True


def spec_overlay_collector(root: Path, task_id: str, status, paths: dict[str, Path]) -> None:
    """Spec overlay: JSON fields, then Relates buckets from DECISIONS on disk.

    Leftover «отложено» markers stay in open_gaps. Apply/ask dispatch uses
    Relates (GAP-* vs CH-*), not «any pending-apply + any leftover marker».
    """
    if not spec_overlay_should_apply(root, task_id, paths):
        return
    path = _effective_routing_state_path(root, task_id, paths)
    apply_routing_state_file(status, path, slug=task_id)
    spec = paths.get("spec")
    if spec is not None and spec.is_file():
        from routing_state_baseline import deferred_gap_ids

        deferred = deferred_gap_ids(spec.read_text(encoding="utf-8"))
        if deferred:
            status.open_gaps = [
                gap_id for gap_id in (status.open_gaps or []) if gap_id not in deferred
            ]
    from routing_state_baseline import apply_decisions_table

    apply_decisions_table(status, paths)


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
    severity: str = "warn",
) -> None:
    path = routing_state_path(root, task_id)
    fix = "Delegate → task на routing-analyzer (step analyze-routing)."
    if not path.is_file():
        add(
            report,
            id="routing-state-missing",
            severity=severity,
            title="Нет routing-state.json",
            detail=f"Ожидался {path.as_posix()}",
            fix=fix,
        )
        return
    _payload, error = load_routing_state(path, slug=task_id)
    if error:
        add(
            report,
            id="routing-state-missing",
            severity=severity,
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
            severity=severity,
            title="routing-state.json устарел",
            detail=f"mtime routing-state старше {compared}",
            fix=fix,
        )

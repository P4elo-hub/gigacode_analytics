"""POC domain predicates: refresh analyzer vs overlay open_gaps vs ready."""

from __future__ import annotations

from pathlib import Path

from pipeline_routing_state import STALE_ID

PIPELINE_ID = "routing-poc"
DOMAIN_PREDICATE_NAMES = frozenset(
    {
        "routing_state_needs_refresh",
        "open_gaps",
        "routing_state_ready",
    }
)


def _routing_state_needs_refresh(_root: Path, _task_id: str, status) -> bool:
    if not getattr(status, "has_routing_state", False):
        return True
    if getattr(status, "routing_state_invalid", False):
        return True
    stale = getattr(status, "stale", None) or []
    return STALE_ID in stale


def _open_gaps(_root: Path, _task_id: str, status) -> bool:
    return bool(getattr(status, "open_gaps", None))


def _routing_state_ready(root: Path, task_id: str, status) -> bool:
    return not _routing_state_needs_refresh(root, task_id, status) and not _open_gaps(
        root, task_id, status
    )


PREDICATES = {
    "routing_state_needs_refresh": _routing_state_needs_refresh,
    "open_gaps": _open_gaps,
    "routing_state_ready": _routing_state_ready,
}


def reason_for_predicate(when: str, status) -> str:
    if when == "routing_state_needs_refresh":
        error = getattr(status, "routing_state_error", "") or ""
        if error and error != "missing":
            return f"routing-state невалиден ({error}) — нужен analyze-routing"
        if STALE_ID in (getattr(status, "stale", None) or []):
            return "routing-state.json устарел относительно SPEC — нужен analyze-routing"
        return "нет routing-state.json — нужен analyze-routing"
    if when == "open_gaps":
        gaps = getattr(status, "open_gaps", None) or []
        return f"незакрытые факты ({len(gaps)})"
    if when == "routing_state_ready":
        return "routing-state актуален, открытых фактов нет"
    return ""

"""POC validate: routing-state missing / stale (invalid JSON counts as missing)."""

from __future__ import annotations

from pathlib import Path

from pipeline_routing_state import STALE_ID, load_routing_state, routing_state_path


def extra_advice(root: Path, task_id: str, status, dispatch: dict, report, add) -> None:
    path = routing_state_path(root, task_id)
    if not path.is_file():
        add(
            report,
            id="routing-state-missing",
            severity="warn",
            title="Нет routing-state.json",
            detail=f"Ожидался {path.as_posix()}",
            fix="Delegate → task на routing-analyzer (step analyze-routing).",
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

    stale = getattr(status, "stale", None) or []
    if STALE_ID in stale:
        add(
            report,
            id="routing-state-stale",
            severity="warn",
            title="routing-state.json устарел",
            detail="mtime routing-state < SPEC",
            fix="Delegate → task на routing-analyzer (step analyze-routing).",
        )

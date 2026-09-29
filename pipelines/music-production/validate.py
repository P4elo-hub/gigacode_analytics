"""Pack-local validate notes for music-production. Does not change the router."""

from __future__ import annotations

from pathlib import Path


def extra_advice(root: Path, task_id: str, status, dispatch: dict, report, add) -> None:
    del root, task_id, status
    mode = dispatch.get("orchestrator_mode") or ""
    if mode == "ask_user":
        title = "Ожидается решение человека"
        if dispatch.get("next_step") == "revision-escalation":
            title = "Эскалация правки ждёт решения человека"
        add(
            report,
            id="music-human-gate",
            severity="ok",
            title=title,
            detail=dispatch.get("next_reason") or "",
            fix="Решение записывает человек. Агент не подставляет verdict и не увеличивает бюджет.",
        )
    if mode == "stopped":
        add(
            report,
            id="music-stopped",
            severity="warn",
            title="Трек остановлен",
            detail=dispatch.get("next_reason") or "",
            fix="Лимит паузы снимает человек. Сетевой retry не является новой попыткой.",
        )

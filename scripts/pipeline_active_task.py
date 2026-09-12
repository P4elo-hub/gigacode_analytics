"""Read/write orchestrator active-task marker for SubagentStop hooks."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from artifact_paths import feature_dir, workspace_root

ACTIVE_TASK_FILENAME = ".pipeline-active-task.json"
SKIP_SUBAGENTS = frozenset(
    {
        "session-telemetry-analyst",
        "spec-orchestrator",
        "calibration-orchestrator",
        "doc-reviewer",
    }
)


def active_task_path(root: Path) -> Path:
    return root / ACTIVE_TASK_FILENAME


def feature_active_task_path(root: Path, slug: str) -> Path:
    return feature_dir(root, slug) / ACTIVE_TASK_FILENAME


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_active_task_file(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def load_active_task(root: Path | None = None) -> dict | None:
    """Workspace-level marker (last delegate across all slugs)."""
    root = (root or workspace_root()).resolve()
    return _read_active_task_file(active_task_path(root))


def load_active_task_latest(root: Path) -> dict | None:
    """Best active-task marker: root if valid, else newest per-feature copy."""
    root_task = load_active_task(root)
    if root_task and root_task.get("slug"):
        found = load_active_task_for_slug(root, root_task["slug"])
        if found:
            return found

    latest: dict | None = None
    latest_ts: datetime | None = None
    from artifact_paths import list_feature_slugs

    for slug in list_feature_slugs(root):
        task = _read_active_task_file(feature_active_task_path(root, slug))
        if not task or task.get("slug") != slug:
            continue
        ts = parse_active_ts(task.get("started_at"))
        if latest is None or (ts and (latest_ts is None or ts >= latest_ts)):
            latest = task
            latest_ts = ts
    return latest


def parse_active_ts(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def load_active_task_for_slug(root: Path, slug: str) -> dict | None:
    """Active task for a feature: root marker if slug matches, else per-feature copy."""
    root = root.resolve()
    global_task = load_active_task(root)
    if global_task and global_task.get("slug") == slug:
        return global_task
    feature_task = _read_active_task_file(feature_active_task_path(root, slug))
    if feature_task and feature_task.get("slug") == slug:
        return feature_task
    return None


def save_active_task(
    root: Path,
    *,
    slug: str,
    step: str,
    subagent: str,
    cli: str = "qwen",
    pipeline: str = "spec",
    session: str = "",
    persistent: bool = False,
) -> dict:
    root = root.resolve()
    payload = {
        "slug": slug,
        "step": step,
        "subagent": subagent,
        "cli": cli,
        "pipeline": pipeline,
        "session": session or None,
        "started_at": utc_now_iso(),
        "persistent": persistent or None,
    }
    payload = {k: v for k, v in payload.items() if v is not None}
    path = active_task_path(root)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    feature_path = feature_active_task_path(root, slug)
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    feature_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def clear_active_task(root: Path, slug: str | None = None) -> None:
    root = root.resolve()
    path = active_task_path(root)
    if path.is_file():
        path.unlink()
    if slug:
        feature_path = feature_active_task_path(root, slug)
        if feature_path.is_file():
            feature_path.unlink()

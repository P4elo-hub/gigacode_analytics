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
    """Workspace-level marker only.

    Per-feature copies are ``load_active_task_for_slug``. Do not pick the newest
    leftover marker from another slug — that sent write-feature to
    ``pipeline-viewer-smoke`` after the BPH cycle marker was cleared.
    """
    root_task = load_active_task(root)
    if not root_task or not root_task.get("slug"):
        return None
    found = load_active_task_for_slug(root, str(root_task["slug"]))
    return found or root_task


def write_cycle_still_open(root: Path, slug: str, active: dict | None) -> bool:
    """True until assemble: part files remain, or result is missing/older than the cycle."""
    if not active or not active.get("persistent"):
        return False
    if (active.get("slug") or "") != slug:
        return False
    from inner_cycle import (
        cycle_artifacts_open,
        cycle_config_for_step,
        resolve_cycle_folder,
        resolve_cycle_out,
    )
    from pipeline_pack import DEFAULT_PIPELINE_ID

    pipeline_id = str(active.get("pipeline") or DEFAULT_PIPELINE_ID)
    step = str(active.get("step") or "")
    cycle = cycle_config_for_step(pipeline_id, step)
    if not cycle:
        if step != "write-feature":
            return False
        cycle = {
            "folder": "Feature-writing/{slug}",
            "out": "{slug}.md",
            "item_file": "{slug}.part-{param}.md",
        }
    folder = resolve_cycle_folder(root, slug, cycle)
    out = resolve_cycle_out(folder, slug, cycle)
    return cycle_artifacts_open(folder, out, slug, cycle, active.get("started_at"))


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
    started_at = utc_now_iso()
    if persistent:
        existing = load_active_task_for_slug(root, slug)
        if (
            existing
            and existing.get("persistent")
            and str(existing.get("step") or "") == step
            and str(existing.get("started_at") or "")
        ):
            started_at = str(existing["started_at"])
    payload = {
        "slug": slug,
        "step": step,
        "subagent": subagent,
        "cli": cli,
        "pipeline": pipeline,
        "session": session or None,
        "started_at": started_at,
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

"""Append-only, pack-neutral reports produced by completed pipeline agents."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pipeline_status import resolve_artifact_paths

REPORT_SCHEMA_VERSION = 1
REPORTS_DIRNAME = "routing-reports"
REPORTS_INDEX = "index.json"
REPORT_BLOCK_RE = re.compile(
    r"<routing-report>\s*(\{.*?\})\s*</routing-report>",
    re.DOTALL | re.IGNORECASE,
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def reports_index_path(
    root: Path,
    slug: str,
    pipeline_id: str,
    *,
    paths: dict[str, Path] | None = None,
) -> Path:
    artifact_paths = paths or resolve_artifact_paths(root, slug, pipeline_id)
    configured = artifact_paths.get("routing_reports")
    if configured is not None:
        return configured
    routing_state = artifact_paths.get("routing_state")
    task_root = routing_state.parent if routing_state is not None else root / slug
    return task_root / ".pipeline" / REPORTS_DIRNAME / REPORTS_INDEX


def _read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def load_index(path: Path) -> dict:
    payload = _read_json(path)
    if payload.get("schema_version") != REPORT_SCHEMA_VERSION:
        return {"schema_version": REPORT_SCHEMA_VERSION, "last_seq": 0, "events": []}
    events = payload.get("events")
    if not isinstance(events, list):
        events = []
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "last_seq": int(payload.get("last_seq") or 0),
        "events": [event for event in events if isinstance(event, dict)],
    }


def extract_report(message: str) -> tuple[dict | None, str]:
    match = REPORT_BLOCK_RE.search(message or "")
    if not match:
        return None, "missing routing-report block"
    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        return None, f"invalid routing-report JSON: {exc}"
    if not isinstance(payload, dict):
        return None, "routing-report must be a JSON object"
    return payload, ""


def _string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _artifacts(value: Any) -> list[dict]:
    if not isinstance(value, list):
        return []
    rows: list[dict] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            rows.append({"path": item.strip(), "action": "updated"})
        elif isinstance(item, dict) and str(item.get("path") or "").strip():
            rows.append(
                {
                    "path": str(item["path"]).strip(),
                    "action": str(item.get("action") or "updated").strip(),
                }
            )
    return rows


def normalize_report(
    payload: dict | None,
    *,
    slug: str,
    pipeline_id: str,
    step: str,
    subagent: str,
    result: str,
    cli: str,
    event_key: str,
    error: str = "",
) -> dict:
    source = payload if isinstance(payload, dict) else {}
    summary = str(source.get("summary") or "").strip()
    incomplete = not payload or bool(error) or not summary
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "seq": 0,
        "ts": utc_now_iso(),
        "event_key": event_key,
        "slug": slug,
        "pipeline_id": pipeline_id,
        "step": step,
        "subagent": subagent,
        "result": result,
        "cli": cli,
        "summary": summary,
        "artifacts": _artifacts(source.get("artifacts")),
        "outcomes": _string_list(source.get("outcomes") or source.get("outcome")),
        "remaining_work": _string_list(source.get("remaining_work")),
        "incomplete": incomplete,
        "capture_error": error or None,
    }


def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def append_report(index_path: Path, report: dict) -> tuple[dict, bool]:
    index = load_index(index_path)
    event_key = str(report.get("event_key") or "")
    for event in index["events"]:
        if event_key and event.get("event_key") == event_key:
            existing = _read_json(index_path.parent / str(event.get("file") or ""))
            return existing or report, False

    seq = int(index["last_seq"]) + 1
    stored = dict(report)
    stored["seq"] = seq
    safe_step = re.sub(r"[^a-zA-Z0-9._-]+", "-", str(stored.get("step") or "step")).strip("-")
    filename = f"{seq:06d}-{safe_step or 'step'}.json"
    _atomic_write_json(index_path.parent / filename, stored)
    index["last_seq"] = seq
    index["events"].append(
        {
            "seq": seq,
            "file": filename,
            "event_key": event_key,
            "ts": stored["ts"],
            "step": stored.get("step"),
            "incomplete": bool(stored.get("incomplete")),
        }
    )
    _atomic_write_json(index_path, index)
    return stored, True


def read_reports_after(index_path: Path, last_seq: int = 0) -> list[dict]:
    index = load_index(index_path)
    reports: list[dict] = []
    for event in index["events"]:
        seq = int(event.get("seq") or 0)
        if seq <= last_seq:
            continue
        report = _read_json(index_path.parent / str(event.get("file") or ""))
        if report:
            reports.append(report)
    return reports


def cursor_from_state(payload: dict | None) -> int:
    metadata = (payload or {}).get("routing_reports")
    if not isinstance(metadata, dict):
        return 0
    try:
        return max(0, int(metadata.get("last_seq") or 0))
    except (TypeError, ValueError):
        return 0


def reports_pending(index_path: Path, state_path: Path) -> bool:
    index = load_index(index_path)
    state = _read_json(state_path)
    return int(index.get("last_seq") or 0) > cursor_from_state(state)


def set_state_cursor(state_path: Path, *, last_seq: int, index_path: Path) -> bool:
    payload = _read_json(state_path)
    if not payload or not isinstance(payload.get("fields"), dict):
        return False
    try:
        relative_index = str(index_path.relative_to(state_path.parent))
    except ValueError:
        relative_index = str(index_path)
    payload["routing_reports"] = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "last_seq": max(0, int(last_seq)),
        "index": relative_index,
        "updated_at": utc_now_iso(),
    }
    _atomic_write_json(state_path, payload)
    return True

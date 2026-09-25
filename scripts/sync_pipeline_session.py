#!/usr/bin/env python3
"""Sync agent-logs from live Qwen/GigaCode session: ingest events + backfill run-log."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from agent_logs import (
    cli_projects_dir,
    default_cli_home,
    events_path,
    load_manifest,
    run_log_path,
)
from archive_subagent_passes import archive_linked_sessions, pack_schema_for_slug
from build_pipeline_graph import parse_iso_ts, subagent_to_step
from pipeline_validate import validate_slug, ValidationReport


def parse_iso_ts(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def session_chat_path(root: Path, session_id: str, cli: str) -> Path | None:
    projects = cli_projects_dir(default_cli_home(cli), root)
    chat = projects / "chats" / f"{session_id}.jsonl"
    return chat if chat.is_file() else None


def session_is_stale(root: Path, slug: str, *, cli: str = "qwen") -> tuple[bool, str]:
    """True if Qwen chat is newer than ingested events for current run."""
    manifest = load_manifest(root, slug)
    session_id = manifest.get("last_session_id") or ""
    run_id = manifest.get("current_run") or "run-001"
    if not session_id:
        return False, "no last_session_id"

    chat = session_chat_path(root, session_id, cli)
    if not chat:
        return False, f"chat missing for {session_id}"

    ev = events_path(root, slug, run_id)
    chat_mtime = chat.stat().st_mtime
    ev_mtime = ev.stat().st_mtime if ev.is_file() else 0.0
    if chat_mtime > ev_mtime + 0.5:
        return True, f"chat newer than events ({session_id})"
    return False, "up to date"


def run_ingest(root: Path, slug: str, *, cli: str, session_id: str | None) -> dict:
    cmd = [
        sys.executable,
        str(root / "scripts" / "ingest_session_telemetry.py"),
        slug,
        "--cli",
        cli,
    ]
    if session_id:
        cmd.extend(["--session", session_id])
    cmd.append("--copy-raw")
    proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "ingest failed")[:500])
    return json.loads(proc.stdout)


def _log_has_subagent_call(rows: list[dict], *, step: str, subagent: str, call_id: str) -> bool:
    needle = call_id or ""
    for row in rows:
        if row.get("step") != step or (row.get("subagent") or "") != subagent:
            continue
        note = row.get("note") or ""
        session = row.get("session") or ""
        if needle and (needle in note or needle in session):
            return True
    return False


def backfill_run_log_from_subagents(
    root: Path,
    slug: str,
    *,
    session_id: str,
    run_id: str,
    cli: str = "qwen",
) -> list[dict]:
    """Append run-log rows for completed subagents missing from SubagentStop hook."""
    projects = cli_projects_dir(default_cli_home(cli), root)
    sub_dir = projects / "subagents" / session_id
    if not sub_dir.is_dir():
        return []

    schema = pack_schema_for_slug(root, slug)
    log_path = run_log_path(root, slug, run_id)
    existing = read_jsonl(log_path)
    appended: list[dict] = []

    for meta_path in sorted(sub_dir.glob("*.meta.json")):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if meta.get("status") != "completed":
            continue

        subagent = meta.get("agentType") or meta.get("subagentName") or ""
        step = subagent_to_step(schema, subagent)
        if not step:
            continue

        call_id = meta.get("toolUseId") or meta.get("agentId") or meta_path.stem
        if _log_has_subagent_call(existing, step=step, subagent=subagent, call_id=call_id):
            continue

        started = meta.get("createdAt") or ""
        ended = meta.get("lastUpdatedAt") or started or ""
        ts = ended or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        description = (meta.get("description") or "")[:200]
        duration_sec = None
        start_dt = parse_iso_ts(started)
        end_dt = parse_iso_ts(ended)
        if start_dt and end_dt and end_dt > start_dt:
            duration_sec = round((end_dt - start_dt).total_seconds(), 1)
        record = {
            "ts": ts,
            "step": step,
            "subagent": subagent,
            "result": "ok",
            "attempt": 1,
            "session": session_id,
            "started_at": started or None,
            "ended_at": ended or None,
            "duration_sec": duration_sec,
            "call_id": call_id,
            "note": f"sync:{call_id}" + (f" · {description}" if description else ""),
            "source": "session-sync",
        }
        record = {k: v for k, v in record.items() if v is not None}
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        existing.append(record)
        appended.append(record)

    return appended


def save_validation(root: Path, slug: str, report: ValidationReport) -> None:
    path = root / "agent-logs" / slug / "validation.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sync_session(
    root: Path,
    slug: str,
    *,
    cli: str = "qwen",
    force: bool = False,
) -> dict:
    """Ingest Qwen session if stale; backfill run-log from completed subagents."""
    root = root.resolve()
    manifest = load_manifest(root, slug)
    session_id = manifest.get("last_session_id") or ""
    run_id = manifest.get("current_run") or "run-001"
    stale, reason = session_is_stale(root, slug, cli=cli)

    ingested = False
    if force or stale or not session_id:
        if not session_id:
            projects = cli_projects_dir(default_cli_home(cli), root)
            chats = sorted(
                (projects / "chats").glob("*.jsonl"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            session_id = chats[0].stem if chats else ""
        if session_id:
            run_ingest(root, slug, cli=cli, session_id=session_id)
            manifest = load_manifest(root, slug)
            session_id = manifest.get("last_session_id") or session_id
            run_id = manifest.get("current_run") or run_id
            ingested = True

    backfilled = backfill_run_log_from_subagents(
        root, slug, session_id=session_id, run_id=run_id, cli=cli
    )
    archived = archive_linked_sessions(
        root, slug, run_id=run_id, cli=cli, copy_raw=True
    )
    if ingested or backfilled or archived.get("passes_archived"):
        report = validate_slug(root, slug)
        save_validation(root, slug, report)

    return {
        "slug": slug,
        "session_id": session_id,
        "run_id": run_id,
        "ingested": ingested,
        "stale_reason": reason,
        "backfilled": backfilled,
        "archived": archived,
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slug")
    parser.add_argument("--cli", default="qwen", choices=("qwen", "gigacode"))
    parser.add_argument("--force", action="store_true", help="Ingest even if events look fresh")
    parser.add_argument("--workspace", type=Path)
    args = parser.parse_args()

    from agent_logs import resolve_slug_arg
    from artifact_paths import workspace_root

    root = (args.workspace or workspace_root()).resolve()
    slug = resolve_slug_arg(args.slug, root)
    result = sync_session(root, slug, cli=args.cli, force=args.force)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

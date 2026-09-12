"""Ingest OpenCode session tree from SQLite into canonical telemetry events."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from agent_logs import utc_now_iso
from telemetry_common import compute_metrics, event_from_tool_call, finalize_run

OPENCODE_TOOL_MAP = {
    "read": "read_file",
    "write": "write_file",
    "bash": "run_shell_command",
    "grep": "grep_search",
}


def default_opencode_db() -> Path:
    return Path.home() / ".local/share/opencode/opencode.db"


def ms_to_iso(ms: int | None) -> str:
    if ms is None:
        return utc_now_iso()
    return (
        datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}


def discover_root_session(
    conn: sqlite3.Connection,
    workspace: Path,
    session_id: str | None,
) -> dict:
    ws = str(workspace.resolve())
    if session_id:
        row = conn.execute("SELECT * FROM session WHERE id = ?", (session_id,)).fetchone()
        if not row:
            raise SystemExit(f"OpenCode session not found: {session_id}")
        return _row_to_dict(row)

    row = conn.execute(
        """
        SELECT * FROM session
        WHERE parent_id IS NULL AND directory = ?
        ORDER BY time_updated DESC
        LIMIT 1
        """,
        (ws,),
    ).fetchone()
    if row:
        return _row_to_dict(row)

    name = workspace.name.replace("_", "-")
    row = conn.execute(
        """
        SELECT * FROM session
        WHERE parent_id IS NULL
          AND (directory LIKE ? OR directory LIKE ? OR directory LIKE ?)
        ORDER BY time_updated DESC
        LIMIT 1
        """,
        (f"%{name}%", f"%{workspace.name}%", ws),
    ).fetchone()
    if not row:
        raise SystemExit(f"No OpenCode root session for workspace: {ws}")
    return _row_to_dict(row)


def collect_session_tree(conn: sqlite3.Connection, root_id: str) -> list[dict]:
    rows = [_row_to_dict(r) for r in conn.execute("SELECT * FROM session WHERE id = ?", (root_id,))]
    queue = [root_id]
    seen = {root_id}
    while queue:
        parent = queue.pop(0)
        for row in conn.execute("SELECT * FROM session WHERE parent_id = ?", (parent,)):
            data = _row_to_dict(row)
            sid = data["id"]
            if sid in seen:
                continue
            seen.add(sid)
            rows.append(data)
            queue.append(sid)
    return rows


def normalize_opencode_args(tool: str, inp: dict) -> tuple[str, dict]:
    if tool == "read":
        return "read_file", {"file_path": inp.get("filePath") or inp.get("path") or ""}
    if tool == "write":
        return "write_file", {"file_path": inp.get("filePath") or inp.get("path") or ""}
    if tool == "edit":
        return "edit", {"file_path": inp.get("filePath") or inp.get("path") or ""}
    if tool == "bash":
        return "run_shell_command", {"command": inp.get("command") or ""}
    if tool == "grep":
        return "grep_search", {"pattern": inp.get("pattern") or inp.get("query") or ""}
    if tool == "skill":
        return "skill", {"skill": inp.get("name") or inp.get("skill") or ""}
    if tool == "task":
        return "task", {
            "subagent_type": inp.get("subagent_type") or inp.get("agent") or "",
            "description": inp.get("description") or "",
        }
    if tool == "glob":
        return "glob", {"pattern": inp.get("pattern") or inp.get("glob_pattern") or ""}
    return tool, inp


def parse_session_parts(conn: sqlite3.Connection, session: dict, events: list[dict]) -> None:
    sid = session["id"]
    agent = session.get("agent") or "orchestrator"
    is_sidechain = bool(session.get("parent_id"))

    parts = conn.execute(
        """
        SELECT time_created, data FROM part
        WHERE session_id = ?
        ORDER BY time_created, id
        """,
        (sid,),
    ).fetchall()

    for time_created, data in parts:
        payload = json.loads(data)
        if payload.get("type") != "tool":
            continue
        tool = payload.get("tool") or "unknown"
        state = payload.get("state") or {}
        inp = state.get("input") or {}
        canonical_tool, args = normalize_opencode_args(tool, inp)
        events.append(
            event_from_tool_call(
                ts=ms_to_iso(time_created),
                session_id=sid,
                agent=agent,
                is_sidechain=is_sidechain,
                tool_name=canonical_tool,
                args=args,
            )
        )
        status = state.get("status")
        if status:
            events.append(
                {
                    "ts": ms_to_iso(time_created),
                    "type": "tool.result",
                    "session_id": sid,
                    "agent": agent,
                    "is_sidechain": is_sidechain,
                    "tool": canonical_tool,
                    "status": status,
                }
            )


def export_raw_opencode(
    conn: sqlite3.Connection,
    sessions: list[dict],
    dest: Path,
) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "sessions.json").write_text(
        json.dumps(sessions, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    parts_dir = dest / "parts"
    parts_dir.mkdir(exist_ok=True)
    for session in sessions:
        sid = session["id"]
        parts = [
            {"time_created": tc, "data": json.loads(data)}
            for tc, data in conn.execute(
                "SELECT time_created, data FROM part WHERE session_id = ? ORDER BY time_created, id",
                (sid,),
            )
        ]
        (parts_dir / f"{sid}.json").write_text(
            json.dumps(parts, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )


def ingest_opencode(
    *,
    root: Path,
    slug: str,
    run_id: str,
    workspace: Path,
    db_path: Path,
    session_id: str | None,
    copy_raw: bool,
) -> dict:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        root_session = discover_root_session(conn, workspace, session_id)
        root_id = root_session["id"]
        sessions = collect_session_tree(conn, root_id)
        subagent_count = sum(1 for s in sessions if s.get("parent_id"))

        events: list[dict] = [
            {
                "ts": utc_now_iso(),
                "type": "session.ingest",
                "session_id": root_id,
                "cli": "opencode",
                "slug": slug,
                "run_id": run_id,
            }
        ]

        for session in sessions:
            parse_session_parts(conn, session, events)

        events.sort(key=lambda e: e.get("ts") or "")

        metrics = compute_metrics(
            events,
            slug=slug,
            run_id=run_id,
            session_id=root_id,
            cli="opencode",
            subagent_count=subagent_count,
        )

        if copy_raw:
            from agent_logs import raw_dir

            export_raw_opencode(conn, sessions, raw_dir(root, slug, run_id) / "opencode")

        return finalize_run(
            root,
            slug,
            run_id,
            events,
            metrics,
            cli="opencode",
            session_id=root_id,
        )
    finally:
        conn.close()

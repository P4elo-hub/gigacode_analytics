#!/usr/bin/env python3
"""Ingest CLI session logs into agent-logs/<slug>/runs/<run-id>/."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from agent_logs import (
    cli_projects_dir,
    default_cli_home,
    raw_dir,
    resolve_run_id,
    resolve_slug_arg,
    utc_now_iso,
    workspace_root,
)
from artifact_paths import workspace_root as ws_root
from ingest_opencode import default_opencode_db, ingest_opencode
from telemetry_common import compute_metrics, event_from_tool_call, finalize_run


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slug", help="Feature slug or path to artifact")
    parser.add_argument("--session", help="CLI session id (default: latest for workspace)")
    parser.add_argument(
        "--cli",
        choices=("qwen", "gigacode", "opencode"),
        default="qwen",
        help="CLI that produced the session",
    )
    parser.add_argument("--cli-home", type=Path, help="Override ~/.qwen or ~/.gigacode")
    parser.add_argument(
        "--opencode-db",
        type=Path,
        help="Override ~/.local/share/opencode/opencode.db",
    )
    parser.add_argument("--run-id", default="auto", help="run-NNN or auto (uses current_run)")
    parser.add_argument("--new-run", action="store_true", help="Start a new run-NNN folder")
    parser.add_argument("--copy-raw", action="store_true", help="Copy source logs into raw/")
    parser.add_argument("--workspace", type=Path, help="Workspace root for agent-logs (default: auto-detect)")
    parser.add_argument(
        "--session-directory",
        type=Path,
        help="OpenCode: session.directory to match (default: workspace root)",
    )
    return parser.parse_args()


def discover_qwen_session(projects_dir: Path, session_id: str | None) -> tuple[str, Path]:
    chats = projects_dir / "chats"
    if not chats.is_dir():
        raise SystemExit(f"No chats directory: {chats}")

    if session_id:
        main = chats / f"{session_id}.jsonl"
        if not main.is_file():
            raise SystemExit(f"Session not found: {main}")
        return session_id, main

    candidates = sorted(chats.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise SystemExit(f"No session jsonl in {chats}")
    main = candidates[0]
    return main.stem, main


def iter_function_calls(record: dict):
    message = record.get("message") or {}
    for part in message.get("parts") or []:
        fc = part.get("functionCall")
        if fc:
            yield fc


def agent_name_from_file(path: Path) -> str:
    name = path.name
    if name.startswith("agent-"):
        name = name[len("agent-") :]
    if "-call_" in name:
        name = name.split("-call_")[0]
    return name


def parse_jsonl_file(
    path: Path,
    *,
    session_id: str,
    agent: str,
    is_sidechain: bool,
    events: list[dict],
) -> None:
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        ts = record.get("timestamp") or utc_now_iso()
        rtype = record.get("type")
        agent_id = record.get("agentId") or record.get("agentName") or agent

        if rtype == "assistant":
            for fc in iter_function_calls(record):
                name = fc.get("name") or "unknown"
                args = fc.get("args") or {}
                events.append(
                    event_from_tool_call(
                        ts=ts,
                        session_id=session_id,
                        agent=agent_id,
                        is_sidechain=is_sidechain,
                        tool_name=name,
                        args=args,
                    )
                )
        elif rtype == "tool_result":
            message = record.get("message") or {}
            for part in message.get("parts") or []:
                fr = part.get("functionResponse") or {}
                fname = fr.get("name")
                if fname:
                    events.append(
                        {
                            "ts": ts,
                            "type": "tool.result",
                            "session_id": session_id,
                            "agent": agent_id,
                            "is_sidechain": is_sidechain,
                            "tool": fname,
                        }
                    )


def ingest_qwen_gigacode(
    *,
    root: Path,
    slug: str,
    session_id: str,
    main_jsonl: Path,
    projects_dir: Path,
    run_id: str,
    cli: str,
    copy_raw: bool,
) -> dict:
    events: list[dict] = [
        {
            "ts": utc_now_iso(),
            "type": "session.ingest",
            "session_id": session_id,
            "cli": cli,
            "slug": slug,
            "run_id": run_id,
        }
    ]

    parse_jsonl_file(
        main_jsonl,
        session_id=session_id,
        agent="orchestrator",
        is_sidechain=False,
        events=events,
    )

    subagents_dir = projects_dir / "subagents" / session_id
    subagent_files: list[Path] = []
    if subagents_dir.is_dir():
        subagent_files = sorted(subagents_dir.glob("*.jsonl"))
        for sub_path in subagent_files:
            agent = agent_name_from_file(sub_path)
            parse_jsonl_file(
                sub_path,
                session_id=session_id,
                agent=agent,
                is_sidechain=True,
                events=events,
            )

    events.sort(key=lambda e: e.get("ts") or "")

    metrics = compute_metrics(
        events,
        slug=slug,
        run_id=run_id,
        session_id=session_id,
        cli=cli,
        subagent_count=len(subagent_files),
    )

    if copy_raw:
        dest = raw_dir(root, slug, run_id)
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(main_jsonl, dest / "main.jsonl")
        if subagent_files:
            sub_dest = dest / "subagents"
            sub_dest.mkdir(exist_ok=True)
            for sub_path in subagent_files:
                shutil.copy2(sub_path, sub_dest / sub_path.name)

    finalize_run(
        root,
        slug,
        run_id,
        events,
        metrics,
        cli=cli,
        session_id=session_id,
    )

    if copy_raw:
        from archive_subagent_passes import archive_session

        archive_session(
            root,
            slug,
            session_id=session_id,
            run_id=run_id,
            cli=cli,
            copy_raw=True,
        )

    return metrics


def main() -> None:
    args = parse_args()
    root = (args.workspace or ws_root()).resolve()
    slug = resolve_slug_arg(args.slug, root)
    run_id = resolve_run_id(root, slug, args.run_id, args.new_run)

    if args.cli == "opencode":
        db_path = (args.opencode_db or default_opencode_db()).expanduser()
        if not db_path.is_file():
            raise SystemExit(f"OpenCode database not found: {db_path}")
        session_dir = (args.session_directory or root).resolve()
        metrics = ingest_opencode(
            root=root,
            slug=slug,
            run_id=run_id,
            workspace=session_dir,
            db_path=db_path,
            session_id=args.session,
            copy_raw=args.copy_raw,
        )
        session_id = metrics["session_id"]
    else:
        cli_home = (args.cli_home or default_cli_home(args.cli)).expanduser()
        projects_dir = cli_projects_dir(cli_home, root)
        session_id, main_jsonl = discover_qwen_session(projects_dir, args.session)
        metrics = ingest_qwen_gigacode(
            root=root,
            slug=slug,
            session_id=session_id,
            main_jsonl=main_jsonl,
            projects_dir=projects_dir,
            run_id=run_id,
            cli=args.cli,
            copy_raw=args.copy_raw,
        )

    print(
        json.dumps(
            {"slug": slug, "run_id": run_id, "session_id": session_id, "metrics": metrics["counts"]},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

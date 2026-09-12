"""Archive Qwen/GigaCode subagent meta + raw jsonl into agent-logs (self-contained telemetry)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from agent_logs import (
    cli_projects_dir,
    default_cli_home,
    load_manifest,
    raw_dir,
    run_log_path,
    save_manifest,
    subagent_passes_path,
    slug_subagent_passes_path,
    utc_now_iso,
)
from build_pipeline_graph import load_schema, parse_iso_ts, subagent_to_step


def read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + ("\n" if rows else ""),
        encoding="utf-8",
    )


def _pass_key(row: dict) -> tuple[str, str]:
    return (str(row.get("session_id") or ""), str(row.get("call_id") or ""))


def merge_passes(existing: list[dict], new_rows: list[dict]) -> list[dict]:
    by_key = {_pass_key(row): row for row in existing if row.get("call_id")}
    for row in new_rows:
        key = _pass_key(row)
        if not key[1]:
            continue
        prev = by_key.get(key)
        if prev is None or (row.get("archived_at") or "") >= (prev.get("archived_at") or ""):
            by_key[key] = row
    merged = list(by_key.values())
    merged.sort(key=lambda r: r.get("started_at") or r.get("ended_at") or "")
    return merged


def collect_linked_session_ids(root: Path, slug: str, cli: str) -> set[str]:
    manifest = load_manifest(root, slug)
    sessions: set[str] = set()
    if manifest.get("last_session_id"):
        sessions.add(str(manifest["last_session_id"]))
    for sid in manifest.get("archived_sessions") or []:
        sessions.add(str(sid))

    for run_id in manifest.get("runs") or []:
        for row in read_jsonl(run_log_path(root, slug, run_id)):
            if row.get("session"):
                sessions.add(str(row["session"]))

    projects = cli_projects_dir(default_cli_home(cli), root)
    sub_root = projects / "subagents"
    if sub_root.is_dir():
        for sess_dir in sub_root.iterdir():
            if not sess_dir.is_dir():
                continue
            for meta_path in sess_dir.glob("*.meta.json"):
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    continue
                if slug in (meta.get("description") or ""):
                    sessions.add(sess_dir.name)
    return sessions


def _meta_to_pass(
    *,
    meta: dict,
    meta_path: Path,
    session_id: str,
    slug: str,
    run_id: str,
    cli: str,
    raw_meta_rel: str | None,
) -> dict | None:
    subagent = str(meta.get("agentType") or meta.get("subagentName") or "").strip()
    if not subagent:
        return None
    schema = load_schema()["pipelines"]["spec"]
    step = subagent_to_step(schema, subagent) or ""
    if not step:
        return None

    started = meta.get("createdAt") or ""
    ended = meta.get("lastUpdatedAt") or meta.get("createdAt") or ""
    start_dt = parse_iso_ts(started)
    end_dt = parse_iso_ts(ended)
    duration_sec = None
    if start_dt and end_dt and end_dt > start_dt:
        duration_sec = round((end_dt - start_dt).total_seconds(), 1)

    call_id = str(meta.get("toolUseId") or meta.get("agentId") or meta_path.stem)
    return {
        "call_id": call_id,
        "session_id": session_id,
        "agent_type": subagent,
        "step": step,
        "subagent": subagent,
        "started_at": started,
        "ended_at": ended,
        "duration_sec": duration_sec,
        "status": meta.get("status") or "unknown",
        "description": (meta.get("description") or "")[:240],
        "slug": slug,
        "run_id": run_id,
        "cli": cli,
        "archived_at": utc_now_iso(),
        "raw_meta_relpath": raw_meta_rel,
        "source": "agent-logs-archive",
    }


def archive_session(
    root: Path,
    slug: str,
    *,
    session_id: str,
    run_id: str,
    cli: str = "qwen",
    copy_raw: bool = True,
) -> list[dict]:
    """Copy subagent meta/jsonl for one CLI session into agent-logs; return new passes."""
    projects = cli_projects_dir(default_cli_home(cli), root)
    sub_dir = projects / "subagents" / session_id
    if not sub_dir.is_dir():
        return []

    session_linked = session_id in collect_linked_session_ids(root, slug, cli)
    archived: list[dict] = []
    raw_sub: Path | None = None
    if copy_raw:
        raw_sub = raw_dir(root, slug, run_id) / "subagents" / session_id
        raw_sub.mkdir(parents=True, exist_ok=True)
        main_chat = projects / "chats" / f"{session_id}.jsonl"
        if main_chat.is_file():
            dest_main = raw_dir(root, slug, run_id) / f"main-{session_id}.jsonl"
            shutil.copy2(main_chat, dest_main)

    for meta_path in sorted(sub_dir.glob("*.meta.json")):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue

        desc = meta.get("description") or ""
        if slug not in desc and not session_linked:
            continue

        raw_meta_rel: str | None = None
        if copy_raw and raw_sub is not None:
            shutil.copy2(meta_path, raw_sub / meta_path.name)
            raw_meta_rel = str(Path("raw") / "subagents" / session_id / meta_path.name)

            stem = meta_path.name.replace(".meta.json", "")
            jsonl_src = sub_dir / f"{stem}.jsonl"
            if jsonl_src.is_file():
                shutil.copy2(jsonl_src, raw_sub / jsonl_src.name)

        row = _meta_to_pass(
            meta=meta,
            meta_path=meta_path,
            session_id=session_id,
            slug=slug,
            run_id=run_id,
            cli=cli,
            raw_meta_rel=raw_meta_rel,
        )
        if row:
            archived.append(row)

    if not archived:
        return []

    slug_path = slug_subagent_passes_path(root, slug)
    write_jsonl(slug_path, merge_passes(read_jsonl(slug_path), archived))

    run_path = subagent_passes_path(root, slug, run_id)
    write_jsonl(run_path, merge_passes(read_jsonl(run_path), archived))

    manifest = load_manifest(root, slug)
    sessions = set(manifest.get("archived_sessions") or [])
    sessions.add(session_id)
    manifest["archived_sessions"] = sorted(sessions)
    manifest["last_archive"] = utc_now_iso()
    save_manifest(root, slug, manifest)
    return archived


def archive_linked_sessions(
    root: Path,
    slug: str,
    *,
    run_id: str,
    cli: str = "qwen",
    copy_raw: bool = True,
) -> dict:
    """Archive all Qwen sessions linked to slug (manifest, run-log, meta descriptions)."""
    session_ids = collect_linked_session_ids(root, slug, cli)
    all_passes: list[dict] = []
    by_session: dict[str, int] = {}
    for session_id in sorted(session_ids):
        rows = archive_session(
            root,
            slug,
            session_id=session_id,
            run_id=run_id,
            cli=cli,
            copy_raw=copy_raw,
        )
        by_session[session_id] = len(rows)
        all_passes.extend(rows)
    return {
        "slug": slug,
        "run_id": run_id,
        "sessions": len(session_ids),
        "passes_archived": len(all_passes),
        "by_session": by_session,
    }


def load_archived_passes(root: Path, slug: str) -> list[dict]:
    """All subagent passes for slug from agent-logs (canonical, no ~/.qwen)."""
    slug_path = slug_subagent_passes_path(root, slug)
    if slug_path.is_file():
        return read_jsonl(slug_path)

    manifest = load_manifest(root, slug)
    rows: list[dict] = []
    for run_id in manifest.get("runs") or []:
        rows.extend(read_jsonl(subagent_passes_path(root, slug, run_id)))
    return merge_passes([], rows)


def main() -> int:
    import argparse

    from agent_logs import resolve_run_id, resolve_slug_arg
    from artifact_paths import workspace_root

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slug")
    parser.add_argument("--run-id", default="auto")
    parser.add_argument("--cli", default="qwen")
    parser.add_argument("--session", help="Archive one session only")
    parser.add_argument("--no-raw", action="store_true")
    parser.add_argument("--workspace", type=Path)
    args = parser.parse_args()

    root = (args.workspace or workspace_root()).resolve()
    slug = resolve_slug_arg(args.slug, root)
    run_id = resolve_run_id(root, slug, args.run_id, False)
    cli = load_manifest(root, slug).get("cli") or args.cli

    if args.session:
        rows = archive_session(
            root,
            slug,
            session_id=args.session,
            run_id=run_id,
            cli=cli,
            copy_raw=not args.no_raw,
        )
        print(json.dumps({"passes": len(rows)}, ensure_ascii=False, indent=2))
    else:
        result = archive_linked_sessions(
            root,
            slug,
            run_id=run_id,
            cli=cli,
            copy_raw=not args.no_raw,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

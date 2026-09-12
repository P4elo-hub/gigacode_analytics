"""Paths and manifest helpers for agent-logs/<slug>/."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from artifact_paths import resolve_slug, workspace_root

AGENT_LOGS_DIR = "agent-logs"
RUN_DIR_PATTERN = re.compile(r"^run-(\d+)$")


def agent_logs_root(root: Path | None = None) -> Path:
    return (root or workspace_root()) / AGENT_LOGS_DIR


def agent_logs_dir(root: Path, slug: str) -> Path:
    return agent_logs_root(root) / slug


def manifest_path(root: Path, slug: str) -> Path:
    return agent_logs_dir(root, slug) / "manifest.json"


def run_log_path(root: Path, slug: str, run_id: str) -> Path:
    return run_dir(root, slug, run_id) / "run-log.jsonl"


def run_dir(root: Path, slug: str, run_id: str) -> Path:
    return agent_logs_dir(root, slug) / "runs" / run_id


def events_path(root: Path, slug: str, run_id: str) -> Path:
    return run_dir(root, slug, run_id) / "events.jsonl"


def metrics_path(root: Path, slug: str, run_id: str) -> Path:
    return run_dir(root, slug, run_id) / "metrics.json"


def anomalies_path(root: Path, slug: str, run_id: str) -> Path:
    return run_dir(root, slug, run_id) / "anomalies.md"


def raw_dir(root: Path, slug: str, run_id: str) -> Path:
    return run_dir(root, slug, run_id) / "raw"


def subagent_passes_path(root: Path, slug: str, run_id: str) -> Path:
    return run_dir(root, slug, run_id) / "subagent-passes.jsonl"


def slug_subagent_passes_path(root: Path, slug: str) -> Path:
    return agent_logs_dir(root, slug) / "subagent-passes.jsonl"


def encode_workspace_path(cwd: Path) -> str:
    """Match Qwen/GigaCode project dir naming (underscores → hyphens)."""
    return str(cwd.resolve()).replace("/", "-").replace("_", "-")


def cli_projects_dir(home: Path, cwd: Path) -> Path:
    encoded = encode_workspace_path(cwd)
    base = home / "projects" / encoded
    if base.is_dir():
        return base
    # Fallback: scan project dirs with matching suffix (legacy encodings)
    projects = home / "projects"
    if projects.is_dir():
        suffix = cwd.name.replace("_", "-")
        for child in projects.iterdir():
            if child.is_dir() and child.name.endswith(suffix):
                return child
    return base


def default_cli_home(cli: str) -> Path:
    if cli == "gigacode":
        return Path.home() / ".gigacode"
    if cli == "qwen":
        return Path.home() / ".qwen"
    raise ValueError(f"No CLI home for: {cli}")


def default_opencode_db() -> Path:
    return Path.home() / ".local/share/opencode/opencode.db"


def load_manifest(root: Path, slug: str) -> dict:
    path = manifest_path(root, slug)
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"slug": slug, "runs": [], "current_run": None}


def save_manifest(root: Path, slug: str, manifest: dict) -> None:
    path = manifest_path(root, slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def next_run_id(root: Path, slug: str) -> str:
    runs_root = agent_logs_dir(root, slug) / "runs"
    if not runs_root.is_dir():
        return "run-001"
    numbers = []
    for child in runs_root.iterdir():
        if child.is_dir():
            match = RUN_DIR_PATTERN.match(child.name)
            if match:
                numbers.append(int(match.group(1)))
    n = max(numbers, default=0) + 1
    return f"run-{n:03d}"


def resolve_run_id(root: Path, slug: str, run_id: str | None, new_run: bool) -> str:
    manifest = load_manifest(root, slug)
    if new_run or not manifest.get("current_run"):
        rid = next_run_id(root, slug)
        manifest.setdefault("runs", [])
        if rid not in manifest["runs"]:
            manifest["runs"].append(rid)
        manifest["current_run"] = rid
        save_manifest(root, slug, manifest)
        return rid
    if run_id and run_id != "auto":
        return run_id
    current = manifest.get("current_run")
    if current:
        return current
    return resolve_run_id(root, slug, None, new_run=True)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def resolve_slug_arg(raw: str, root: Path) -> str:
    slug = resolve_slug(raw, root)
    if not slug:
        raise SystemExit(f"Cannot resolve slug from: {raw!r}")
    return slug

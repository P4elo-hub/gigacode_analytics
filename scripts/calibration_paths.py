"""Paths for Calibration/<slug>/ meta-pipeline artifacts."""

from __future__ import annotations

import json
import re
from pathlib import Path

from agent_logs import load_manifest as load_agent_manifest
from artifact_paths import (
    alignment_path,
    challenges_map_path,
    challenges_path,
    context_doc_path,
    decisions_path,
    gaps_map_path,
    resolve_slug,
    spec_path,
    workspace_root,
)

CALIBRATION_DIR = "Calibration"
RUN_PATTERN = re.compile(r"^run-(\d+)$")

SNAPSHOT_FILES = (
    ("spec", lambda r, s: spec_path(r, s)),
    ("decisions", lambda r, s: decisions_path(r, s)),
    ("gaps_map", lambda r, s: gaps_map_path(r, s)),
    ("challenges", lambda r, s: challenges_path(r, s)),
    ("challenges_map", lambda r, s: challenges_map_path(r, s)),
    ("alignment", lambda r, s: alignment_path(r, s)),
)


def calibration_root(root: Path | None = None) -> Path:
    return (root or workspace_root()) / CALIBRATION_DIR


def calibration_slug_dir(root: Path, slug: str) -> Path:
    return calibration_root(root) / slug


def calibration_manifest_path(root: Path, slug: str) -> Path:
    return calibration_slug_dir(root, slug) / "manifest.json"


def calibration_run_dir(root: Path, slug: str, run_id: str) -> Path:
    return calibration_slug_dir(root, slug) / "runs" / run_id


def baseline_dir(root: Path, slug: str, run_id: str) -> Path:
    return calibration_run_dir(root, slug, run_id) / "baseline"


def gold_dir(root: Path, slug: str, run_id: str) -> Path:
    return calibration_run_dir(root, slug, run_id) / "gold"


def review_dir(root: Path, slug: str, run_id: str) -> Path:
    return calibration_run_dir(root, slug, run_id) / "review"


def proposals_dir(root: Path, slug: str, run_id: str) -> Path:
    return calibration_run_dir(root, slug, run_id) / "proposals"


def rerun_dir(root: Path, slug: str, run_id: str) -> Path:
    return calibration_run_dir(root, slug, run_id) / "rerun"


def inputs_lock_path(root: Path, slug: str, run_id: str) -> Path:
    return calibration_run_dir(root, slug, run_id) / "inputs.lock.json"


def human_review_path(root: Path, slug: str, run_id: str) -> Path:
    return review_dir(root, slug, run_id) / "human-review.md"


def delta_analysis_path(root: Path, slug: str, run_id: str) -> Path:
    return review_dir(root, slug, run_id) / "delta-analysis.md"


def delta_summary_path(root: Path, slug: str, run_id: str) -> Path:
    return review_dir(root, slug, run_id) / "delta-summary.json"


def context_gaps_path(root: Path, slug: str, run_id: str) -> Path:
    return review_dir(root, slug, run_id) / "context-gaps.md"


def context_gaps_json_path(root: Path, slug: str, run_id: str) -> Path:
    return review_dir(root, slug, run_id) / "context-gaps.json"


def proposals_table_path(root: Path, slug: str, run_id: str) -> Path:
    return proposals_dir(root, slug, run_id) / "proposals.md"


def scorecard_path(root: Path, slug: str, run_id: str) -> Path:
    return calibration_run_dir(root, slug, run_id) / "scorecard.json"


def rerun_feature_dir(root: Path, slug: str, run_id: str) -> Path:
    return rerun_dir(root, slug, run_id) / "Feature-writing" / slug


def resolve_slug_arg(raw: str, root: Path) -> str:
    slug = resolve_slug(raw, root)
    if not slug:
        raise SystemExit(f"Cannot resolve slug from: {raw!r}")
    return slug


def load_calibration_manifest(root: Path, slug: str) -> dict:
    path = calibration_manifest_path(root, slug)
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"slug": slug, "runs": [], "current_run": None}


def save_calibration_manifest(root: Path, slug: str, manifest: dict) -> None:
    path = calibration_manifest_path(root, slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def next_calibration_run_id(root: Path, slug: str) -> str:
    runs_root = calibration_slug_dir(root, slug) / "runs"
    if not runs_root.is_dir():
        return "run-001"
    numbers = []
    for child in runs_root.iterdir():
        if child.is_dir():
            match = RUN_PATTERN.match(child.name)
            if match:
                numbers.append(int(match.group(1)))
    return f"run-{max(numbers, default=0) + 1:03d}"


def resolve_calibration_run_id(
    root: Path, slug: str, run_id: str | None, new_run: bool
) -> str:
    manifest = load_calibration_manifest(root, slug)
    if new_run or not manifest.get("current_run"):
        rid = next_calibration_run_id(root, slug)
        manifest.setdefault("runs", [])
        if rid not in manifest["runs"]:
            manifest["runs"].append(rid)
        manifest["current_run"] = rid
        save_calibration_manifest(root, slug, manifest)
        return rid
    if run_id and run_id != "auto":
        return run_id
    current = manifest.get("current_run")
    if current:
        return current
    return resolve_calibration_run_id(root, slug, None, new_run=True)


def baseline_spec_path(root: Path, slug: str, run_id: str) -> Path:
    return baseline_dir(root, slug, run_id) / f"{slug}.md"


def gold_spec_path(root: Path, slug: str, run_id: str) -> Path:
    return gold_dir(root, slug, run_id) / f"{slug}.md"


def file_hash(path: Path) -> str | None:
    if not path.is_file():
        return None
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def link_agent_logs_run(root: Path, slug: str) -> dict:
    agent = load_agent_manifest(root, slug)
    return {
        "agent_logs_run": agent.get("current_run"),
        "agent_logs_session": agent.get("last_session_id"),
        "agent_logs_cli": agent.get("cli"),
    }

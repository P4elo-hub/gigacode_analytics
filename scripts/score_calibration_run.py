#!/usr/bin/env python3
"""Score calibration run: baseline vs gold vs optional rerun spec."""

from __future__ import annotations

import argparse
import difflib
import json
from pathlib import Path

from agent_logs import load_manifest as load_agent_manifest, metrics_path as agent_metrics_path
from artifact_paths import workspace_root
from calibration_paths import (
    baseline_spec_path,
    context_gaps_json_path,
    gold_spec_path,
    resolve_calibration_run_id,
    resolve_slug_arg,
    rerun_feature_dir,
    scorecard_path,
)


def similarity(a: Path, b: Path) -> float | None:
    if not a.is_file() or not b.is_file():
        return None
    return round(difflib.SequenceMatcher(None, a.read_text(encoding="utf-8"), b.read_text(encoding="utf-8")).ratio(), 4)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slug")
    parser.add_argument("--run-id", default="auto")
    parser.add_argument("--workspace", type=Path)
    args = parser.parse_args()

    root = (args.workspace or workspace_root()).resolve()
    slug = resolve_slug_arg(args.slug, root)
    run_id = resolve_calibration_run_id(root, slug, args.run_id, new_run=False)

    gold = gold_spec_path(root, slug, run_id)
    baseline = baseline_spec_path(root, slug, run_id)
    rerun_spec = rerun_feature_dir(root, slug, run_id) / f"{slug}.md"

    agent_manifest = load_agent_manifest(root, slug)
    agent_run = agent_manifest.get("current_run")
    metrics_before = None
    if agent_run:
        mp = agent_metrics_path(root, slug, agent_run)
        if mp.is_file():
            metrics_before = json.loads(mp.read_text(encoding="utf-8"))

    ctx_gaps_path = context_gaps_json_path(root, slug, run_id)
    ctx_counts = None
    if ctx_gaps_path.is_file():
        ctx_counts = json.loads(ctx_gaps_path.read_text(encoding="utf-8")).get("counts")

    scorecard = {
        "slug": slug,
        "calibration_run_id": run_id,
        "similarity_baseline_vs_gold": similarity(baseline, gold),
        "similarity_rerun_vs_gold": similarity(rerun_spec, gold) if rerun_spec.is_file() else None,
        "has_rerun_spec": rerun_spec.is_file(),
        "agent_logs_run": agent_run,
        "skill_loads": (metrics_before or {}).get("counts", {}).get("skill_loads"),
        "anomaly_count": len((metrics_before or {}).get("anomalies") or []),
        "context_gaps": ctx_counts,
    }

    scorecard_path(root, slug, run_id).parent.mkdir(parents=True, exist_ok=True)
    scorecard_path(root, slug, run_id).write_text(
        json.dumps(scorecard, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(scorecard, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

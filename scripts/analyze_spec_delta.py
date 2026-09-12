#!/usr/bin/env python3
"""Deterministic baseline vs gold spec diff → delta-analysis.md + delta-summary.json."""

from __future__ import annotations

import argparse
import difflib
import json
import re
from pathlib import Path

from artifact_paths import workspace_root
from calibration_paths import (
    baseline_spec_path,
    delta_analysis_path,
    delta_summary_path,
    gold_spec_path,
    resolve_calibration_run_id,
    resolve_slug_arg,
)

SECTION_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slug")
    parser.add_argument("--run-id", default="auto")
    parser.add_argument("--workspace", type=Path)
    return parser.parse_args()


def split_sections(text: str) -> dict[str, str]:
    sections: dict[str, str] = {"__preamble__": ""}
    current = "__preamble__"
    lines = text.splitlines()
    buf: list[str] = []
    for line in lines:
        match = SECTION_RE.match(line)
        if match and len(match.group(1)) <= 3:
            sections[current] = "\n".join(buf).strip()
            current = match.group(2).strip()
            buf = [line]
        else:
            buf.append(line)
    sections[current] = "\n".join(buf).strip()
    return sections


def main() -> None:
    args = parse_args()
    root = (args.workspace or workspace_root()).resolve()
    slug = resolve_slug_arg(args.slug, root)
    run_id = resolve_calibration_run_id(root, slug, args.run_id, new_run=False)

    baseline_path = baseline_spec_path(root, slug, run_id)
    gold_path = gold_spec_path(root, slug, run_id)
    if not baseline_path.is_file():
        raise SystemExit(f"Baseline missing: {baseline_path}. Run snapshot_baseline.py first.")
    if not gold_path.is_file():
        raise SystemExit(f"Gold missing: {gold_path}. Run sync_gold_spec.py after your edits.")

    baseline = baseline_path.read_text(encoding="utf-8")
    gold = gold_path.read_text(encoding="utf-8")

    base_lines = baseline.splitlines(keepends=True)
    gold_lines = gold.splitlines(keepends=True)
    unified = list(
        difflib.unified_diff(base_lines, gold_lines, fromfile="baseline", tofile="gold", n=2)
    )

    base_secs = split_sections(baseline)
    gold_secs = split_sections(gold)
    all_keys = sorted(set(base_secs) | set(gold_secs))
    changed_sections = []
    for key in all_keys:
        if key == "__preamble__":
            continue
        b = base_secs.get(key, "")
        g = gold_secs.get(key, "")
        if b != g:
            ratio = difflib.SequenceMatcher(None, b, g).ratio()
            changed_sections.append(
                {
                    "section": key,
                    "baseline_chars": len(b),
                    "gold_chars": len(g),
                    "similarity": round(ratio, 3),
                }
            )

    summary = {
        "slug": slug,
        "run_id": run_id,
        "baseline_lines": len(base_lines),
        "gold_lines": len(gold_lines),
        "line_delta": len(gold_lines) - len(base_lines),
        "changed_sections": changed_sections,
        "unified_diff_lines": len(unified),
    }

    lines = [
        f"# Delta analysis — {slug} / {run_id}",
        "",
        f"- baseline: `{baseline_path.name}`",
        f"- gold: `{gold_path.name}`",
        f"- changed sections: {len(changed_sections)}",
        f"- line delta: {summary['line_delta']:+d}",
        "",
        "## Sections changed",
        "",
    ]
    if not changed_sections:
        lines.append("No section-level changes detected.")
    else:
        lines.append("| Section | Similarity | Baseline chars | Gold chars |")
        lines.append("|---------|------------|----------------|------------|")
        for item in changed_sections:
            lines.append(
                f"| {item['section']} | {item['similarity']} | {item['baseline_chars']} | {item['gold_chars']} |"
            )

    lines.extend(["", "## Unified diff (excerpt)", ""])
    excerpt = unified[:200]
    if len(unified) > 200:
        lines.append(f"_Truncated: {len(unified)} lines total._")
    lines.append("```diff")
    lines.extend(line.rstrip("\n") for line in excerpt)
    lines.append("```")

    review = delta_analysis_path(root, slug, run_id)
    review.parent.mkdir(parents=True, exist_ok=True)
    review.write_text("\n".join(lines) + "\n", encoding="utf-8")
    delta_summary_path(root, slug, run_id).write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Scaffold context-gap analysis: was the agent missing sources, not skill?"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from artifact_paths import context_doc_path, workspace_root
from calibration_paths import (
    baseline_spec_path,
    context_gaps_json_path,
    context_gaps_path,
    delta_summary_path,
    gold_spec_path,
    human_review_path,
    resolve_calibration_run_id,
    resolve_slug_arg,
)

SECTION_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
WORD_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9_-]{5,}")
REV_CAUSE_RE = re.compile(
    r"^##\s+(REV-\d+).*?\n(?:.*?\n)*?- section:\s*(.+?)\s*\n(?:.*?\n)*?- cause:\s*(context-gap|skill-gap|hybrid|unclear)",
    re.MULTILINE | re.IGNORECASE,
)
SOURCE_EXTS = {".java", ".md", ".proto", ".yml", ".yaml", ".xml", ".json", ".sql", ".kt"}
TEXT_LIMIT = 400_000


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


def added_lines(baseline: str, gold: str) -> list[str]:
    base_set = {line.strip() for line in baseline.splitlines() if line.strip()}
    added: list[str] = []
    for line in gold.splitlines():
        stripped = line.strip()
        if stripped and stripped not in base_set:
            added.append(stripped)
    return added


def keywords(text: str, limit: int = 8) -> list[str]:
    seen: set[str] = set()
    tokens: list[str] = []
    for token in WORD_RE.findall(text):
        key = token.lower()
        if key in seen:
            continue
        seen.add(key)
        tokens.append(token)
        if len(tokens) >= limit:
            break
    return tokens


def iter_source_files(root: Path, subdir: str) -> list[Path]:
    base = root / subdir
    if not base.is_dir():
        return []
    files: list[Path] = []
    for path in base.rglob("*"):
        if path.is_file() and path.suffix.lower() in SOURCE_EXTS:
            files.append(path)
    return files


def search_files(files: list[Path], token: str) -> list[str]:
    hits: list[str] = []
    needle = token.lower()
    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")[:TEXT_LIMIT]
        except OSError:
            continue
        if needle in text.lower():
            hits.append(str(path))
            if len(hits) >= 5:
                break
    return hits


def inventory_sources(root: Path, slug: str) -> dict:
    repos = root / "repositories"
    analytics = root / "analytics"
    ctx = context_doc_path(root, slug)
    repo_dirs = sorted(p.name for p in repos.iterdir() if p.is_dir()) if repos.is_dir() else []
    analytics_files = iter_source_files(root, "analytics")
    repo_files = iter_source_files(root, "repositories")
    return {
        "repositories_present": repos.is_dir(),
        "repository_count": len(repo_dirs),
        "repository_names": repo_dirs[:30],
        "analytics_present": analytics.is_dir(),
        "analytics_file_count": len(analytics_files),
        "repository_file_count": len(repo_files),
        "context_doc_present": ctx.is_file(),
        "context_doc": str(ctx) if ctx.is_file() else None,
        "_repo_files": repo_files,
        "_analytics_files": analytics_files,
        "_context_path": ctx,
    }


def parse_human_review_causes(path: Path) -> dict[str, dict]:
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    mapping: dict[str, dict] = {}
    for match in REV_CAUSE_RE.finditer(text):
        rev_id, section, cause = match.group(1), match.group(2).strip(), match.group(3).lower()
        mapping[section] = {"rev_id": rev_id, "cause": cause}
    return mapping


def gap_type_from_hits(repo_hits: list[str], analytics_hits: list[str], ctx_hit: bool) -> str:
    if not repo_hits and not analytics_hits and not ctx_hit:
        return "missing-source"
    if not repo_hits and analytics_hits:
        return "missing-repository"
    if repo_hits or analytics_hits or ctx_hit:
        return "skill-gap-candidate"
    return "unclear"


def main() -> None:
    args = parse_args()
    root = (args.workspace or workspace_root()).resolve()
    slug = resolve_slug_arg(args.slug, root)
    run_id = resolve_calibration_run_id(root, slug, args.run_id, new_run=False)

    baseline_path = baseline_spec_path(root, slug, run_id)
    gold_path = gold_spec_path(root, slug, run_id)
    if not baseline_path.is_file() or not gold_path.is_file():
        raise SystemExit("Baseline and gold required. Run snapshot + sync_gold first.")

    baseline = baseline_path.read_text(encoding="utf-8")
    gold = gold_path.read_text(encoding="utf-8")
    base_secs = split_sections(baseline)
    gold_secs = split_sections(gold)

    summary_path = delta_summary_path(root, slug, run_id)
    changed = []
    if summary_path.is_file():
        changed = json.loads(summary_path.read_text(encoding="utf-8")).get("changed_sections") or []
    else:
        changed = [
            {"section": key}
            for key in sorted(set(base_secs) | set(gold_secs))
            if key != "__preamble__" and base_secs.get(key, "") != gold_secs.get(key, "")
        ]

    inventory = inventory_sources(root, slug)
    rev_causes = parse_human_review_causes(human_review_path(root, slug, run_id))
    ctx_text = ""
    if inventory["_context_path"].is_file():
        ctx_text = inventory["_context_path"].read_text(encoding="utf-8", errors="ignore")[:TEXT_LIMIT]

    gaps: list[dict] = []
    skill_candidates: list[dict] = []
    gap_num = 0
    skill_num = 0

    for item in changed:
        section = item["section"]
        added = added_lines(base_secs.get(section, ""), gold_secs.get(section, ""))
        significant = [line for line in added if len(line) >= 24][:6]
        if not significant:
            continue

        sample = "\n".join(significant[:3])
        tokens = keywords(sample)
        repo_hits: list[str] = []
        analytics_hits: list[str] = []
        ctx_hit = False
        for token in tokens[:5]:
            repo_hits.extend(search_files(inventory["_repo_files"], token))
            analytics_hits.extend(search_files(inventory["_analytics_files"], token))
            if ctx_text and token.lower() in ctx_text.lower():
                ctx_hit = True
        repo_hits = sorted(set(repo_hits))[:5]
        analytics_hits = sorted(set(analytics_hits))[:5]

        rev = rev_causes.get(section, {})
        cause = rev.get("cause")
        inferred = gap_type_from_hits(repo_hits, analytics_hits, ctx_hit)
        if cause == "context-gap":
            gap_type = "missing-source"
            confidence = "high"
        elif cause == "skill-gap":
            gap_type = "skill-gap-candidate"
            confidence = "high"
        elif cause == "hybrid":
            gap_type = "hybrid"
            confidence = "medium"
        else:
            gap_type = inferred
            confidence = "high" if gap_type == "missing-source" else "medium"

        entry = {
            "section": section,
            "sample_added": sample[:500],
            "keywords": tokens,
            "repository_hits": repo_hits,
            "analytics_hits": analytics_hits,
            "context_doc_hit": ctx_hit,
            "linked_rev": rev.get("rev_id"),
            "user_cause": cause,
            "inferred_type": gap_type,
            "confidence": confidence,
        }

        if gap_type in {"missing-source", "missing-repository", "hybrid", "tacit-brief"}:
            gap_num += 1
            gaps.append(
                {
                    "id": f"CTX-GAP-{gap_num:02d}",
                    "status": "open",
                    **entry,
                    "suggested_remediation": _suggest_remediation(gap_type, inventory, entry),
                }
            )
        elif gap_type == "skill-gap-candidate":
            skill_num += 1
            skill_candidates.append({"id": f"SKILL-CAND-{skill_num:02d}", **entry})

    payload = {
        "slug": slug,
        "run_id": run_id,
        "source_inventory": {
            k: v
            for k, v in inventory.items()
            if not k.startswith("_")
        },
        "context_gaps": gaps,
        "skill_gap_candidates": skill_candidates,
        "counts": {
            "context_gaps": len(gaps),
            "skill_gap_candidates": len(skill_candidates),
        },
    }

    out_json = context_gaps_json_path(root, slug, run_id)
    out_md = context_gaps_path(root, slug, run_id)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_md.write_text(_render_markdown(slug, run_id, payload), encoding="utf-8")
    print(json.dumps(payload["counts"], ensure_ascii=False, indent=2))


def _suggest_remediation(gap_type: str, inventory: dict, entry: dict) -> list[str]:
    items: list[str] = []
    if gap_type in {"missing-source", "missing-repository", "hybrid"}:
        if not inventory["repositories_present"] or inventory["repository_count"] == 0:
            items.append("Добавить/склонировать репозиторий в `repositories/` (релевантный модуль).")
        elif not entry["repository_hits"]:
            items.append(
                "Проверить, есть ли нужный серvice в `repositories/`; при отсутствии — clone + повтор."
            )
        if not inventory["analytics_present"] or inventory["analytics_file_count"] == 0:
            items.append("Экспортировать аналитику в `analytics/` (Confluence / постановка).")
        elif not entry["analytics_hits"]:
            items.append("Дописать постановку в `analytics/` по теме секции.")
        if not inventory["context_doc_present"]:
            items.append("Создать/обновить context-doc через `/find-context`.")
        else:
            items.append("Дописать факт в `Feature-context/` (§ «Что учесть» или закрытый Q-XX).")
        items.append("Опционально: метка в коде (`// ANALYTICS:` / README модуля) для следующих прогонов.")
    if gap_type == "tacit-brief":
        items.append("Зафиксировать факт в брифе или context-doc до `/write-feature`.")
    return items


def _render_markdown(slug: str, run_id: str, payload: dict) -> str:
    inv = payload["source_inventory"]
    lines = [
        f"# Context gaps — {slug} / {run_id}",
        "",
        "> Не «агент тупой», а «источник не был доступен». Отдельно от PROP-* (патчи скиллов).",
        "",
        "## Source inventory",
        "",
        f"- repositories/: {'present' if inv['repositories_present'] else '**missing**'} "
        f"({inv['repository_count']} dirs)",
        f"- analytics/: {'present' if inv['analytics_present'] else '**missing**'} "
        f"({inv['analytics_file_count']} files)",
        f"- context-doc: {'present' if inv['context_doc_present'] else '**missing**'}",
        "",
        "## Context gaps (CTX-GAP-*)",
        "",
    ]
    if not payload["context_gaps"]:
        lines.append("_No scaffold gaps — enrich after human-review or no significant user additions._")
    for gap in payload["context_gaps"]:
        lines.extend(
            [
                f"### {gap['id']} — {gap['section']}",
                "",
                f"- type: `{gap['inferred_type']}`",
                f"- confidence: {gap['confidence']}",
                f"- status: {gap['status']}",
                f"- linked_rev: {gap.get('linked_rev') or '—'}",
                f"- user_cause: {gap.get('user_cause') or '—'}",
                "- what_user_added (sample):",
                "```",
                gap["sample_added"],
                "```",
                "- sources_checked:",
                f"  - repositories: {len(gap['repository_hits'])} hits",
                f"  - analytics: {len(gap['analytics_hits'])} hits",
                f"  - context-doc: {'hit' if gap['context_doc_hit'] else 'no hit'}",
                "- why_agent_could_not_know: _enrich regression-analyst_",
                "- suggested_remediation:",
            ]
        )
        for item in gap["suggested_remediation"]:
            lines.append(f"  - {item}")
        lines.append("")

    lines.extend(["## Not context gaps (skill / process)", ""])
    if not payload["skill_gap_candidates"]:
        lines.append("_None scaffolded — sources existed; check PROP-* proposals._")
    else:
        lines.append("| ID | Section | Repo hits | Analytics hits | Context hit |")
        lines.append("|----|---------|-----------|----------------|-------------|")
        for item in payload["skill_gap_candidates"]:
            lines.append(
                f"| {item['id']} | {item['section']} | {len(item['repository_hits'])} | "
                f"{len(item['analytics_hits'])} | {item['context_doc_hit']} |"
            )
    lines.append("")
    lines.append("_Enrich `why_agent_could_not_know` via analyze-delta / regression-analyst._")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Resolve feature slug from free-text hint (Russian/English, typos, «продолжи БПХ»)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from artifact_paths import (
    context_doc_path,
    feature_dir,
    list_feature_slugs,
    resolve_slug,
    spec_path,
    workspace_root,
)
from pipeline_active_task import load_active_task

HINT_ALIASES = {
    "бпх": "bph",
    "экстаз": "tax",
    "налог": "tax",
    "налоги": "tax",
    "моex": "moex",
    "москва": "moex",
}

STOP_WORDS = frozenset(
    {
        "continue",
        "prodolzhi",
        "prodolzhit",
        "prodolzhai",
        "prodolzh",
        "dalee",
        "dal",
        "продолжи",
        "продолжай",
        "продолжить",
        "дальше",
        "далее",
        "мой",
        "моя",
        "мое",
        "наш",
        "наша",
        "the",
        "my",
        "our",
    }
)


def normalize_hint(text: str) -> str:
    t = text.lower().strip()
    for src, dst in HINT_ALIASES.items():
        t = t.replace(src, dst)
    t = re.sub(r"[^\w\s-]", " ", t, flags=re.UNICODE)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def hint_tokens(text: str) -> list[str]:
    norm = normalize_hint(text)
    tokens = [tok for tok in re.split(r"[\s-]+", norm) if tok]
    return [tok for tok in tokens if tok not in STOP_WORDS and len(tok) > 1]


def slug_artifact_score(root: Path, slug: str) -> int:
    score = 0
    ctx = context_doc_path(root, slug)
    spec = spec_path(root, slug)
    if ctx.is_file() and ctx.stat().st_size > 80:
        score += 50
    if spec.is_file() and spec.stat().st_size > 200:
        score += 100
    fdir = feature_dir(root, slug)
    if fdir.is_dir():
        extras = [
            p
            for p in fdir.iterdir()
            if p.is_file() and p.name.startswith(slug) and p.suffix == ".md"
        ]
        score += min(len(extras) * 5, 25)
    logs = root / "agent-logs" / slug
    if (logs / "manifest.json").is_file():
        score += 20
    return score


def slug_matches_tokens(slug: str, tokens: list[str]) -> bool:
    if not tokens:
        return True
    hay = slug.lower()
    return all(token in hay for token in tokens)


def rank_slugs(root: Path, tokens: list[str]) -> list[tuple[str, int, str]]:
    ranked: list[tuple[str, int, str]] = []
    for slug in list_feature_slugs(root):
        if tokens and not slug_matches_tokens(slug, tokens):
            continue
        score = slug_artifact_score(root, slug)
        reason = "token+artifacts" if tokens else "artifacts"
        ranked.append((slug, score, reason))
    ranked.sort(key=lambda item: (-item[1], item[0]))
    return ranked


def resolve_from_hint(root: Path, hint: str, *, continue_mode: bool = False) -> dict:
    hint = hint.strip()
    if not hint:
        return {"ok": False, "error": "empty hint", "slug": None, "ambiguous": False}

    direct = resolve_slug(hint, root)
    if direct and (root / "Feature-writing" / direct).is_dir():
        score = slug_artifact_score(root, direct)
        if score > 0 or not continue_mode:
            return {
                "ok": True,
                "slug": direct,
                "ambiguous": False,
                "reason": "exact-slug",
                "score": score,
                "candidates": [{"slug": direct, "score": score}],
            }

    tokens = hint_tokens(hint)
    ranked = rank_slugs(root, tokens)

    active = load_active_task(root) or {}
    active_slug = str(active.get("slug") or "").strip()
    if continue_mode and active_slug:
        active_score = slug_artifact_score(root, active_slug)
        if active_score > 0:
            return {
                "ok": True,
                "slug": active_slug,
                "ambiguous": False,
                "reason": "active-task-with-artifacts",
                "score": active_score,
                "candidates": [{"slug": active_slug, "score": active_score}],
            }
        # Typo sibling: active slug empty but close name has artifacts
        prefix = active_slug.rsplit("-", 1)[0] if "-" in active_slug else active_slug
        siblings = [
            (slug, score)
            for slug, score, _ in rank_slugs(root, [prefix] if prefix else [])
            if score > 0 and slug != active_slug
        ]
        if len(siblings) == 1:
            slug, score = siblings[0]
            return {
                "ok": True,
                "slug": slug,
                "ambiguous": False,
                "reason": f"typo-sibling-of-{active_slug}",
                "score": score,
                "candidates": [{"slug": slug, "score": score}],
                "corrected_from": active_slug,
            }

    if not ranked:
        return {
            "ok": False,
            "error": "no matching slug",
            "slug": None,
            "ambiguous": False,
            "tokens": tokens,
        }

    with_artifacts = [(slug, score, reason) for slug, score, reason in ranked if score > 0]
    pool = with_artifacts or ranked

    if len(pool) == 1:
        slug, score, reason = pool[0]
        return {
            "ok": True,
            "slug": slug,
            "ambiguous": False,
            "reason": reason,
            "score": score,
            "candidates": [{"slug": slug, "score": score}],
            "tokens": tokens,
        }

    top_score = pool[0][1]
    ties = [item for item in pool if item[1] == top_score]
    if len(ties) == 1:
        slug, score, reason = ties[0]
        return {
            "ok": True,
            "slug": slug,
            "ambiguous": False,
            "reason": reason,
            "score": score,
            "candidates": [{"slug": s, "score": sc} for s, sc, _ in pool[:5]],
            "tokens": tokens,
        }

    return {
        "ok": False,
        "slug": None,
        "ambiguous": True,
        "reason": "multiple-candidates",
        "candidates": [{"slug": s, "score": sc} for s, sc, _ in pool[:8]],
        "tokens": tokens,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve feature slug from user hint")
    parser.add_argument("hint", nargs="?", default="", help="Free-text hint or slug")
    parser.add_argument("--continue", dest="continue_mode", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = workspace_root()
    result = resolve_from_hint(root, args.hint, continue_mode=args.continue_mode)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif result.get("ok"):
        print(result["slug"])
    elif result.get("ambiguous"):
        names = ", ".join(c["slug"] for c in result.get("candidates", []))
        print(f"ambiguous: {names}", file=sys.stderr)
        return 2
    else:
        print(result.get("error", "unknown"), file=sys.stderr)
        return 1

    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())

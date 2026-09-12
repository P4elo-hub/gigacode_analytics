#!/usr/bin/env python3
"""Дособрать CONTEXT_DOC после resolve: якоря и § «Что учесть», без переписывания current-state."""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

from artifact_paths import (
    challenges_map_path,
    context_doc_path,
    gaps_map_path,
    resolve_slug,
    spec_path,
    workspace_root,
)

CONSIDER_HEADING = "## Что учесть при написании фичи"
OPEN_QUESTIONS_HEADING = "## Открытые вопросы"
CLOSED_QUESTIONS_HEADING = "## Закрытые вопросы"
REFRESH_HEADING = "### Актуализация после resolve"
DECISION_ROW_RE = re.compile(
    r"^\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|",
    re.MULTILINE,
)
FIELD_TOKEN_RE = re.compile(r"`([A-Za-z][A-Za-z0-9_.]+)`")
MAX_ANCHORS = 12
MAX_DECISION_LINES = 20


def _today() -> str:
    return dt.date.today().isoformat()


def _extract_decisions(map_text: str) -> list[str]:
    lines: list[str] = []
    for match in DECISION_ROW_RE.finditer(map_text):
        identifier = match.group(1).strip()
        decision = match.group(3).strip()
        if identifier in {"ID", "----", "—"} or not decision or decision == "Решение":
            continue
        lines.append(f"- {identifier}: {decision}")
        if len(lines) >= MAX_DECISION_LINES:
            break
    return lines


def _extract_field_anchors(spec_text: str) -> list[str]:
    seen: set[str] = set()
    anchors: list[str] = []
    for token in FIELD_TOKEN_RE.findall(spec_text):
        if token in seen or len(token) < 3:
            continue
        seen.add(token)
        anchors.append(token)
        if len(anchors) >= MAX_ANCHORS:
            break
    return anchors


def _closed_questions_block(context_text: str) -> str:
    start = context_text.find(CLOSED_QUESTIONS_HEADING)
    if start == -1:
        return ""
    rest = context_text[start:]
    next_heading = re.search(r"^##\s+", rest[len(CLOSED_QUESTIONS_HEADING) :], re.MULTILINE)
    if next_heading:
        return rest[: len(CLOSED_QUESTIONS_HEADING) + next_heading.start()]
    return rest


def build_refresh_section(
    *,
    date_stamp: str,
    decisions: list[str],
    anchors: list[str],
    closed_questions: str,
) -> str:
    lines = [
        f"{REFRESH_HEADING} ({date_stamp})",
        "",
        "Решения из resolve, которые писатель и ревьюер должны считать актуальнее исходного current-state:",
        "",
    ]
    if decisions:
        lines.extend(decisions)
    else:
        lines.append("- закрытых решений в картах нет — опирайся на § «Закрытые вопросы».")
    lines.extend(["", "**Якоря полей из актуальной SPEC:**", ""])
    if anchors:
        lines.append(", ".join(f"`{name}`" for name in anchors))
    else:
        lines.append("—")
    if closed_questions.strip():
        lines.extend(["", "См. также § «Закрытые вопросы» ниже — не переспрашивать закрытые Q."])
    lines.append("")
    return "\n".join(lines)


def apply_refresh(context_text: str, refresh_section: str) -> str:
    existing = re.search(
        rf"{re.escape(REFRESH_HEADING)}.*?(?=^##\s+|\Z)",
        context_text,
        re.DOTALL | re.MULTILINE,
    )
    if existing:
        return context_text[: existing.start()] + refresh_section + context_text[existing.end() :]

    consider_at = context_text.find(CONSIDER_HEADING)
    if consider_at != -1:
        after_heading = consider_at + len(CONSIDER_HEADING)
        next_h2 = re.search(r"^##\s+", context_text[after_heading:], re.MULTILINE)
        insert_at = after_heading + (next_h2.start() if next_h2 else len(context_text) - after_heading)
        prefix = context_text[:insert_at].rstrip() + "\n\n"
        suffix = context_text[insert_at:]
        return prefix + refresh_section + ("\n" if suffix.startswith("#") else "") + suffix

    open_at = context_text.find(OPEN_QUESTIONS_HEADING)
    if open_at != -1:
        return (
            context_text[:open_at].rstrip()
            + "\n\n"
            + CONSIDER_HEADING
            + "\n\n"
            + refresh_section
            + context_text[open_at:]
        )
    return context_text.rstrip() + "\n\n" + CONSIDER_HEADING + "\n\n" + refresh_section


def refresh_context_doc(root: Path, slug: str) -> Path:
    context = context_doc_path(root, slug)
    if not context.is_file():
        raise FileNotFoundError(f"CONTEXT_DOC не найден: {context}")
    decisions: list[str] = []
    for map_file in (gaps_map_path(root, slug), challenges_map_path(root, slug)):
        if map_file.is_file():
            decisions.extend(_extract_decisions(map_file.read_text(encoding="utf-8")))
    spec = spec_path(root, slug)
    spec_text = spec.read_text(encoding="utf-8") if spec.is_file() else ""
    original = context.read_text(encoding="utf-8")
    section = build_refresh_section(
        date_stamp=_today(),
        decisions=decisions,
        anchors=_extract_field_anchors(spec_text),
        closed_questions=_closed_questions_block(original),
    )
    context.write_text(apply_refresh(original, section), encoding="utf-8")
    return context


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="refresh-context")
    parser.add_argument("slug", help="slug фичи")
    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    root = workspace_root(Path(args.root))
    slug = resolve_slug(args.slug, root) or args.slug
    try:
        path = refresh_context_doc(root, slug)
    except FileNotFoundError as error:
        print(str(error), file=sys.stderr)
        return 1
    print(f"Обновлён CONTEXT_DOC: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

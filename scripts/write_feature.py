#!/usr/bin/env python3
"""write-feature: план блоков, проверка фрагмента и сборка SPEC.

Список блоков — `kb-writing-kits/spec-catalog.yaml`.
`--mode plan` — таблица блоков, скиллы и готовые задания writer.
`--mode check-part` — принять или отклонить один `*.part-*.md`.
`--mode assemble` — склейка фрагментов в SPEC.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from part_checks import (
    check_part_against_skills,
    find_block_by_id,
    format_writer_assignments,
)
from section_profiles import DEFAULT_PROFILE, infer_sections
from spec_catalog import catalog_blocks, parent_headers, parent_order

FEATURE_WRITING_DIR = "Feature-writing"

_PART_FILENAME_TEMPLATE = "{slug}.part-{block_id}.md"
_PART_GLOB_TEMPLATE = "{slug}.part-*.md"
_CONTEXT_FILENAME_TEMPLATE = "{slug}.context.md"


@dataclass
class AssembleResult:
    document: str
    missing_parts: list[str]
    orphan_parts: list[str]


def resolve_active_skills(block: dict, active_sections: list[str]) -> list[str]:
    """Скиллы блока: базовые + те, что привязаны к активным разделам."""
    skill_names: list[str] = []
    for skill_name in block.get("skills") or []:
        if skill_name not in skill_names:
            skill_names.append(skill_name)
    extra_by_section = block.get("section_skills") or {}
    for section_id in active_sections:
        for skill_name in extra_by_section.get(section_id, []):
            if skill_name not in skill_names:
                skill_names.append(skill_name)
    return skill_names


def list_active_blocks(target_sections: list[str]) -> list[dict]:
    """Блоки, у которых есть хотя бы один активный раздел, в порядке каталога."""
    active: list[dict] = []
    target_set = set(target_sections)
    for block in catalog_blocks():
        present = [section_id for section_id in block["sections"] if section_id in target_set]
        if present:
            active.append({
                **block,
                "active_sections": present,
                "active_skills": resolve_active_skills(block, present),
            })
    return active


def part_filename(slug: str, block_id: str) -> str:
    return _PART_FILENAME_TEMPLATE.format(slug=slug, block_id=block_id)


def find_orphan_parts(part_dir: Path, slug: str, consumed: set[str]) -> list[str]:
    if not part_dir.is_dir():
        return []
    pattern = _PART_GLOB_TEMPLATE.format(slug=slug)
    return sorted(
        path.name for path in part_dir.glob(pattern) if path.name not in consumed
    )


def delete_working_files(part_dir: Path, slug: str) -> list[str]:
    """Удаляет part и context после успешной сборки SPEC."""
    deleted_paths: list[str] = []
    if not part_dir.is_dir():
        return deleted_paths

    part_pattern = _PART_GLOB_TEMPLATE.format(slug=slug)
    for part_path in sorted(part_dir.glob(part_pattern)):
        part_path.unlink()
        deleted_paths.append(str(part_path))

    context_path = part_dir / _CONTEXT_FILENAME_TEMPLATE.format(slug=slug)
    if context_path.is_file():
        context_path.unlink()
        deleted_paths.append(str(context_path))
    return deleted_paths


def build_plan(
    feature_brief: str,
    *,
    section_id: str | None,
    protocol: str | None,
    feature_name: str,
    part_dir: str,
    profile: str | None = None,
) -> str:
    target = infer_sections(feature_brief, section_id, profile)
    active = list_active_blocks(target)
    proto = protocol or "не задан"
    lines = [
        "# План написания документа фичи (по блокам)",
        "",
        f"Фича: `{feature_name}`",
        f"Профиль разделов: `{profile or DEFAULT_PROFILE}`",
        f"Протокол интеграции: `{proto}`",
        "",
        "Активные блоки (в порядке записи). Один блок = один вызов `spec-writer`. "
        "Writer грузит **все** скиллы из колонки — не больше и не меньше:",
        "",
        "| # | Блок | Скиллы | Разделы | Файл фрагмента |",
        "|---|---|---|---|---|",
    ]
    for index, block in enumerate(active, start=1):
        sections = ", ".join(block["active_sections"])
        skill_cell = ", ".join(f"`{name}`" for name in block["active_skills"])
        lines.append(
            f"| {index} | `{block['id']}` — {block['label']} | {skill_cell} | "
            f"{sections} | `{part_dir}/{part_filename(feature_name, block['id'])}` |"
        )

    lines.extend([
        "",
        "## Как писать",
        "",
        "Оркестратор вызывает `spec-writer` **отдельно на каждую строку** "
        "(свежий контекст). В задании: `block_id`, скиллы из колонки, бриф, slug, "
        "протокол, пути `CONTEXT_DOC` и `<slug>.context.md`. Writer загружает "
        "каждый скилл колонки и читает его template / example / gate "
        "из kit, указанного в `kb-writing-kits/spec-catalog.yaml`.",
        "",
        "`check-part` вызывает оркестратор **один** раз на блок: всегда "
        "`--block-id` и `--sections` утверждённого плана. Writer сам не гоняет "
        "проверку на первом проходе.",
        "",
        "После всех фрагментов — сборка. Успешный `--mode assemble --out` "
        "удаляет `*.part-*.md` и `*.context.md`.",
        "",
        "```bash",
        f'python3 scripts/write_feature.py "<бриф>" --mode assemble --name {feature_name} '
        f'--part-dir {part_dir} --out {part_dir}/{feature_name}.md',
        "```",
    ])
    lines.extend(
        format_writer_assignments(
            active,
            feature_name=feature_name,
            part_dir=part_dir,
            part_filename_for=part_filename,
        )
    )
    return "\n".join(lines)


def check_part_document(
    feature_brief: str,
    *,
    section_id: str | None,
    feature_name: str,
    part_dir: Path,
    block_id: str,
    profile: str | None = None,
) -> tuple[int, str]:
    target = infer_sections(feature_brief, section_id, profile)
    active = list_active_blocks(target)
    block = find_block_by_id(active, block_id)
    if block is None:
        known = ", ".join(f"`{item['id']}`" for item in active) or "нет активных"
        return 1, f"блок `{block_id}` не в плане. Активные: {known}\n"

    part_path = part_dir / part_filename(feature_name, block_id)
    problems = check_part_against_skills(part_path, block["active_skills"])
    if problems:
        skill_line = ", ".join(block["active_skills"])
        details = "\n".join(f"- {item}" for item in problems)
        return 1, (
            f"блок `{block_id}` не принят. скиллы плана: {skill_line}\n{details}\n"
        )
    return 0, f"блок `{block_id}` принят\n"


def assemble_document(
    feature_brief: str,
    *,
    section_id: str | None,
    feature_name: str,
    part_dir: Path,
    profile: str | None = None,
) -> AssembleResult:
    target = infer_sections(feature_brief, section_id, profile)
    active = list_active_blocks(target)

    lines: list[str] = [f"# {feature_name}", ""]
    missing: list[str] = []
    consumed: set[str] = set()
    headers = parent_headers()
    for parent in parent_order():
        parent_blocks = [block for block in active if str(block["parent"]) == str(parent)]
        if not parent_blocks:
            continue
        if parent in headers:
            lines.extend([headers[parent], ""])
        for block in parent_blocks:
            part_path = part_dir / part_filename(feature_name, block["id"])
            consumed.add(part_path.name)
            if part_path.is_file():
                lines.append(part_path.read_text(encoding="utf-8").strip())
                lines.append("")
            else:
                missing.append(part_path.name)
                lines.extend([
                    f"<!-- TODO: фрагмент блока `{block['id']}` не найден: {part_path.name} -->",
                    "",
                ])

    document = "\n".join(lines).strip() + "\n"
    if missing:
        sys.stderr.write(
            "Предупреждение: не найдены фрагменты блоков: " + ", ".join(missing) + "\n"
        )
    orphans = find_orphan_parts(part_dir, feature_name, consumed)
    if orphans:
        sys.stderr.write(
            "Предупреждение: фрагменты есть на диске, но НЕ вошли в документ "
            "(их разделы отсутствуют в --sections): " + ", ".join(orphans) + "\n"
        )
    return AssembleResult(
        document=document,
        missing_parts=missing,
        orphan_parts=orphans,
    )


def _read_brief(args: argparse.Namespace) -> str:
    if args.brief:
        return args.brief
    if args.brief_file:
        return Path(args.brief_file).read_text(encoding="utf-8")
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return ""


def _slugify(text: str) -> str:
    words = re.findall(r"[a-zа-яё0-9]+", text.lower())
    return "-".join(words[:6]) or "feature"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="write-feature",
        description=(
            "План блоков (--mode plan), проверка фрагмента (--mode check-part) "
            "или сборка SPEC (--mode assemble)."
        ),
    )
    parser.add_argument("brief", nargs="?", help="Бриф фичи (текст).")
    parser.add_argument("--brief", dest="brief_opt", help="Бриф (альтернатива позиционному).")
    parser.add_argument("--brief-file", help="Файл с брифом.")
    parser.add_argument("--name", help="Название/slug фичи.")
    parser.add_argument("--protocol", help="Протокол интеграции: REST, gRPC, GraphQL, SOAP, Async.")
    parser.add_argument(
        "--sections",
        help="Override разделов: full или список через запятую. По умолчанию профиль.",
    )
    parser.add_argument(
        "--profile",
        default=DEFAULT_PROFILE,
        help="Профиль разделов: sihist (по умолчанию), core, full.",
    )
    parser.add_argument(
        "--mode",
        choices=["plan", "check-part", "assemble"],
        default="plan",
        help="plan — таблица и задания; check-part — приём фрагмента; assemble — склейка.",
    )
    parser.add_argument(
        "--block-id",
        help="id блока для --mode check-part (например usecase-as-is).",
    )
    parser.add_argument(
        "--part-dir",
        help="Папка фрагментов для assemble (по умолчанию папка --out или Feature-writing).",
    )
    parser.add_argument("--out", help="Куда записать результат. По умолчанию stdout.")

    args = parser.parse_args(argv)
    if not args.brief and args.brief_opt:
        args.brief = args.brief_opt

    brief = _read_brief(args).strip()
    if not brief:
        parser.error("не задан бриф: передай текст аргументом, через --brief-file или stdin.")

    name = args.name or _slugify(brief)
    default_part_dir = FEATURE_WRITING_DIR

    if args.mode == "plan":
        output = build_plan(
            brief,
            section_id=args.sections,
            protocol=args.protocol,
            feature_name=name,
            part_dir=args.part_dir or default_part_dir,
            profile=args.profile,
        )
        _write_output(args.out, output)
        return 0

    if args.mode == "check-part":
        if not args.block_id:
            parser.error("--mode check-part требует --block-id")
        check_part_dir = Path(args.part_dir) if args.part_dir else Path(default_part_dir)
        exit_code, check_message = check_part_document(
            brief,
            section_id=args.sections,
            feature_name=name,
            part_dir=check_part_dir,
            block_id=args.block_id,
            profile=args.profile,
        )
        stream = sys.stdout if exit_code == 0 else sys.stderr
        stream.write(check_message)
        return exit_code

    assemble_part_dir = Path(args.part_dir) if args.part_dir else (
        Path(args.out).parent if args.out else Path(default_part_dir)
    )
    assemble_result = assemble_document(
        brief,
        section_id=args.sections,
        feature_name=name,
        part_dir=assemble_part_dir,
        profile=args.profile,
    )
    _write_output(args.out, assemble_result.document)
    if args.out:
        if assemble_result.missing_parts:
            print(
                "Рабочие файлы не удалены: не хватает фрагментов "
                + ", ".join(assemble_result.missing_parts),
                file=sys.stderr,
            )
        else:
            deleted_paths = delete_working_files(assemble_part_dir, name)
            if deleted_paths:
                print(
                    "Удалены рабочие файлы: " + ", ".join(deleted_paths),
                    file=sys.stderr,
                )
    return 0


def _write_output(out_path_value: str | None, output: str) -> None:
    if out_path_value:
        out_path = Path(out_path_value)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
        print(f"Записано: {out_path}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    raise SystemExit(main())

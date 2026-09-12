"""Проверка part-файла: фрагмент есть и UML на месте, если скилл в плане.

Форма раздела (пример запроса, ER, таблицы) — kit, не этот скрипт.
"""

from __future__ import annotations

from pathlib import Path

UML_SKILL_NAME = "uml-diagram-analysis"
PLANTUML_START = "@startuml"
PLANTUML_END = "@enduml"


def find_block_by_id(active_blocks: list[dict], block_id: str) -> dict | None:
    for block in active_blocks:
        if block["id"] == block_id:
            return block
    return None


def check_part_against_skills(part_path: Path, skill_names: list[str]) -> list[str]:
    """Пустой список — блок принят. Иначе причины отказа."""
    if not skill_names:
        return ["у блока пустой список скиллов"]
    if not part_path.is_file():
        return [f"нет файла `{part_path}`"]

    fragment_text = part_path.read_text(encoding="utf-8")
    problems: list[str] = []
    if not fragment_text.strip():
        problems.append("фрагмент пустой")
    if UML_SKILL_NAME in skill_names:
        has_start = PLANTUML_START in fragment_text
        has_end = PLANTUML_END in fragment_text
        if not has_start or not has_end:
            problems.append(
                f"в плане есть `{UML_SKILL_NAME}`, во фрагменте нет PlantUML "
                f"(`{PLANTUML_START}` / `{PLANTUML_END}`)"
            )
    return problems


def format_writer_assignments(
    active_blocks: list[dict],
    *,
    feature_name: str,
    part_dir: str,
    part_filename_for,
) -> list[str]:
    """Готовые блоки задания: оркестратор копирует целиком, без выбора «первого скилла»."""
    lines = [
        "",
        "## Задания spec-writer (копировать блок целиком в task)",
        "",
        "Не выбирай один скилл из колонки. Строка `skills:` — полный список.",
        "",
    ]
    for block in active_blocks:
        skill_line = ", ".join(block["active_skills"])
        section_line = ", ".join(block["active_sections"])
        part_name = part_filename_for(feature_name, block["id"])
        lines.extend([
            f"### `{block['id']}`",
            f"- block_id: `{block['id']}`",
            f"- skills: {skill_line}",
            f"- sections: {section_line}",
            f"- part: `{part_dir}/{part_name}`",
            "",
        ])
    return lines

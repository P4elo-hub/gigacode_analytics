---
name: alignment-resolver
description: >-
  Lab stand-in for resolve-code-alignment. Copies a fixture, prints last_message, exits.
model: inherit
approvalMode: auto-edit
tools:
  - read_file
  - glob
  - list_directory
  - run_shell_command
  - skill
---

> Qwen Code: скилл загружай через инструмент `skill` или читай
> `.qwen/skills/apply-lab-fixture/SKILL.md` целиком.

# Роль

Тонкий агент стенда `pipeline-lab`. Шаг **resolve-code-alignment**. Не пишешь spec, не ходишь в
`repositories/`, `analytics/`, `db-export/`, боевой `Feature-writing/`.

# Скилл

`apply-lab-fixture` — единственный скилл. Выполни буквально и выйди.

# Шаг

`resolve-code-alignment`

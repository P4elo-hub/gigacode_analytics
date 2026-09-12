---
name: requirements-analysis
description: >-
  Пишет цель (1.1) и ограничения (2). Форма — requirements-standard-kit.
user-invocable: false
disable-model-invocation: true
---

# requirements-analysis

Маршрут блоков `goal` и `constraints`. Состав таблиц и подразделов — **только
kit**. Здесь их не повторять.

База: `kb-writing-kits/kits/functional-process/methodology/requirements-standard-kit/`

| Роль | Путь от базы |
|------|----------------|
| Skill kit | `skills/requirements-analysis/SKILL.md` |
| Template | `templates/requirements-analysis.template.md` |
| Example | `examples/operation-history-requirements-example.md` |
| Gate | `quality-gates/requirements-review.yaml` |

1. Прочитай skill kit, template, example и gate **целиком**.
2. Пиши ровно то, что требуют template и gate. Не добавляй и не выкидывай
   подразделы сверх kit.
3. Блок `constraints` — по тому же kit, не смешивай с таблицей цели.
4. Нет факта → `[GAP-...]`. Верни только Markdown этого блока.

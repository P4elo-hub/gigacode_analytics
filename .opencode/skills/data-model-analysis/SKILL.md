---
name: data-model-analysis
description: >-
  Пишет §4.2.3 модель данных. Форма — data-standard-kit.
disable-model-invocation: true
---

# data-model-analysis

Маршрут блока `data-model`. Форма — kit.
Миграция и field-mapping — другие скиллы колонки плана, не подмешивай их сюда.

База: `kb-writing-kits/kits/database-storage/methodology/data-standard-kit/`

| Роль | Файл |
|------|------|
| Skill kit | `skills/data-model-analysis/SKILL.md` |
| Template | `templates/data-model.template.md` |
| Example | `examples/payment-processing-data-model-example.md` |
| Gate | `quality-gates/data-model-review.yaml` |

1. Прочитай skill kit, template, example и gate **целиком**.
2. Пиши ровно по kit. DDL/DML миграции — в блоке `migration`, не здесь.
3. Нет факта → `[GAP-...]`. Верни только Markdown блока `data-model`.

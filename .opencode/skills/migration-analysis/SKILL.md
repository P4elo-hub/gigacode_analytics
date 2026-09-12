---
name: migration-analysis
description: >-
  Пишет план миграции. Форма — migration-standard-kit.
disable-model-invocation: true
---

# migration-analysis

Маршрут блока `migration`. Форма — kit.

База: `kb-writing-kits/kits/migration-liquibase/methodology/migration-standard-kit/`

| Роль | Путь от базы |
|------|----------------|
| Skill kit | `skills/migration-analysis/SKILL.md` |
| Template | `templates/migration-plan.template.md` |
| Example | `examples/payment-status-backfill-migration-example.md` |
| Gate | `quality-gates/migration-review.yaml` |

1. Прочитай skill kit, template, example и gate **целиком**.
2. Пиши ровно по kit. DDL/DML — здесь, не в таблице модели данных.
3. Нет факта → `[GAP-...]`. Верни только Markdown блока `migration`.

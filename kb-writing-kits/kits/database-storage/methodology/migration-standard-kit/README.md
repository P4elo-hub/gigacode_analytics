<!--
Imported from: migration-standard-kit/README.md
Current-state adaptation:
- Use only confirmed current behavior.
- Do not write TO BE, rollout/rollback, future requirements, design proposals, GAP/ASM/DESIGN markers as reader-facing content.
- Put unresolved or future/change-specific material into working-layer gaps, not into permanent KB pages.
-->
# Migration Standard Kit


## Зачем нужен kit

Data model kit описывает целевую структуру хранения, но не должен включать миграционные скрипты. Migration kit закрывает раздел миграции: как безопасно перейти от текущей структуры к целевой.

| Слой | Зачем нужен | Что лежит здесь |
|---|---|---|
| `skills/` | Учит агента планировать миграции. | `migration-analysis/SKILL.md` |
| `spec-kit/` | Задает контракт плана миграции. | `migration-plan.schema.yaml` |
| `templates/` | Дает форму документа. | `migration-plan.template.md` |
| `examples/` | Показывает ожидаемый стиль. | `payment-status-backfill-migration-example.md` |
| `quality-gates/` | Проверяет готовность миграции. | `migration-review.yaml` |

## Как использовать в runbook

```text
Команда: описать миграцию данных.

Используй:
- skill: migration-standard-kit/skills/migration-analysis/SKILL.md
- spec: migration-standard-kit/spec-kit/migration-plan.schema.yaml
- template: migration-standard-kit/templates/migration-plan.template.md
- example: migration-standard-kit/examples/payment-status-backfill-migration-example.md
- quality gate: migration-standard-kit/quality-gates/migration-review.yaml

Выход:
- 05-Migrations/<current-state functionality>-migration.md
```

## Когда применять

Применяй kit, если фича:

- добавляет/меняет/удаляет таблицы, колонки, индексы или constraints;
- требует backfill существующих данных;
- должна сохранять совместимость старой и новой версий приложения;

## Главная идея

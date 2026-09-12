<!--
Imported from: data-mapping-standard-kit/README.md
Current-state adaptation:
- Use only confirmed current behavior.
- Do not write TO BE, rollout/rollback, future requirements, design proposals, GAP/ASM/DESIGN markers as reader-facing content.
- Put unresolved or future/change-specific material into working-layer gaps, not into permanent KB pages.
-->
# Data Mapping Standard Kit

Этот каталог описывает маппинг данных между источником и целевой моделью: поля, трансформации, enum/status mapping, null/default behavior, validation и rejection rules.

## Зачем нужен kit

Маппинг часто оказывается размазан между интеграцией, моделью данных и кодом. Kit задает отдельный артефакт source -> target, который можно ревьюить с владельцами систем.

| Слой | Зачем нужен | Что лежит здесь |
|---|---|---|
| `skills/` | Учит агента строить field-level mapping. | `data-mapping-analysis/SKILL.md` |
| `spec-kit/` | Задает контракт mapping artifact. | `data-mapping.schema.yaml` |
| `templates/` | Дает форму документа. | `data-mapping.template.md` |
| `examples/` | Показывает ожидаемый стиль. | `bph-event-to-operation-mapping-example.md` |
| `quality-gates/` | Проверяет готовность маппинга. | `data-mapping-review.yaml` |

## Когда применять

Применяй kit, если нужно:

- сопоставить поля source contract и target contract/model;
- описать трансформации, units, formats, timezone, currency;
- описать enum/status mapping;
- определить поведение при null/missing/default;
- задать validation и rejection rules;
- подготовить mapping для интеграции, backfill или аналитики.

## Граница с другими kits

`integration-standard-kit` описывает контракт обмена; `data-mapping-standard-kit` описывает как данные из одного контракта/модели превращаются в другой.

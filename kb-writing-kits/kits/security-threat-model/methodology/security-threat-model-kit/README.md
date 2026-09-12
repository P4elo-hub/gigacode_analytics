<!--
Imported from: security-threat-model-kit/README.md
Current-state adaptation:
- Use only confirmed current behavior.
- Do not write TO BE, rollout/rollback, future requirements, design proposals, GAP/ASM/DESIGN markers as reader-facing content.
- Put unresolved or future/change-specific material into working-layer gaps, not into permanent KB pages.
-->
# Security Threat Model Kit

Этот каталог описывает threat model фичи: assets, actors, trust boundaries, threats, mitigations, residual risk и связи с security NFR.

## Зачем нужен kit

Security в NFR фиксирует требования. Threat model объясняет, от каких угроз защищаемся, где границы доверия и какие меры нужны.

| Слой | Зачем нужен | Что лежит здесь |
|---|---|---|
| `skills/` | Учит агента строить threat model. | `threat-model-analysis/SKILL.md` |
| `spec-kit/` | Задает контракт threat model. | `threat-model.schema.yaml` |
| `templates/` | Дает форму документа. | `threat-model.template.md` |
| `examples/` | Показывает ожидаемый стиль. | `bph-getlink-events-threat-model-example.md` |
| `quality-gates/` | Проверяет готовность threat model. | `threat-model-review.yaml` |

## Когда применять

Применяй kit, если фича:

- обрабатывает персональные, финансовые или чувствительные данные;
- меняет доступы, роли, auth/authz;
- добавляет внешнюю интеграцию;
- пересекает trust boundary;
- требует аудита, маскирования, шифрования или data retention.

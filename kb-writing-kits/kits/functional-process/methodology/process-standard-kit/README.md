<!--
Imported from: process-standard-kit/README.md
Current-state adaptation:
- Use only confirmed current behavior.
- Do not write TO BE, rollout/rollback, future requirements, design proposals, GAP/ASM/DESIGN markers as reader-facing content.
- Put unresolved or future/change-specific material into working-layer gaps, not into permanent KB pages.
-->
# Process Standard Kit


## Зачем нужен kit

Process kit нужен, когда фича меняет последовательность действий пользователя, оператора, системы или внешних участников, а также когда нужно сравнить текущее и целевое поведение.

| Слой | Зачем нужен | Что лежит здесь |
|---|---|---|
| `spec-kit/` | Задает контракт процесса. | `process.schema.yaml` |
| `templates/` | Дает форму документа. | `process.template.md` |
| `examples/` | Показывает ожидаемый стиль. | `operation-history-process-example.md` |
| `quality-gates/` | Проверяет готовность процесса. | `process-review.yaml` |

## Как использовать в runbook

```text

Используй:
- skill: process-standard-kit/skills/process-analysis/SKILL.md
- spec: process-standard-kit/spec-kit/process.schema.yaml
- template: process-standard-kit/templates/process.template.md
- example: process-standard-kit/examples/operation-history-process-example.md
- quality gate: process-standard-kit/quality-gates/process-review.yaml

Выход:
- 02-Process/<current-state functionality>-process.md
```

## Когда применять

Применяй kit, если нужны:

- текстовый текущее поведение;
- участники и роли процесса;
- pain points текущего процесса;
- отличия текущего и целевого поведения;
- связь с use cases, activity diagram, UI или интеграциями.

## Граница с другими kits

`process-standard-kit` отвечает за бизнес/системный поток целиком. `use-case-standard-kit` отвечает за конкретный сценарий, а `uml-diagram-standard-kit` визуализирует flow в диаграммах.

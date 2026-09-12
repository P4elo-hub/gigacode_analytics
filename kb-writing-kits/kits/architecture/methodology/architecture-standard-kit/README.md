<!--
Imported from: architecture-standard-kit/README.md
Current-state adaptation:
- Use only confirmed current behavior.
- Do not write TO BE, rollout/rollback, future requirements, design proposals, GAP/ASM/DESIGN markers as reader-facing content.
- Put unresolved or future/change-specific material into working-layer gaps, not into permanent KB pages.
-->
# Architecture Standard Kit

Этот каталог раскладывает архитектурный слой фичи: затрагиваемые компоненты, границы систем, C4-диаграммы, архитектурные решения и impact analysis.

## Зачем нужен kit

Architecture kit нужен, когда фича меняет компоненты, сервисы, контейнеры, взаимодействия между системами, технологический выбор или ответственность команд.

| Слой | Зачем нужен | Что лежит здесь |
|---|---|---|
| `skills/` | Учит агента описывать архитектурный impact. | `architecture-analysis/SKILL.md` |
| `spec-kit/` | Задает контракт архитектурного артефакта. | `architecture.schema.yaml` |
| `templates/` | Дает форму документа. | `architecture.template.md` |
| `examples/` | Показывает ожидаемый стиль. | `operation-history-architecture-example.md` |
| `quality-gates/` | Проверяет готовность результата. | `architecture-review.yaml` |

## Как использовать в runbook

```text
Команда: описать архитектуру фичи.

Используй:
- skill: architecture-standard-kit/skills/architecture-analysis/SKILL.md
- spec: architecture-standard-kit/spec-kit/architecture.schema.yaml
- template: architecture-standard-kit/templates/architecture.template.md
- example: architecture-standard-kit/examples/operation-history-architecture-example.md
- quality gate: architecture-standard-kit/quality-gates/architecture-review.yaml

Выход:
- 04-Architecture/<current-state functionality>-architecture.md
```

## Когда применять

Применяй kit, если фича:

- добавляет или меняет сервис, модуль, контейнер, gateway, worker, job;
- меняет ответственность между компонентами;
- требует C4 Container/Component diagram;
- вводит архитектурное решение или trade-off;
- влияет на runtime topology, dependencies, deployment boundary или ownership.

## Граница с другими kits

| Kit | Граница |
|---|---|
| `integration-standard-kit` | Описывает API/event contract; architecture kit описывает компонентную границу и ответственность |
| `uml-diagram-standard-kit` | Sequence/activity показывают flow; architecture kit показывает статическую структуру |
| `data-standard-kit` | Описывает модель хранения; architecture kit показывает, какой компонент владеет данными |
| `nfr-standard-kit` | Описывает целевые NFR; architecture kit фиксирует architectural drivers и constraints |

## Главная идея

Архитектурный артефакт должен объяснять, какие части системы меняются, почему выбран такой дизайн и какие последствия это несет.

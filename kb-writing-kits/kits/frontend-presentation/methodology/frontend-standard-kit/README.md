<!--
Imported from: frontend-standard-kit/README.md
Current-state adaptation:
- Use only confirmed current behavior.
- Do not write TO BE, rollout/rollback, future requirements, design proposals, GAP/ASM/DESIGN markers as reader-facing content.
- Put unresolved or future/change-specific material into working-layer gaps, not into permanent KB pages.
-->
# Frontend Standard Kit

Этот каталог описывает UI/UX слой фичи: экраны, состояния, действия пользователя, API -> UI mapping, validation, empty/loading/error states и тексты сообщений.

## Зачем нужен kit

Frontend kit нужен, когда фича имеет видимое поведение в интерфейсе или влияет на данные, которые пользователь видит на экране.

| Слой | Зачем нужен | Что лежит здесь |
|---|---|---|
| `skills/` | Учит агента описывать UI-поведение. | `frontend-analysis/SKILL.md` |
| `spec-kit/` | Задает контракт UI-артефакта. | `frontend.schema.yaml` |
| `templates/` | Дает форму документа. | `frontend.template.md` |
| `examples/` | Показывает ожидаемый стиль. | `operation-history-frontend-example.md` |
| `quality-gates/` | Проверяет готовность UI-описания. | `frontend-review.yaml` |

## Когда применять

Применяй kit, если фича:

- меняет экран, форму, список, карточку, таблицу или состояние UI;
- меняет порядок/состав отображаемых данных;
- требует API -> UI mapping;
- требует validation, error, empty, loading или disabled states;
- меняет пользовательские сообщения.

## Граница с другими kits

Frontend kit не проектирует backend contract. Если API меняется, использовать `integration-standard-kit`. Если меняется персистентная модель, использовать `data-standard-kit`.

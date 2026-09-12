<!--
Imported from: nfr-standard-kit/templates\feature-toggles.template.md
Current-state adaptation:
- Use only confirmed current behavior.
- Do not write TO BE, rollout/rollback, future requirements, design proposals, GAP/ASM/DESIGN markers as reader-facing content.
- Put unresolved or future/change-specific material into working-layer gaps, not into permanent KB pages.
-->
#### NFR — [Название фичи] (current-state functionality Toggles)

### current-state functionality Toggles

**Toggle [N]: [Краткое название]**

| Параметр | Значение | Статус |
|----------|----------|--------|
| Описание | [что включает/выключает] | [Статус] |
| Тип | [Release / Experiment / Ops / Permission] | [Статус] |
| Владелец | [команда / человек] | [Статус] |
| Дата создания | [YYYY-MM-DD] | [Статус] |
| Планируемая дата удаления | [YYYY-MM-DD или — для Ops] | [Статус] |
| Значение по умолчанию | [true / false] | [Статус] |

Поведение:
| Состояние | Поведение | UI | API |
|-----------|----------|-----|-----|
| ON | [поведение] | [UI] | [контракт ответа] |
| OFF | [поведение] | [UI] | [контракт ответа] |

Зависимости:
| Тогл | Зависит от | Тип | Описание | Статус |
|------|-----------|-----|----------|--------|



| ID | Тип | Где в документе | Что предположено | Подтверждено? | Как закрыть |
|----|-----|-----------------|------------------|---------------|-------------|

План удаления:
| Этап | Действие | Ответственный | Срок |
|------|----------|---------------|------|
| 1 | [действие] | [роль] | [срок] |

Чек-лист верификации после раскатки:
|---------|------------------------|-----------------------------------|----------|-------------------|
| [метрика] | [порог] | [порог] | [Grafana / Prometheus / Analytics / Support] | [период] |

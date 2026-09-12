<!--
Imported from: acceptance-test-standard-kit/examples\operation-sorting-acceptance-example.md
Current-state adaptation:
- Use only confirmed current behavior.
- Do not write TO BE, rollout/rollback, future requirements, design proposals, GAP/ASM/DESIGN markers as reader-facing content.
- Put unresolved or future/change-specific material into working-layer gaps, not into permanent KB pages.
-->
#### Acceptance Tests — Сортировка истории событий по дате изменения

**Контекст тестирования:**

| Элемент | Значение |
|---|---|
| Фича | Изменить сортировку истории событий |
| Source requirements | `01-Requirements/sort-operations-requirements.md` |

**Coverage matrix:**

| Requirement / rule | Covered by scenarios | Gap |
|---|---|---|
| Операции сортируются по дате изменения | ACC-001 | — |

**Acceptance scenarios:**

| ID | Requirement / Use Case | Given | When | Then | Тип | Статус |
|---|---|---|---|---|---|---|

**Negative и edge cases:**

| ID | Requirement / Use Case | Given | When | Then | Тип | Статус |
|---|---|---|---|---|---|---|

**Test data:**

| Data item | Значение / правило | Источник | Статус |
|---|---|---|---|

**Regression scope:**

| Область | Что проверить | Причина |
|---|---|---|
| История событий | Фильтры и пагинация сохраняют корректную сортировку | Sorting can affect pagination |
| API/UI contract | UI получает поле даты изменения | Dependency on contract |

**Gaps и допущения:**

| ID | Где найдено | Что неизвестно / что предположено / что спроектировано | Как закрыть |
|---|---|---|---|

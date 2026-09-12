<!--
Imported from: migration-standard-kit/templates\migration-plan.template.md
Current-state adaptation:
- Use only confirmed current behavior.
- Do not write TO BE, rollout/rollback, future requirements, design proposals, GAP/ASM/DESIGN markers as reader-facing content.
- Put unresolved or future/change-specific material into working-layer gaps, not into permanent KB pages.
-->
#### Миграция — [Название фичи]

**Контекст миграции:**

| Элемент | Значение |
|---|---|
| Фича | [Название] |

**Scope и зависимости:**

| Объект | Изменение | Зависимости | Статус |
|---|---|---|---|

**Pre-checks:**

| Проверка | Метод | Ожидаемый результат | Blocking |
|---|---|---|---|
| [Проверка] | [SQL/query/tool] | [Результат] | [yes/no] |

**План миграции:**

| Фаза | Действие | Тип | Совместимость | Owner | Статус |
|---|---|---|---|---|---|

**Backfill:**

| Элемент | Значение |
|---|---|
| Источник данных | [Источник] |
| Идемпотентность | [Как обеспечивается] |
| Retry | [Правило] |
| Throttling | [Правило] |

**Validation:**

| Проверка | Метод | Ожидаемый результат | Blocking |
|---|---|---|---|
| [Проверка количества строк] | [SQL/query] | [Ожидаемый результат] | yes |


|---|---|---|---|
| [Ошибка DDL] | [Действие] | [Да/нет] | [Ограничения] |
| [Ошибка backfill] | [Действие] | [Да/нет] | [Ограничения] |

**Риски и ограничения:**

| Риск | Влияние | Митигация | Статус |
|---|---|---|---|
| [Риск] | [Impact] | [Mitigation] | [confirmed/GAP] |

**Gaps и допущения:**

| ID | Где найдено | Что неизвестно / что предположено / что спроектировано | Как закрыть |
|---|---|---|---|

<!--
Imported from: migration-standard-kit/examples\payment-status-backfill-migration-example.md
Current-state adaptation:
- Use only confirmed current behavior.
- Do not write TO BE, rollout/rollback, future requirements, design proposals, GAP/ASM/DESIGN markers as reader-facing content.
- Put unresolved or future/change-specific material into working-layer gaps, not into permanent KB pages.
-->
#### Миграция — Добавить статус платежа к заказам

**Контекст миграции:**

| Элемент | Значение |
|---|---|
| Фича | Добавить систему платежей к заказам |
| Data model artifact | `03-Data/payment-processing-data-model.md` |

**Scope и зависимости:**

| Объект | Изменение | Зависимости | Статус |
|---|---|---|---|

**Pre-checks:**

| Проверка | Метод | Ожидаемый результат | Blocking |
|---|---|---|---|
| Проверить объем `orders` | SQL count/size query | Значение известно до планирования batch | yes |
| Проверить отсутствие таблицы `payments` | metadata query | Таблица отсутствует | yes |

**План миграции:**

| Фаза | Действие | Тип | Совместимость | Owner | Статус |
|---|---|---|---|---|---|

**Backfill:**

| Элемент | Значение |
|---|---|

**Validation:**

| Проверка | Метод | Ожидаемый результат | Blocking |
|---|---|---|---|
| Нет заказов с неконсистентным payment_status | SQL validation query | 0 строк | yes |
| Количество платежей соответствует источнику | reconciliation query | Расхождение в допустимых пределах | yes |


|---|---|---|---|
| Ошибка до записи новых платежей | Откатить DDL если возможно | Нет | Depends on DB/tool |
| Ошибка после записи новых платежей | Отключить чтение через current-state functionality toggle, сохранить данные | Нет | Полный DROP может потерять данные |

**Риски и ограничения:**

| Риск | Влияние | Митигация | Статус |
|---|---|---|---|

**Gaps и допущения:**

| ID | Где найдено | Что неизвестно / что предположено / что спроектировано | Как закрыть |
|---|---|---|---|

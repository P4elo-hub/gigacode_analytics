---
report_type: challenges-resolved
slug: bph-moex-tax
source_document: Feature-writing/bph-moex-tax/bph-moex-tax.md
challenges_document: Feature-writing/bph-moex-tax/bph-moex-tax-challenges.md
decisions_document: Feature-writing/bph-moex-tax/bph-moex-tax-decisions.md
session: 2
language: ru
---

# Карта закрытий challenges: bph-moex-tax

**Спецификация:** `Feature-writing/bph-moex-tax/bph-moex-tax.md`
**Банк:** `Feature-writing/bph-moex-tax/bph-moex-tax-challenges.md`
**Решения:** `Feature-writing/bph-moex-tax/bph-moex-tax-decisions.md`

## Сводка — сессия 2 (apply)

- Всего CH: 24
- **Covered (закрыто по spec/коду):** 8 — CH-04, CH-05, CH-06, CH-07, CH-09, CH-12, CH-16, CH-17
- **Resolved (по applied Decision):** 16 — CH-01, CH-02, CH-03, CH-08, CH-10, CH-11, CH-13, CH-14, CH-15, CH-18, CH-19, CH-20, CH-21, CH-22, CH-23, CH-24
- **needs-answer (ожидают ответа оркестратора):** 0
- **Осталось open:** 0
- SPEC в этой сессии **патчился** по applied Decision D-23…D-38 (все 16).

## Resolved — по applied Decision (сессия 2)

| ID | Verdict | Выбор | Решение | Затронутые § | Источник | Связанный Q |
|----|---------|-------|---------|--------------|----------|-------------|
| CH-01 | resolved | C | BR-10 снять как неприменимый к текущему объёму — правило удалено из spec | §1.1 (BR-10 удалён), §1.3, §4.1.1, §4.2.3 | D-23 | — |
| CH-02 | resolved | A | Формулировка ошибочна — «fallback → шаг 7», 6a/6b схлопнуты | §1.3 (alt 6a/6b) | D-27 | — |
| CH-03 | resolved | A | Ветка alt 3a убрана как недостижимая для `MOEX_TAX`; условие остаётся регресс-тестом | §1.3 (alt 3a), §4.2.2 | D-28 | — |
| CH-08 | resolved | A (уточнено) | Различение обеспечивается комментарием из `info` по `type`/`subtype`/`additionalType`; значение для `MOEX_TAX` добавляется в таблицу | §1.1 (BR-08), §1.3, §4.2.2 (шаг 8), §4.2.3 | D-29, D-31 | — |
| CH-10 | resolved | B | При `totalPrice = null` операция отбрасывается | §4.1.1 (request/`lead.total_sum`), §4.2.3 | D-30 | — |
| CH-11 | resolved | A | Как у `TAX_RETAIN` — валюта не переносится, сумма как есть | §4.1.1 (`lead.total_sum`), §4.2.3 (сравнение с `TAX_RETAIN`) | D-38 | — |
| CH-13 | resolved | Уточнено (не A) | Комментарий всегда из таблицы `info` по `type`/`subtype`/`additionalType` с подстановкой параметров; `accComment` — только при `null` в таблице; пустой комментарий не ожидается | §1.1 (BR-05/BR-09), §4.1.1, §4.2.2, §4.2.3, §7 | D-31 | — |
| CH-14 | resolved | B | SERIAL подтверждён; changeset вызывает `setval` после ручных `id` | §4.2.3 (Migration CS5, raw-SQL, занятые id) | D-24 | — |
| CH-15 | resolved | A | Rollback только по конкретным `${moexTax.*}` id (id-предикат) | §4.2.3 (CS1–CS4 rollback, Rollback table) | D-32 | — |
| CH-18 | resolved | A | Коллизия невозможна — `externalSystemId` глобально уникален между налогами | §4.1.1 (`lead.id`), §4.2.3 (сравнение с `TAX_RETAIN`) | D-25 | — |
| CH-19 | resolved | A | Окно мало/приемлемо, поведение как у существующих налогов; значение `updateDelayMs` — конфигурируемое/instance-specific | CN-08, §4.2.3 (кэш) | D-26 | — |
| CH-20 | resolved | A | Кэш читается одним SQL-снапшотом (`find_all_operations_v2.sql`) — частичное состояние невозможно | §4.2.3 («Как заполняется кэш») | D-33 | — |
| CH-21 | resolved | Штатный порядок | Набор INSERT делится на changeSet по обычной практике history-ops; спец. требований к атомарности нет | §4.2.3 (Backfill, порядок пролива) | D-34 | — |
| CH-22 | resolved | A | Детекция не требуется — поведение как у существующих налогов; разрез по `subtype` не вводится | §4.2.3 (Validation/приёмка) | D-35 | — |
| CH-23 | resolved | Штатный порядок | Отдельный лог/счётчик не вводится — поведение как у существующих налогов | §1.3 (alt 3a/4a), §4.2.2 (таблица развилок) | D-36 | — |
| CH-24 | resolved | A | Приёмка по общим правилам history-ops — отдельные acceptance-критерии и фикстуры не требуются | §4.2.3 (Validation, Test fixtures) | D-37 | — |

## Covered — закрыто по spec/коду (без правки SPEC, сессия 1)

| ID | Verdict | Severity | Обоснование (цитата § / источник) | Связанный Q |
|----|---------|----------|-----------------------------------|-------------|
| CH-04 | covered | Major | Статус-членство проверяется **всегда**: §2 (CN-10) и §4.2.2 (шаг 3) требуют наличия статуса в `status_and_general_status`; код `BphBcFilterService.isCommonOperationByBphContext()` всегда вычисляет `statusMap.containsKey(status)` в одном `return` с `bphActive()`/`bphType`/`bphSubtype` — досрочный `return true` относится к водоразделу, а не к статусу. Статус не из `statusMap` → операция отсеивается. | — |
| CH-05 | covered | Minor | `operation_type` (`operation.operation_type_id` → `Operation.toOperationTypeEnum()`) NOT NULL для записи `operation`; пустой/невалидный тип у найденной `bphActive`-записи в описанной миграции невозможен (§4.2.3, DDL `20241029_SIHIST-2774_1_create_operation.xml`). Клиент видит тип из кэша. | — |
| CH-06 | covered | Major | D-19 (`applied`): для `MOEX_TAX` поддерживается только `COMPLETE`; иные статусы не заводятся в `status_to_operation`, поэтому операция отсеивается шагом 3 — это осознанное поведение по D-19/D-09, не дефект. §2 (CN-10), §4.2.3 (допущение по набору статусов). | Q-16 |
| CH-07 | covered | Major | D-02 (`applied`) + §2 (CN-09) + §4.2.2 (шаг 2): при `bc_id=NULL` ветка проверки `additionalType` не применяется (ранний `return true` в `isActualBphOperation()` при единственной стороне). Асимметрия `TAX_RETAIN` vs `MOEX_TAX` зафиксирована. | Q-09 |
| CH-09 | covered | Major | §4.2.3: все 4 строки `info` вставляются **одним** changeSet (CS3), а Validation-шаг проверяет наличие 4 строк `info` с `Blocking=yes` → частичный набор блокирует пролив. Усечённый `additionalTypes[]` недопустим штатным конвейером. | — |
| CH-12 | covered | Major | `info.displayed_name` — nullable (`20241029_SIHIST-2774_3_create_info.xml`), во всех существующих кэш-записях (в т.ч. `TAX_RETAIN`, `TAX_REFUND_BROK_ACCOUNT`) `displayed_name: null`; NULL от нового налога — существующее ожидаемое состояние, не дефект. | — |
| CH-16 | covered | Major | §4.2.3 Pre-checks: проверяется не только существование, но и соответствие — `SELECT id,name,general_status_id FROM history_ops.status WHERE id=19` с ожиданием `COMPLETE`→`general_status_id=1`; несоответствие блокирует пролив. | Q-16 |
| CH-17 | covered | Minor | На `info` нет UNIQUE-констрейнта (`20241029_SIHIST-2774_3_create_info.xml`); PK по `id`. Одинаковый `comment` у четырёх строк допустим (прецедент — существующие строки `info` с общим текстом). | — |

## Отложено

| ID | Проблема | Причина отсрочки | Связанный CH |
|----|----------|------------------|--------------|
| — | — | — | (нет) |

## Следующий шаг

- Все 24 `CH-*` закрыты (16 `resolved`, 8 `covered`); `needs-answer` и `open` — 0.
- SPEC поправлен по всем applied Decision D-23…D-38.
- Рекомендуемый следующий шаг пайплайна: `/check-feature` (SPEC изменён) →
  `/check-feature-code` (затронуты контракты/БД: `setval`, rollback-предикаты,
  модель `info`, маппинг `comment`/`total_sum`).
- **Флаг (D-26):** конкретное значение `updateDelayMs` в коде не найдено и не
  выдумано; CN-08 фиксирует значение как конфигурируемое/instance-specific
  (`OperationCacheLoaderProperties.java:7-8`). Требует уточнения человеком, если
  нужен конкретный таймаут в spec.

---
report_type: gaps-resolved
slug: og-trading-order-yield
source_document: Feature-writing/og-trading-order-yield/og-trading-order-yield.md
context_document: Feature-context/og-trading-order-yield.md
generated_at: 2026-06-18
session: 3
---

# Карта закрытых gaps: og-trading-order-yield

**Спецификация:** `Feature-writing/og-trading-order-yield/og-trading-order-yield.md`
**Карта:** `Feature-writing/og-trading-order-yield/og-trading-order-yield-gaps-resolved.md`

## Сводка

- Открытых GAP в SPEC (на входе): **98** уникальных id (≈242 inline-упоминания)
- Закрыто по источникам (батч 1, сессия 2): **61 GAP** (7 кластеров, D-01…D-07)
- Переведено в `needs-answer` (батч 1, blocker-кластеры): **7 кластеров / 61 GAP** → `applied`
- Закрыто по решениям (батч 2, сессия 3): **37 GAP** (11 кластеров, D-08…D-18) → `applied`
- Остаётся открытых GAP в SPEC: **0**

> Причина нулевого «закрыто по источникам»: в `analytics/` нет документа о
> «доходности» (`grep -i 'доходност|yield|profitab' analytics/` — совпадений нет),
> источник значения в аналитике не описан, а факты о значении/формате/уровне поля
> приходят только от владельцев контрактов (ОГ, screen-api) и продукта. Скилл
> `resolve-gaps` запрещает выдумывать факты: нет источника → только `needs-answer`.
> Батч 2 закрыт по решениям пользователя (D-08…D-18), а не по новым источникам.

## Сессия 1 (2026-06-18)

Правило батча (skill `resolve-gaps`): открытых GAP > 15 → только батч 1
(blocker-кластеры: контракт, UC, BR), записать `needs-answer`, стоп.

| Кластер | Действие | Затронутые § (при apply) | Связанные Q | DECISIONS |
|---------|----------|--------------------------|-------------|-----------|
| Формат/тип/имя поля (OG vs BPH `PriceData`) | `needs-answer` | §1.1, §2 (CN/ASM), §4.1.1 (proto OG, REST, gRPC), §4.2.3, §4.2.4 (маппинг) | Q-01, Q-03 | D-01 |
| Уровень размещения поля (lead vs детали) + BDUI | `needs-answer` | §4.1.1.3, §4.2.2, §4.2.3 | Q-04 | D-02 |
| Источник значения (кто вычисляет) + транзитность | `needs-answer` | §1.2, §1.3, §2 (ASM-01), §4.2.2, §4.2.3 | Q-02, Q-05, Q-07 | D-03 |
| Scope (активные заявки) + фиче-тогл | `needs-answer` | §1.2.1, §1.3.1, §2, §5.5 | Q-06, Q-08 | D-04 |
| Merge с BPH + отсутствующее/нулевое/отрицательное | `needs-answer` | §1.3.1, §2, §4.1.1, §4.2.2, §4.2.4 | Q-07 | D-05 |
| SMART: метрика и срок/релиз | `needs-answer` | §1.1 | — | D-06 |
| Готовность контракта ОГ + ребилд + перечень слоёв | `needs-answer` | §2 (CN-02, CN-04), §4.2.4, §4.1.1.2 | Q-09 | D-07 |

### Полный Relates по кластерам (batches: все GAP-id)

| Кластер | GAP-id в Relates |
|---------|------------------|
| Формат/тип/имя (D-01) | GAP-GOAL-03, GAP-GOAL-05, GAP-CONS-04, GAP-CONS-05, GAP-INT-04, GAP-INT-05, GAP-DM-02, GAP-DM-03, GAP-MAP-01, GAP-MAP-02, GAP-UCTB-02, GAP-ALG-02 |
| Уровень/BDUI (D-02) | GAP-CONS-05a, GAP-INT-14, GAP-ALG-07, GAP-MAP-04, GAP-MAP-05, GAP-GOAL-08, GAP-UCTB-04, GAP-ALG-06, GAP-DM-04, GAP-INT-15, GAP-NFR-09 |
| Источник значения + транзит (D-03) | GAP-GOAL-04, GAP-UCAS-02, GAP-UCTB-01, GAP-ALG-01, GAP-CONS-03, GAP-DM-01, GAP-MAP-10, GAP-NFR-16 |
| Scope + тогл (D-04) | GAP-GOAL-06, GAP-UCAS-06, GAP-UCTB-06, GAP-CONS-07, GAP-INT-08, GAP-ALG-05, GAP-MAP-09, GAP-NFR-20 |
| Merge/отсутствие значения (D-05) | GAP-UCAS-03, GAP-UCTB-03, GAP-CONS-06, GAP-ALG-03, GAP-CONS-09, GAP-ALG-04, GAP-INT-06, GAP-MAP-08, GAP-GOAL-07 |
| SMART (D-06) | GAP-GOAL-01, GAP-UCAS-01, GAP-GOAL-02 |
| Контракт/ребилд (D-07) | GAP-CONS-01, GAP-CONS-10, GAP-CONS-08 |

## Сессия 2 (2026-06-18) — apply батча 1

Правило (skill `resolve-gaps`): Decision есть в `DECISIONS` для всех Relates —
применить ко **всем** GAP кластера, переписать §, удалить следы `[GAP-...]`.
Status → `applied`.

| ID | Выбор | Решение (кратко) | Затронутые § | Связанные Q | Status |
|----|-------|------------------|--------------|-------------|--------|
| D-01 | B | Поле — объект `{value, currency}` (`PriceData`), имя `yield`; OG приведён к объекту; плоские `google.type.Decimal`/`number`/`double` заменены | §1.3 (preconditions), §1.3.1 (примечания по контрактам), §4.2.4 (lineage + field-mapping) | Q-01, Q-03 | applied |
| D-02 | A | Уровень lead `HistoryOperationLead`; детали `ReportOrderOperationDetails` для доходности не используются; composite/BDUI секция не меняется | §1.3 (main scenario, «Изменения»), §4.2.4 (lineage, BDUI), §5.2 (NFR-09) | Q-04 | applied |
| D-03 | A | ОГ отдаёт готовое значение; `history-ops` читает/пробрасывает; поле транзитное, схема БД без миграций | §1.3 (preconditions, main scenario, «Изменения»), §5.4 | Q-02, Q-05, Q-07 | applied |
| D-04 | A | Scope — только `GetTradeOrders` (история); активные заявки вне scope; отдельного фиче-тогла нет | §1.3 (blockquote), §1.3.1, §5.5 (NFR-20) | Q-06, Q-08 | applied |
| D-05 | A | Приоритет ОГ; нет значения в ОГ → подмешивание из BPH linked events; иначе поле `null`/опускается; `0` отображается; отрицательные допускаются | §1.3 (postconditions, main scenario, alt 3a, примечания), §5.2 (graceful degradation) | Q-07 | applied |
| D-06 | C | Релиз — как у симметричной BPH-фичи `bph-linked-events-yield`; отдельная количественная метрика не задаётся | §1.1 | Q-01 | applied |
| D-07 | C (проектный порядок) | `history-ops` разрабатывает первыми, контракт задаётся этой аналитикой; OG реализует после; версии proto с полем нет; слои `history-ops` подтверждены | §2 (CN), §4.1.1.2, §4.2.4 | Q-09 | applied |

**Итог apply:** закрыто **61 GAP** из 98; следы `[GAP-...]` удалены из SPEC (не помечены «закрыт»); строки пустых блоков «Gaps и допущения» удалены; подтверждённые Допущения переведены в текст §.

## Отложено (батч 2 — после apply батча 1)

| ID | Причина |
|----|---------|
| GAP-INT-01 | Контрактные детали (`GetTradeOrders` SLA/timeout/retry) — не blocker; уточняется после формата поля |
| GAP-INT-02, GAP-INT-03 | gRPC metadata запроса/ответа — контрактные детали |
| GAP-INT-07 | Полный набор gRPC-кодов `GetTradeOrders` — контрактные детали |
| GAP-INT-09, GAP-INT-10, GAP-INT-11 | DB/cache, `OrderMerger`, парсинг — детали apply на коде |
| GAP-INT-12, GAP-INT-13 | REST/gRPC детали исходящего контракта — зависят от D-01/D-02 |
| GAP-UCAS-04, GAP-UCAS-05 | Тайминги/имена вызовов AS IS — детали кода |
| GAP-UCTB-05, GAP-UCTB-07 | Отсутствие значения/перечень слоёв — зависят от D-03/D-05 |
| GAP-ALG-04, GAP-ALG-08 | Отсутствие значения, БД — зависят от D-03/D-05 |
| GAP-MAP-03, GAP-MAP-06, GAP-MAP-07 | Детали lineage (типы, номер 99, BDUI) — зависят от D-01/D-02 |
| GAP-NFR-01…GAP-NFR-08, GAP-NFR-10…GAP-NFR-15, GAP-NFR-17…GAP-NFR-19 | NFR-блок (безопасность, производительность, настройки) — отдельный прогон после apply батча 1 |
| GAP-OBS-01…GAP-OBS-09 | Наблюдаемость (логи/метрики) — отдельный прогон |

## Сессия 3 (2026-09-12) — apply батча 2

Правило (skill `resolve-gaps`): Decision есть в `DECISIONS` для всех Relates —
применить ко **всем** GAP кластера, переписать §, удалить следы `[GAP-...]`.
Status → `applied`.

| ID | Выбор | Решение (кратко) | Затронутые § | Связанные Q | Status |
|----|-------|------------------|--------------|-------------|--------|
| D-08 | A | Контракт `GetTradeOrders` as-is: deadline `grpc.order_gateway.deadline` (тест 50000 ms), retry — стандартный gRPC-клиент, metadata без доп. заголовков, коды по факту кода; SLA/p85 — отдельным запросом эксплуатации | §4.1.1.1 (таблица вызова, gRPC-коды) | Q-09 | applied |
| D-09 | A | Merge доходности: непустая ОГ побеждает; пустая → из BPH; `PriceData` без трансформации в исходящий контракт | §4.1.1.2 (алгоритм обработки) | Q-03, Q-07 | applied |
| D-10 | A | BDUI: отдельная секция карточки заявки, формат «{value} {currency}», знак как есть | §1.3 (BDUI), §4.1.1.3, §4.2 (lineage), §5.1 | Q-04 | applied |
| D-11 | A | Контрактные имена: поле `yield` типа `PriceData`, свободный номер **99**, lead `HistoryOperationLead`; внутренние сигнатуры/классы не описываются | §4.2 (lineage) | Q-01, Q-04 | applied |
| D-12 | D | Только алгоритм, без классов/внутренних ДТО: §1.2 AS IS и §4.1.1.2 — процессно, без имён методов и таймингов; имена полей контрактов остаются | §1.2 (AS IS), §4.1.1.2 | Q-08, Q-09 | applied |
| D-13 | A | Ошибка чтения доходности не влияет на отдачу заявки: WARN, поле опускается; других потребителей нет | §1.3 (изменения), §2 | Q-07, Q-09 | applied |
| D-14 | A | §5.1: новых прав/ролей и аудит-события нет; доступ — существующая фильтрация заявок; доходность не PII/секрет; канал — стандартный TLS | §5.1 | Q-04 | applied |
| D-15 | A | §5.2: фича не влияет на нагрузку — требования остаются as-is, новых числовых целей нет | §5.2 (производительность, надёжность) | Q-09, Q-04 | applied |
| D-16 | C | §5.2: ёмкость/лимиты без изменений относительно AS IS | §5.2 (ёмкость/лимиты) | Q-09 | applied |
| D-17 | A | §5.4: зафиксированы as-is тестовые значения + пометка «prod подтвердить у эксплуатации/SRE» | §5.4 | Q-09 | applied |
| D-18 | A | §5.3: новых error/бизнес-метрик и фронтовых UI-событий нет; логирование по существующей схеме; атрибуты стенда по образцу kit; трассировка — существующий `traceId` | §5.3 (логирование, метрики) | Q-02, Q-04, Q-07 | applied |

### Полный Relates по кластерам (батч 2)

| Кластер | GAP-id в Relates |
|---------|------------------|
| Контракт `GetTradeOrders` (D-08) | GAP-INT-01, GAP-INT-02, GAP-INT-03, GAP-INT-07 |
| Merge OG+BPH (D-09) | GAP-INT-10, GAP-INT-11 |
| BDUI-секция (D-10) | GAP-INT-15, GAP-MAP-07 |
| Контрактные имена/lineage (D-11) | GAP-MAP-03, GAP-MAP-06 |
| AS IS — алгоритм (D-12) | GAP-UCAS-04, GAP-UCAS-05 |
| Ошибка чтения (D-13) | GAP-UCTB-05, GAP-UCTB-07 |
| Безопасность (D-14) | GAP-NFR-01, GAP-NFR-02, GAP-NFR-03 |
| Производительность/надёжность (D-15) | GAP-NFR-04, GAP-NFR-05, GAP-NFR-06, GAP-NFR-07, GAP-NFR-08, GAP-NFR-09, GAP-NFR-15 |
| Ёмкость/лимиты (D-16) | GAP-NFR-10, GAP-NFR-11, GAP-NFR-12, GAP-NFR-13, GAP-NFR-14 |
| Prod-конфигурация (D-17) | GAP-NFR-17, GAP-NFR-18 |
| Наблюдаемость (D-18) | GAP-OBS-01, GAP-OBS-02, GAP-OBS-03, GAP-OBS-04, GAP-OBS-05, GAP-OBS-06, GAP-OBS-07, GAP-OBS-08, GAP-OBS-09 |

**Итог apply батча 2:** закрыто **37 GAP** из отложенных; следы `[GAP-...]` и
блоки «Gaps и допущения» удалены из SPEC (не помечены «закрыт»); закрытые
вопросы дописаны в `CONTEXT_DOC` §«Закрытые вопросы». Открытых GAP в SPEC — **0**.

> Отмечено при apply: `GAP-NFR-16`, `GAP-NFR-19`, `GAP-NFR-20` (Relates D-03/D-04)
> были закрыты в сессии 2 вместе с кластерами батча 1; в SPEC следов не осталось.
> `GAP-INT-09`, `GAP-INT-12`, `GAP-INT-13`, `GAP-ALG-04`, `GAP-ALG-08` не имели
> собственных решений в D-08…D-18 и были сняты как производные от закрытых
> кластеров (D-08/D-09/D-15) — их контрактные/алгоритмические детали покрыты
> решениями соответствующих кластеров.

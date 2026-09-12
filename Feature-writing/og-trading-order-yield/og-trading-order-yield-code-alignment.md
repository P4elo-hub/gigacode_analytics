---
report_type: code-alignment
slug: og-trading-order-yield
source_document: Feature-writing/og-trading-order-yield/og-trading-order-yield.md
generated_at: 2026-09-13
alignment_iteration: 3
scope: repositories/ only (read-only; code = source of truth)
language: ru
verdict: PASS WITH GAPS
critical_major_mismatch: 0
---

# Code alignment — `og-trading-order-yield`

Аудит соответствия спецификации фактическому коду (`repositories/`). Код —
источник истины. Отчёт — единственный артефакт, который создаётся этим шагом;
`SPEC` и код не правились.

**Итерация alignment: 3 из 3.**

> **Вердикт ПЕРЕСЧИТАН** из текущего текста `SPEC` (не унаследован от итерации 2).
> Предыдущий `verdict: FAIL` / Major MISMATCH = 2 относился к редакции `SPEC` **до**
> применения D-30…D-34 и на текущий текст не распространяется.

## Управляющие решения (учтены в вердикте)

| ID | Решение | Как учтено в отчёте |
|----|---------|---------------------|
| **D-07** | Команда ОГ реализует контракт **после** `history-ops` и ровно те поля, что описаны в спеке; спека — источник истины для контракта ОГ | Отсутствие `yield`/`PriceData` в текущем `order-gateway.proto` — ожидаемое **NOT FOUND (expected, TO BE)**, на вердикт **не влияет** |
| **D-12** | Аналитика описывает только алгоритмы, без классов/внутренних DTO разработки | Наличие имён классов в колонках «evidence» — намеренные code-якоря, не находка. Отсутствие классов в нарративе не является пробелом |
| **D-26** | Синхронизация BPH-спеки (`bph-linked-events-yield`) **не выполняется**; расхождение = принятый риск; OG-релиз не блокируется | Расхождение OG/BPH формата `yield` — документированный риск (CN-15, ASM-03, EC-13/EC-14, AC-17), **не** дефект. BPH-спека не читалась и не редактировалась |
| **D-27** | Fallback на BPH не гейтится отдельным тоглом | CN-16/EC-12 фиксируют: при выключенном BPH-пути поле остаётся `null`. Сверено с кодом (см. B-04) |

## Сводка

| Показатель | Значение |
|------------|----------|
| CONFIRMED | 32 |
| MISMATCH (Critical) | 0 |
| MISMATCH (Major) | 0 |
| MISMATCH (Minor) | 0 |
| NOT FOUND (expected, TO BE) | 5 |
| UNVERIFIABLE | 2 |
| **Critical MISMATCH** | **0** |
| **Major MISMATCH** | **0** |
| **Вердикт** | **PASS WITH GAPS** |

Вердикт повышен с `FAIL` (итерация 2) до **`PASS WITH GAPS`**: все Critical/Major
MISMATCH предыдущей редакции **фактически закрыты** правкой `SPEC` (батч D-30…D-34),
что подтверждено сверкой текущего текста `SPEC` с кодом. Остаются только
ожидаемые **NOT FOUND (expected, TO BE)** по D-07 и **UNVERIFIABLE** — они вердикт
не понижают (правило скилла: TO BE NOT FOUND → PASS WITH GAPS, а не FAIL).

## Верификация закрытия находок итерации 2 (рекомендованных к закрытию)

Сверка каждой closure-находки итерации 2 с **текущим** текстом `SPEC` и с кодом
(не с намерением).

| Finding (итер. 2) | Severity | Claim в `SPEC` (текущий текст) | Evidence (файл:строка) | Статус |
|-------------------|----------|--------------------------------|------------------------|--------|
| **F-01 / I-05** — `ex_system` | было Major | §1.3, §4.1.1.3, §5.1 (аудит-таблица), §5.3: `ex_system` / `exSystem` = **`OG`**; литерал `ORDER_GATEWAY` в `SPEC` отсутствует | `counter/adapter/GetTradeOrdersGateway.java:46` → `return "OG";`; `counter/adapter/GetActiveOrdersGateway.java:46` → `return "OG";`; `service/matcher/OrderEnricher.java:22` → `private static final String OG = "OG";`; Prometheus-фикстуры: `ex_system="OG"` для `event_type="GET_TRADE_ORDERS"` (`prometheus_metrics_feed_screen_negotiated.txt:42,45` и др.); значение `"ORDER_GATEWAY"` как label в `repositories/` отсутствует | **CLOSED (CONFIRMED)** |
| **F-02 / T-06** — `bphGetLinkedEvents.active` | было Major | §5.4 (таблица настроек): ключ `app-config-dynamic.instrument-filter-requests-dynamic.bphGetLinkedEvents.active`; §5.5: `bphGetLinkedEvents.active` **отсутствует** в таблице Auth-тоглов; в §5.5 явная фраза «не является Auth-тоглом» | `adapter/RpcNamesForRequestCondition.java:11` → `BPH_GET_LINKED_EVENTS("bphGetLinkedEvents")` — ConfigMap-ключ (`getConfigMapKey()`); `adapter/bph/linked_events/BphLinkedOperationsGateway.java:146` → `RpcNamesForRequestCondition.BPH_GET_LINKED_EVENTS.getConfigMapKey()`; `application-test.yml:70-74` → ключ под `app-config-dynamic.instrument-filter-requests-dynamic`; `CounterFeatureToggleName.java` (Auth-тоглы) — `bphGetLinkedEvents` **отсутствует** | **CLOSED (CONFIRMED)** |
| **F-03 / C-10** — `PriceData` | было Minor | §4.1.1.1 (примечание к proto) и §4.1.1.3: форма `PriceData {value, currency}` совпадает с существующим `PriceData` в `bph.yml` (1226–1240); имя пакета — за владельцем контракта (D-21) | `swagger/bph/bph.yml:1226` → `PriceData:` (секция схемы); используется в `bph.yml:1118,1120`; Java-тип `adapter/bph/PriceData` (`BphLinkedTradeOrderBaseConverterForTrades.java:8`) | **CLOSED (контекст, не противоречие)** |
| **F-04** — doc cross-refs | было Minor | Ссылки `§4.2.3` / `§4.2.4` в `SPEC` **отсутствуют**; используются текстовые названия «Модель данных» / «Маппинг данных» | grep по `SPEC` (`§4.2.3|§4.2.4`): 0 совпадений; заголовки «Модель данных» / «Маппинг данных» без номеров; нумерован только `#### 4.2.2.` | **CLOSED (doc)** |
| **F-05 / I-07** — регистр `serviceName` | было Minor | §5.5: `serviceName` = `history_ops` (нижний регистр) во всех упоминаниях | `adapter/auth/SessionServiceGateway.java` → `SERVICE_NAME = "history_ops"`; `HISTORY_OPS` как `serviceName` в `SPEC` отсутствует | **CLOSED (CONFIRMED)** |

## Находки — полный реестр (по категориям)

### 1. Контракты

| # | Severity | Claim (секция SPEC) | Evidence | Статус |
|---|----------|---------------------|----------|--------|
| C-01 | Info | §4.1.1.1: входящий gRPC — package `com.sberbank.si20.trade.operations.api.order.gateway.v1`, service `OrdersService`, rpc `GetTradeOrders` | `order-gateway.proto`: package/service/rpc совпадают (`service OrdersService { rpc GetTradeOrders ... }`) | **CONFIRMED** |
| C-02 | Info | §4.1.1.1/ASM-02: свободный номер нового поля `yield` = **42**, последнее занятое — 41 | `order-gateway.proto`: `optional string card_number = 41;` — последнее поле `TradeOrder`; 42 свободен | **CONFIRMED** |
| C-03 | — | §4.1.1.1/CN-10/AC-04: `optional PriceData yield = 42;` в `TradeOrder` | `order-gateway.proto` — полей `PriceData`/`yield` нет | **NOT FOUND (expected, TO BE)** по D-07 |
| C-04 | Info | §4.1.1.3/AC-04: `historyOperationDetails.proto` — последнее занятое 98 (`auto_follow`), новое `yield` = **99** | `historyOperationDetails.proto`: `optional bool auto_follow = 98;` — последнее; 99 свободен; `card_number = 96`, `trd_forced_close = 97` | **CONFIRMED** |
| C-05 | Info | §4.1.1.3: группа `// REPORT ORDER OPERATION` = поля 65–98 | `historyOperationDetails.proto`: `// REPORT ORDER OPERATION` → `optional double commission_value = 65;` … `optional bool auto_follow = 98;` | **CONFIRMED** |
| C-06 | — | §4.1.1.3/AC-04: `optional PriceData yield = 99;` + import `.../common/v1/price_data.proto` | В `historyOperationDetails.proto` нет `yield` и нет import `price_data.proto`; файла `price_data.proto` в `repositories/` нет | **NOT FOUND (expected, TO BE)** |
| C-07 | Info | §4.1.1.3: REST `ReportOrderOperationDetails` — 32 поля, `yield` отсутствует (as-is) | `swagger/history/history.yml:376` → `ReportOrderOperationDetails:`; последнее поле группы — `auto_follow` (стр. 454); `yield` нет | **CONFIRMED** |
| C-08 | Info | §4.1.1.3: REST `HistoryOperationLead` — 18 полей (id…channel), новое `yield` на уровне lead | `history.yml:456` `HistoryOperationLead:` — `id`…`channel` (18 полей); `yield` отсутствует | **CONFIRMED (18 полей); `yield` → NOT FOUND (expected, TO BE)** |
| C-09 | Info | §4.1.1.3: `HistoryOperationBase` собирает lead через `JsonUnwrapped` | `history.yml:517` → `allOf: - $ref '#/components/schemas/HistoryOperationLead'` (`@JsonUnwrapped`) | **CONFIRMED** |
| C-10 | Info | §4.1.1.1/D-21: `PriceData {value, currency}` — единый общий тип, дублирование запрещено | `swagger/bph/bph.yml:1226-1240` — уже существует `PriceData` (форма идентична) | **CONFIRMED (контекст; см. F-03 CLOSED)** |

### 2. БД и миграции

| # | Severity | Claim (секция SPEC) | Evidence | Статус |
|---|----------|---------------------|----------|--------|
| D-01 | Info | «Модель данных»/ASM-01/AC-15: схема БД `history-ops` не меняется; доходность — транзитное поле | В `db/changesets/` нет changeset под `yield`; колонки доходности нет | **CONFIRMED** |
| D-02 | Info | «Модель данных»: таблица `operation` — `operation_type_id`, `bc_id`, `bph_id`, `name`, PK `id` | `20241029_SIHIST-2774_7_create_operation.xml` — состав колонок совпадает точно | **CONFIRMED** |
| D-03 | Info | «Модель данных»: все перечисленные таблицы (`bc`, `bph`, `info`, `status`, `status_to_operation`, `type`, `general_status`, `operation_type`, `operation`, `cancellation_bph`, `active_ops_count_systems`) существуют | changelog `db/changesets/` — все перечисленные changeset присутствуют | **CONFIRMED** |
| D-04 | — | «Модель данных»: изменение схемы под персистентность доходности где-либо | Следов не найдено (ожидаемо по Q-05/ASM-01: доходность не персистится) | **NOT FOUND (expected)** |

### 3. Интеграции

| # | Severity | Claim (секция SPEC) | Evidence | Статус |
|---|----------|---------------------|----------|--------|
| I-01 | Info | §4.1.1.1/§5.1: OG-клиент — `OrderGrpcGateway`, `enabled() = true`, `extract()`, `grpcIntegration()` | `adapter/order_gateway/OrderGrpcGateway.java`: `enabled()` → `true`; `extract()` → `GetTradeOrdersResponse::getOrdersList`; `grpcIntegration()` → `GrpcProperties::orderGateway` | **CONFIRMED** |
| I-02 | Info | §5.1: `ruleKey()` — `RpcNamesForRequestCondition.OG_GET_TRADE_ORDERS.getConfigMapKey()` | `RpcNamesForRequestCondition.java:9` → `OG_GET_TRADE_ORDERS("ogGetTradeOrders")` | **CONFIRMED** |
| I-03 | Info | §5.1/§4.1.2: `rpcName()` счётчика = `RpcNameConstants.OG_ORDERS` (= `GetTradeOrders`) | `counter/RpcNameConstants.java` → `OG_ORDERS = "GetTradeOrders"` | **CONFIRMED** |
| I-04 | Info | §4.1.2/EC-*: ошибка вызова OG → WARN-лог + `history_ops_integration{status="error"}` | `counter/adapter/AbstractActiveOpsGrpcGateway.java` → `getOperationsSafe` onErrorResume → `logWarnForCounter(...)` + `countIntegrationDataCompleteFalse(...)` | **CONFIRMED** |
| I-05 | Info | §5.3/§5.1: `ex_system = OG` при логировании/метриках OG-вызовов | `GetTradeOrdersGateway.java:46` / `GetActiveOrdersGateway.java:46` → `"OG"` | **CONFIRMED (F-01 закрыт)** |
| I-06 | Info | §5.5: авторизация — `SessionServiceGateway.getSession(traceId, sessionId, ucpId)` | `adapter/auth/SessionServiceGateway.java` → `getSession(traceId, sessionId, ucpId)`; `SERVICE_NAME = "history_ops"` | **CONFIRMED** |
| I-07 | Info | §5.5: `serviceName = history_ops` (нижний регистр) | `SessionServiceGateway.SERVICE_NAME = "history_ops"` | **CONFIRMED (F-05 закрыт)** |

### 4. Конфигурация

| # | Severity | Claim (секция SPEC) | Evidence | Статус |
|---|----------|---------------------|----------|--------|
| K-01 | Info | §5.4: `grpc.order_gateway.target`, `grpc.order_gateway.deadline` | `application-test.yml`: `grpc.order_gateway.target: localhost:${grpcmock.server.port}`, `deadline: 50000`; `GrpcProperties(prefix="grpc")` | **CONFIRMED** |
| K-02 | Info | §5.4: динамический фильтр `app-config-dynamic.instrument-filter-requests-dynamic.ogGetTradeOrders` | `application-test.yml:70-71` → `ogGetTradeOrders:` (`active`/`inactive`); `OriginalInstrumentWithItsVersionsRequestsConfigMapTest.java:30-31` | **CONFIRMED** |
| K-03 | Info | §5.4: `app-config.counter.sourceConfigMapDefaultValue` содержит `rpc_name=GetTradeOrders` | `application-test.yml` → `app-config.counter.sourceConfigMapDefaultValue` → `rpc_name=GetTradeOrders` | **CONFIRMED** |
| K-04 | Info | §5.4: `app-config.reporting.maxRecords = 100` как дефолт; лимит выборки | `application-test.yml` → `app-config.reporting.maxRecords: 100` | **CONFIRMED** |
| K-05 | Info | §5.4: конфиг тоглов/фильтров — ConfigMap (`app-config-dynamic`) | `application-test.yml` — ключи `app-config-dynamic.*`; `RpcNamesForRequestCondition.getConfigMapKey()` | **CONFIRMED** |
| K-06 | — | §5.4: значения конфигов **промышленного** контура | В `repositories/` присутствует только `application-test.yml`; prod values недоступны | **UNVERIFIABLE (D-17)** |
| K-07 | Info | §5.4: `app-config-dynamic.instrument-filter-requests-dynamic.bphGetLinkedEvents.active/inactive` — ключ ConfigMap, не Auth-тоггл | `application-test.yml:74` → `bphGetLinkedEvents:`; `RpcNamesForRequestCondition.java:11` → `BPH_GET_LINKED_EVENTS("bphGetLinkedEvents")` | **CONFIRMED (F-02 закрыт)** |

### 5. Feature toggles

| # | Severity | Claim (секция SPEC) | Evidence | Статус |
|---|----------|---------------------|----------|--------|
| T-01 | Info | §5.5: тогл `enableOrderGatewayRequestDates` (Sber Auth) | `CounterFeatureToggleName.java` → `ENABLE_ORDER_GATEWAY_REQUEST_DATES("enableOrderGatewayRequestDates")`; `SourcesGatewayService.java:38,112` | **CONFIRMED** |
| T-02 | Info | §5.5: тогл `enableOgNewActiveOrdersEndpoint` (Sber Auth) | `CounterFeatureToggleName.java` → `ENABLE_OG_NEW_ACTIVE_ORDERS_ENDPOINT("enableOgNewActiveOrdersEndpoint")` | **CONFIRMED** |
| T-03 | Info | §5.1: OG-клиент включён (`enabled() = true`) | `OrderGrpcGateway.enabled()` → `true` | **CONFIRMED** |
| T-04 | Info | §5.5: отсутствующий тогл трактуется как выключенный (`false`) + INFO-лог | `SessionServiceGateway` → при отсутствии тогла возвращается `false`, лог через `logMissingFeatureToggles` | **CONFIRMED** |
| T-05 | Info | D-27/CN-16: отдельного тогла под `yield` нет | `CounterFeatureToggleName.java` — тогла `yield` нет; в спеке тогл не заявлен | **CONFIRMED** |
| T-06 | Info | §5.5: набор Auth-тоглов = ровно `enableOrderGatewayRequestDates`, `enableOgNewActiveOrdersEndpoint`; `bphGetLinkedEvents.active` — **не** Auth-тогл | `CounterFeatureToggleName.java` — ровно эти два значения; `bphGetLinkedEvents` отсутствует | **CONFIRMED (F-02 закрыт)** |

### 6. Алгоритм и поведение

| # | Severity | Claim (секция SPEC) | Evidence | Статус |
|---|----------|---------------------|----------|--------|
| A-01 | Info | §4.2.2/BR-*: приоритет OG при слиянии (`hasOgDeals` → OG-операция; иначе BPH) | `service/conversion/operation/merger/TradeMerger.java` → `mergeOperation`: `if (hasOgDeals) { buildSyntheticOgOperation(...) } else if (isBphPresent) { … }` | **CONFIRMED** |
| A-02 | Info | §4.2.2: OG-операция собирается синтетически, префикс `og_deal_` | `TradeMerger` → `buildSyntheticOgOperation(...)`; `SYNTHETIC_OG_DEAL_PREFIX = "og_deal_"` | **CONFIRMED** |
| A-03 | Info | §4.2.2: сортировка результатов слияния — компаратор | `TradeMerger` → `resolveComparator` | **CONFIRMED** |
| A-04 | — | §4.2.2/BR-*: `yield` прокидывается в `HistoryOperationLead` при сборке OG-операции | `TradeMerger.buildSyntheticOgOperation` → `HistoryOperationLead.builder()` **без** `yield` — поля нет (TO BE) | **NOT FOUND (expected, TO BE)** |
| A-05 | — | «Маппинг данных»/AC-*: `DetailsResponseMapper` проставляет `yield` в ответе (в т.ч. `refreshFeed=false`, `setChevron(null)`) | `model/DetailsResponseMapper.java`: `refreshFeed = false`, `setChevron(null)`, `setCardNumber`, `setTrdForcedClose` — CONFIRMED; `setYield` — **отсутствует** (TO BE) | **NOT FOUND (expected, TO BE)** |
| A-06 | — | «Маппинг данных»/EC-*: неполный `PriceData` → трактуется как отсутствующее значение | В текущем коде `PriceData`/`yield` нет → проверить нельзя; логика — TO BE | **UNVERIFIABLE (TO BE)** |

### 7. Наблюдаемость и тесты

| # | Severity | Claim (секция SPEC) | Evidence | Статус |
|---|----------|---------------------|----------|--------|
| M-01 | Info | §5.3: метрика `history_ops_time` (Timer, теги ex_system/event_type, персентили) | `service/meter/service/MeterService.java` → `history_ops_time` Timer | **CONFIRMED** |
| M-02 | Info | §5.3: метрика `history_ops_integration` (Counter, теги ex_system/event_type/comment/status) | `MeterService` → `history_ops_integration` Counter с теми же тегами | **CONFIRMED** |
| M-03 | Info | §5.3: счётчик успешного ответа — `comment = ""` | `MeterService.countIntegration(...)` → comment `""` | **CONFIRMED** |
| M-04 | Info | §5.3: счётчик размера ответа — `comment = "response_size"` | `adapter/ListRequestService.java` → `countIntegration(exSystem, eventType, "response_size", list.size())` | **CONFIRMED** |
| M-05 | Info | §5.3/EC-*: ошибка парсинга → `comment = "parse_error"` + WARN | `ListRequestService.java` → `countIntegrationError(exSystem, eventType, "parse_error", ...)`; WARN `"Failed to convert operations: errors = %s"` | **CONFIRMED** |
| M-06 | Info | §5.3: `status = "error"` | `MeterService.countIntegrationError(...)` → status `"error"` | **CONFIRMED** |
| M-07 | Info | §5.3: метрика `history_ops_general` | `MeterService` → `history_ops_general` | **CONFIRMED** |
| M-08 | Info | §5.3: `logRequest`/`logResponse` с записью персентили и метрик | `adapter/RequestService.java` → `logRequest`, `logResponse`, `recordPercentile`, `addIntegrationMetric` | **CONFIRMED** |
| M-09 | Info | §5.3: логирование обмена — `IntegrationLogger`, `callType = OUT/IN`, `"Integration log entry"` | `logger/IntegrationLogService.java` → `getLogger("IntegrationLogger")`; `callType(...)`; INFO `"Integration log entry"` | **CONFIRMED** |
| M-10 | Info | §5.3: усечение тела лога до `bodyMaxBytes` → `"Oops.. content is too long"` | `IntegrationLogService` → `CONTENT_TOO_LONG = "Oops.. content is too long"` | **CONFIRMED** |
| M-11 | — | §5.3: полнота тестового контура для нового сценария | Тесты под `yield` в `repositories/` отсутствуют (TO BE) | **NOT FOUND (expected, TO BE)** |

### 8. OG/BPH-риски (D-26) и ограничения D-07/D-12

| # | Severity | Claim (секция SPEC) | Evidence | Статус |
|---|----------|---------------------|----------|--------|
| B-01 | Info | D-07: контракт ОГ (поле 42, `PriceData`) — **TO BE**, реализуется командой ОГ после `history-ops` | `order-gateway.proto` — `yield`/`PriceData` отсутствуют | **NOT FOUND (expected, TO BE)** — риск принят по D-07, вердикт не снижает |
| B-02 | Info | D-12: имена классов/внутренних DTO в спеке отсутствуют намеренно | `SPEC` §4.x — алгоритмическое описание; классы в спеку не выносятся | **CONFIRMED (как ограничение)** |
| B-03 | Info | D-26/CN-15/ASM-03/EC-13,EC-14/AC-17: расхождение формата `yield` между OG- и BPH-спеками — принятый риск | `Feature-writing/bph-linked-events-yield/` не читался и не редактировался (по D-26) | **CONFIRMED (риск документирован)** |
| B-04 | Info | D-27/CN-16/EC-12: fallback на BPH не гейтится отдельным тоглом; при выключенном BPH-пути поле `null` | `CounterFeatureToggleName.java` — тогла fallback нет; `TradeMerger` — BPH-ветка без тогл-гейта | **CONFIRMED** |

## Ожидаемые TO BE-разрывы (не блокеры)

Реализуются после согласования контракта ОГ (D-07); вердикт **не** понижают:

- **C-03** — `optional PriceData yield = 42;` в `TradeOrder` (`order-gateway.proto`);
- **C-06** — `optional PriceData yield = 99;` + import в `historyOperationDetails.proto`;
- **A-04** — прокидка `yield` в `HistoryOperationLead` при сборке OG-операции (`TradeMerger`);
- **A-05** — `setYield` в `DetailsResponseMapper`;
- **M-11** — тесты сценария доходности;
- **B-01** — сами TO BE-контракт-поля ОГ.

## Проверить вручную

- **K-06** — промышленные значения конфигов/тоглов: в `repositories/` только `application-test.yml` → **UNVERIFIABLE** (оговорка D-17).
- **A-06** — семантика неполного `PriceData` (частично заполненный объект): появится вместе с реализацией → **UNVERIFIABLE (TO BE)**.

## Пропущено / ограничения аудита

- Синхронизация с BPH-спекой **не выполнялась** (D-26); файл `Feature-writing/bph-linked-events-yield/*` **не читался и не редактировался**. Расхождение типов `yield` — принятый риск (CN-15/ASM-03/EC-13,EC-14/AC-17), OG-релиз не блокируется.
- Промышленные значения конфигов и тоглов недоступны в `repositories/` (только `application-test.yml`) → **K-06 UNVERIFIABLE** (оговорка D-17).
- Поведенческие аспекты `yield` (частично заполненный `PriceData`, отсутствие значения) не могут быть подтверждены до появления реализации → **A-06 UNVERIFIABLE (TO BE)**.
- `db-export/` и `analytics/` использовались как справочные; источник истины по DDL — миграции и entity в `repositories/` (пропусков не выявлено).
- Наличие имён классов (`OrderGrpcGateway`, `TradeMerger` и т. п.) в колонках «evidence» — намеренные code-якоря по D-12, не нарушение аналитического нарратива; в текстовых разделах `SPEC` классы не выносятся.

## Вердикт

| Показатель | Значение |
|------------|----------|
| Critical MISMATCH | **0** |
| Major MISMATCH | **0** |
| Minor MISMATCH | **0** |
| CONFIRMED | 32 |
| NOT FOUND (expected, TO BE) | 5 (C-03, C-06, A-04, A-05, M-11) + B-01 |
| UNVERIFIABLE | 2 (K-06 — prod-конфиги; A-06 — семантика неполного `PriceData`) |

**Вердикт: PASS WITH GAPS.** Critical и Major MISMATCH **отсутствуют**. Все
находки итерации 2 (F-01…F-05 / I-05, I-07, T-06, C-10) закрыты правкой `SPEC`
(батч D-30…D-34) и подтверждены сверкой с кодом. Остаются только ожидаемые
**NOT FOUND для TO BE** (контракт ОГ и прокидка `yield` — D-07; тесты) и
**UNVERIFIABLE** (prod-конфиги D-17; семантика неполного `PriceData`). По правилу
скилла TO BE NOT FOUND и UNVERIFIABLE дают `PASS WITH GAPS`, а не `FAIL`.

---

## Журнал решений

Append-only. Записи ниже — история правок `SPEC`; `verdict` и счётчики в шапке
отчёта **пересчитаны** этим прогоном (`alignment_iteration: 3`).

### Батч 4 (2026-09-13) — применено в `SPEC` по `DECISIONS` D-30…D-34

| Decision | Relates (finding) | Действие по `SPEC` | Разделы `SPEC` |
|----------|-------------------|--------------------|----------------|
| **D-30** | F-01 (Major MISMATCH), I-05 | `ex_system`/`exSystem` приведены к коду = `"OG"` (было `ORDER_GATEWAY`); статус «Подтверждено кодом» сохранён | §1.3, §5.1 (аудит-таблица), §5.3 |
| **D-31** | F-02 (Major MISMATCH), T-06 | `bphGetLinkedEvents.active` убран из таблицы Auth-тоглов §5.5; описан в §5.4 как ключ динамического ConfigMap (`app-config-dynamic.instrument-filter-requests-dynamic`), не Auth-тогл; в §5.5 добавлена отсылка и дисклеймер | §5.4, §5.5 |
| **D-32** | F-05 (Minor MISMATCH), I-07 | `serviceName` приведён к коду = `history_ops` (нижний регистр) | §5.5 |
| **D-33** | F-03 (Minor MISMATCH / PARTIAL), C-10 | В §4.1.1.1 добавлена явная ссылка: форма `PriceData {value, currency}` совпадает с существующим `PriceData` в `bph.yml` (1226–1240); при общем пакете — переиспользовать тип; имя пакета — за владельцем контракта | §4.1.1.1, §4.1.1.3 |
| **D-34** | F-04 (Minor MISMATCH, doc) | Ссылки `§4.2.3`/`§4.2.4` заменены на текстовые названия «Модель данных» / «Маппинг данных»; нумерация заголовков не менялась | §2 (CN-17), §4.2, §5.1/§5.4/§6/§7 |

### Итерация 3 (2026-09-13) — пересчёт вердикта

Проведена сверка каждой closure-находки итерации 2 с фактическим текстом `SPEC`
и с кодом. Новых решений не создавалось: `DECISIONS` не менялся (0 строк
`needs-answer`, 0 `pending-apply`; все строки батча 4 — `applied`). Открытых
`[GAP-...]` и `[CH-...]` в `SPEC` нет.

| Finding | Итог сверки | Статус после пересчёта |
|---------|-------------|------------------------|
| F-01 / I-05 (`ex_system`) | `SPEC` = `OG`; код `GetTradeOrdersGateway.java:46` / `GetActiveOrdersGateway.java:46` = `"OG"` | **CLOSED** |
| F-02 / T-06 (`bphGetLinkedEvents`) | `SPEC` §5.4 = ConfigMap-ключ, §5.5 не содержит; код `RpcNamesForRequestCondition.java:11` = ConfigMap-ключ, `CounterFeatureToggleName` без него | **CLOSED** |
| F-03 / C-10 (`PriceData`) | `SPEC` ссылается на `bph.yml:1226-1240`; в коде `PriceData` существует | **CLOSED (контекст)** |
| F-04 (`§4.2.3`/`§4.2.4`) | в `SPEC` 0 совпадений; используются текстовые названия | **CLOSED (doc)** |
| F-05 / I-07 (`serviceName`) | `SPEC` = `history_ops`; код `SessionServiceGateway.SERVICE_NAME = "history_ops"` | **CLOSED** |

Итог: Critical/Major MISMATCH = **0** → вердикт **PASS WITH GAPS**. Остаются
ожидаемые NOT FOUND (TO BE) и UNVERIFIABLE — вердикт не понижают (D-07, D-17).
Лимит alignment (3 из 3) исчерпан; дальнейший цикл `check-feature-code` не
требуется.


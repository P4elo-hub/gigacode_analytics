---
slug: composite-active-order-commission
spec: Feature-writing/composite-active-order-commission/composite-active-order-commission.md
context_doc: Feature-context/composite-active-order-commission.md
alignment_iteration: 1
verdict: PASS WITH GAPS
counts:
  confirmed: 42
  mismatch: 1
  partial: 0
  not_found: 4
  unverifiable: 1
date: 2026-02-17
---

# Отчёт о соответствии коду: composite-active-order-commission

## Сводка

Проведён аудит SPEC `composite-active-order-commission.md` против фактического кода в
`repositories/`. Итерация alignment: **1** (отчёт создаётся впервые).

Спецификация в подавляющей части **согласована с кодом**: номера полей proto,
схема `history.yml`, ключи конфигурации, формат ключей Ignite, поведение
`CurrencyConverter` / `DecimalFormatter` / `OgTradeOperationCreator` — подтверждены
цитатами и путями. Изменений схемы БД фича не вносит — миграций для аудита нет.

Все заявленные «новые» сущности (BPH-параметр `precalc_commission`, фича-тогл
`enable_feed_precalc_commission`, шильдик комиссии в `ChipsContent`) в коде
**отсутствуют** — это ожидаемое состояние TO BE до реализации (NOT FOUND, Major
для TO BE).

Выявлено **1 расхождение (Minor)**: имя config-ключа пула потоков ленты в SPEC
не совпадает с фактическим в `application.yml`.

**Вердикт: PASS WITH GAPS** — Critical/Major MISMATCH нет; NOT FOUND относятся к
ещё не реализованному TO BE.

## Приоритетные находки

| # | Severity | Раздел SPEC | Утверждение | Код | Статус |
|---|----------|-------------|-------------|-----|--------|
| F-01 | Major | §4.1.1.2, CN-02, шаг 3.4 | Новый параметр BPH `tradeOrder.lead.precalc_commission` (`{value, currency}`) | `grep 'precalc_commission\|precalc' repositories/` → 0 совпадений | NOT FOUND (TO BE) |
| F-02 | Major | §5.5, CN-02, шаг 4 | Фича-тогл `enable_feed_precalc_commission`, default `false` | `grep 'enable_feed_precalc_commission' repositories/ analytics/` → 0 совпадений | NOT FOUND (TO BE) |
| F-03 | Major | §4.1.1.5, CN-07, шаг 10 | Элемент шильдика комиссии в `chipsContent` (`params[]`) | `ChipsContent.java` — чипа комиссии нет; `TransactionChipsContentCustomizer` кладёт только существующие элементы | NOT FOUND (TO BE) |
| F-04 | Minor | §5.2 (стр. 1651), §5.4 (стр. 1740) | Config-ключ `history.ops.feed.executor.threads: 5` | `application.yml:66-68` → фактически `history.ops.feed.transactions.executor.threads: 5` | MISMATCH (Minor) |
| F-05 | Major | §4.1.1.2, §5.5 | Готовность BPH отдавать `precalc_commission`; заполненность `TradeOrder.commission_value` для активных заявок OG | Кода-источника в воркспейсе нет; заполненность данными — вне репозиториев | UNVERIFIABLE |

## Находки по категориям

### Контракты

| # | Раздел | Утверждение (цитата) | Код (path:lines) | Доказательство | Статус |
|---|--------|----------------------|------------------|----------------|--------|
| C-01 | §1.2/§4.1.1.3, CN-01 | «поле `commission_value` (поле 65)» в `GetDetailsResponse` | `repositories/ИО/history-ops-grpc-client/history-ops-grpc-client-api/src/main/proto/historyOperationDetails.proto:146` | `optional double commission_value = 65;` | CONFIRMED |
| C-02 | CN-13 | `commission_value_stop_loss = 66`, `commission_value_take_profit = 67` | `.../historyOperationDetails.proto:147-148` | `optional double commission_value_stop_loss = 66;` / `optional double commission_value_take_profit = 67;` | CONFIRMED |
| C-03 | CN-04 | `total_deals_commission` (proto поле 72) | `.../historyOperationDetails.proto:153` | `optional double total_deals_commission = 72;` | CONFIRMED |
| C-04 | CN-03/CN-16 | `TradeOrder.commission_value = 11`, rpc `GetTradeOrders` | `repositories/ИО/history-ops/src/main/proto/order-gateway.proto:14,71,82` | `rpc GetTradeOrders (...)`; `message TradeOrder`; `optional google.type.Decimal commission_value = 11;` | CONFIRMED (уточнение: тип `google.type.Decimal`, не объект `{value}` — см. замечание ниже) |
| C-05 | CN-16 | `rpc GetActiveOrders` (17); `message ActiveOrder` (155) без полей комиссии | `.../order-gateway.proto:17,155-172` | `rpc GetActiveOrders (...)`; `message ActiveOrder { ... total_sum = 11; stop_loss_px = 12; take_profit_px = 13; }` — полей комиссии нет | CONFIRMED |
| C-06 | CN-07 | «Срок `expire_date_details`, ценовые элементы `stop_px`, `take_profit_px`, `value_by_instrument_item`» сохраняются | `.../historyOperationDetails.proto:85-86,154-155,90`; `history.yml` `ReportOrderOperationDetails` | `expire_date = 85`, `expire_date_details = 86`, `stop_px = 73`, `take_profit_px = 74`, `value_by_instrument_item = 24` | CONFIRMED |
| C-07 | §4.1.1.4 | REST `ReportOrderOperationDetails`; `required: [orderType, deals, agreementNumber]` | `repositories/ИО/history-ops/src/main/swagger/history/history.yml:381-383` | `required:` → `- orderType` / `- deals` / `- agreementNumber` | CONFIRMED |
| C-08 | §4.1.1.4 | Поля `commission_value`, `commission_value_stop_loss`, `commission_value_take_profit`, `total_deals_value`, `order_type`, `total_deals_commission`, `stop_px`, `take_profit_px`, `total_brokerage_comission`, `total_exchange_comission` | `.../history.yml:387-444` | перечисленные поля присутствуют с `type: number` / `type: string` | CONFIRMED |
| C-09 | §4.1.1.4 | `HistoryOperationLead.required = [id, itemtype, type, general_status, time_happened]`, без комиссии | `.../history.yml:459-465` | совпадает побайтово; поля `commission_value` в lead нет | CONFIRMED |
| C-10 | §4.1.1.4 | `expire_date_details: $ref ExpireDateDetails` | `.../history.yml:436-437` | присутствует | CONFIRMED |
| C-11 | §4.2.3.1 | `DetailsResponseMapper.convertDouble("commission_value", source)`; `convertString("currency", source)` | `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/model/DetailsResponseMapper.java:72,77` | `convertString("currency", source)` / `convertDouble("commission_value", source)` | CONFIRMED |
| C-12 | CN-14 | `enrichWithOptionalValue` выставляет поле только при `value != null`; `DetailsResponseMapper.convertDouble` → `Optional.of(key).map(source::get).map(JsonNode::asDouble).orElse(null)` | `.../DetailsResponseMapper.java:182,404-408` | `setCommissionValue(enrichWithOptionalValue(...))`; helper совпадает с цитатой | CONFIRMED |
| C-13 | CN-14, §4.2.3.6 | proto3 `optional double` не передаёт признак наличия; `0.0` и отсутствие неразличимы | `.../historyOperationDetails.proto:146` (`optional double commission_value = 65`) | контракт не несёт отдельного presence-флага для получателя композита | CONFIRMED |
| C-14 | §4.1.1.2 | Новый ключ `tradeOrder.lead.precalc_commission {value, currency}` | grep по `repositories/` → 0 совпадений | — | NOT FOUND (TO BE) |

**Замечание к C-04 (Info).** SPEC §4.1.1.1 представляет `commission_value` OG как
объект `{value}` (форма таблицы аналитики). В proto фактический тип —
`google.type.Decimal` (`optional google.type.Decimal commission_value = 11`),
у которого значение извлекается через `Decimal.getValue()` (см. `GrpcDecimalConverter`,
`OrderGrpcConverter`). Отображение в SPEC не искажает поведение, но форма записи
не совпадает с proto. Severity: Info.

### БД и миграции

| # | Раздел | Утверждение (цитата) | Код (path:lines) | Доказательство | Статус |
|---|--------|----------------------|------------------|----------------|--------|
| D-01 | §4.2.3, §5.2.6 | «Схема БД **не меняется**: новых/изменённых сущностей, FK и индексов нет»; шильдик не читает/не пишет БД | `repositories/ИО/history-ops/src/main/swagger/history/history.yml` (изменений нет); миграции ChangeLog `user_data-history_ops_screen_api-changelog.xml` — новых changeset под фичу нет | в `repositories/` не найдено миграций/entity, связанных с шильдиком комиссии; отсутствуют новые changeset | CONFIRMED |
| D-02 | §4.2.3 | Кэш `spring.cache` Caffeine, `expireAfterWrite=1m`, схема `history_ops_screen_api` | `repositories/ИО/history-ops-screen-api/src/main/resources/application.yml:7-11,16-19,22-25` | `cache.type: caffeine`, `spec: expireAfterWrite=1m`; `hikari.schema: history_ops_screen_api`; `default_schema: history_ops_screen_api` | CONFIRMED |
| D-03 | §5.2.7 | Ключ Ignite `ucpId:paginationResponseId` / `ucpId:clientRequestId` | `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/service/OperationsIgniteProxyService.java:40,154,243`; `.../model/HistoryOpsDetailsRequestContext.java:26-30` | `IGNITE_OPERATIONS_CACHE_TEMPLATE_KEY = "%s:%s"`; ключ `ucpId:paginationResponseId` (154), `ucpId:clientRequestId` (243); `resolveKey()` = `ucpId + ":" + paginationResponseId` | CONFIRMED |

### Интеграции

| # | Раздел | Утверждение (цитата) | Код (path:lines) | Доказательство | Статус |
|---|--------|----------------------|------------------|----------------|--------|
| I-01 | §4.2.3.1 | `OgTradeOperationCreator`: `.commissionValue(orderGatewayOrders.commissionValue())` | `repositories/ИО/history-ops/src/main/java/.../service/conversion/operation/creator/OgTradeOperationCreator.java:110,200` | `BigDecimal commissionValue = orderGatewayOrders.commissionValue();`; builder `.commissionValue(commissionValue)` | CONFIRMED |
| I-02 | §4.2.3.5, BR-03 | stop_loss/take_profit заполняются только при `isTakeProfitAndStopLimit`; `totalDealsCommission` считается независимо | `.../OgTradeOperationCreator.java:112-117` | `commissionValueStopLoss/TakeProfit` — только для `isTakeProfitAndStopLimit`, иначе `null`; `computeCommissionFromOg` возвращает `commissionValue()` для FUTURES | CONFIRMED |
| I-03 | §4.2.3.7 | `ExpireDate` только для активных статусов | `.../OgTradeOperationCreator.java` (`isActiveStatus`) | заполнение `ExpireDate` под условием активного статуса | CONFIRMED |
| I-04 | §4.2.3.1 | `OrderGrpcConverter.parseNullableDecimal(order.getCommissionValue())` | `repositories/ИО/history-ops/src/main/java/.../adapter/order_gateway/converter/OrderGrpcConverter.java:57,59-63,116-118` | `parseNullableDecimal(order.getCommissionValue())`; stop_loss/take_profit (59-63); wrapper ctor (116-118) | CONFIRMED |
| I-05 | CN-14 | `GrpcDecimalConverter.parseNullableDecimal` → `null` при пустом `Decimal` | `repositories/ИО/history-ops/src/main/java/.../adapter/grpc/GrpcDecimalConverter.java` | `if (source.getValue().isEmpty()) return null;` | CONFIRMED |
| I-06 | §4.1.1.3 | HO→composite gRPC `GetDetailsResponse` (ucpId, operationId, paginationResponseId) | `repositories/ИО/history-ops-screen-api/src/main/java/.../services/HistoryOpsServiceProxy.java`; `HistoryOpsDetailsRequestContext.resolveKey` | `GetDetailsRequest(ucpId, operationId, paginationResponseId)`; метрики `operation_details_requests_*`; `onCacheMissException` инкрементит на NOT_FOUND | CONFIRMED |
| I-07 | §1.2.1 / §4.1.1.2 | HO↔BPH `GET_LINKED_EVENTS` | в `repositories/` релевантный клиент присутствует, ключ линковки — как в §4.2.3.2 | интеграционная ветка BPH существует | CONFIRMED |
| I-08 | §4.1.1.5, CN-07 | `TransactionChipsContentCustomizer` → `ChipsContent`; активные типы `TRANSACTION_BUY`/`TRANSACTION_SELL` | `repositories/ИО/history-ops-screen-api/src/main/java/.../composite/screen/feed/section/customizers/TransactionChipsContentCustomizer.java` | `ACTIVE_STATUSES = Set.of(CANCELLING, IN_PROGRESS)`; `getSupportedTypes = Set.of(TRANSACTION_BUY, TRANSACTION_SELL)`; `chipsContent` кладётся только для активных | CONFIRMED |
| I-09 | §4.1.1.5 | `AbstractSectionCreator.resolveType` → `history.feed.operationActive` для активных | `repositories/ИО/history-ops-screen-api/src/main/java/.../composite/sections/feed/section/creators/AbstractSectionCreator.java:64-70` | `if (ACTIVE_STATUSES.contains(generalStatus)) return "history.feed.operationActive"; else return "history.feed.operation";` | CONFIRMED |
| I-10 | §4.1.1.5, §4.2.3.6 | Шильдик комиссии в `ChipsContent.enrich` (JSONArray `params`) | `repositories/ИО/history-ops-screen-api/src/main/java/.../composite/sections/feed/ChipsContent.java` | методы `enrich`/`enrichWithLogo`/`enrichWithPriceMessage`/`enrichWithSecondPrice`; `resolveValueByOrderType`/`resolvePostfix` — чипа комиссии нет | NOT FOUND (TO BE) |
| I-11 | §4.1.1.2 | Готовность BPH отдавать `precalc_commission`; заполненность `TradeOrder.commission_value` активных заявок OG (кроме FUTURES — `computeCommissionFromOg`) | вне `repositories/` | заполненность реальными данными источника не проверяется по коду | UNVERIFIABLE |

### Конфигурация

| # | Раздел | Утверждение (цитата) | Код (path:lines) | Доказательство | Статус |
|---|--------|----------------------|------------------|----------------|--------|
| K-01 | §5.2, §5.4 | `history.ops.details.transaction.executor.threads: 5` | `application.yml:98-99` | `details.transaction.executor.threads: 5` | CONFIRMED |
| K-02 | §5.2, §5.4 | `ignite.threads.pool`: `coreSize: 3`, `maxSize: 5`, `queueCapacity: 100` | `application.yml:139-143` | совпадает | CONFIRMED |
| K-03 | §5.2.6 | `spring.datasource.hikari.maximum-pool-size: 10`; `connection-timeout: 30000` | `application.yml:13-15` | `connection-timeout: 30000`; `maximum-pool-size: 10` | CONFIRMED |
| K-04 | §5.2.7 | `ignite.chevrons.logo.cache`: `cacheName: CHEVRONS_LOGO`, `backupsAmount: 0`, `rowTimeToLiveMs: 600000` | `application.yml:144-148` | совпадает | CONFIRMED |
| K-05 | §5.4 | `session.service.channel`: port 9097, deadline 1s, retries 3, shouldRetryCodes 14 | `application.yml:39-49` | `port: 9097`, `deadline: 1s`, `retries: 3`, `shouldRetryCodes: 14` | CONFIRMED |
| K-06 | §5.4 | `history.ops.details.service.channel`: port 9098, deadline 1s, retries 3 | `application.yml:126-137` | `port: 9098`, `deadline: 1s`, `retries: 3` | CONFIRMED |
| K-07 | §5.2.3 | `history.ops.details.transaction.details.*` types (stop/futures/bond/stock), статусы | `application.yml:100-125` | `futures.types: SETTLEMENT_FUTURES,DELIVERY_FUTURES`; `stop.types`, `bond.types`, `stock.types`, `statuses.*` присутствуют | CONFIRMED |
| K-08 | §5.2 (стр. 1651), §5.4 (стр. 1740) | `history.ops.feed.executor.threads: 5` | `application.yml:66-68` | фактически `history.ops.feed.transactions.executor.threads: 5` — имя ключа в SPEC неполное | MISMATCH (Minor) |
| K-09 | §5.4 | Prefix свойств `history.ops.details.transaction.details` | `repositories/ИО/history-ops-screen-api/src/main/java/.../configurations/properties/HistoryOperationDetailsScreenProperties.java` | prefix совпадает; `OrderProperties.types`, `OperationStatusesProperties`, `OperationScreenProperties` | CONFIRMED |
| K-10 | §5.4 | Rate Limiting / Throttling / Circuit Breaker не сконфигурированы | `application.yml` (отсутствуют) | в `application.yml` нет соответствующих ключей | CONFIRMED |

### Feature toggles

| # | Раздел | Утверждение (цитата) | Код (path:lines) | Доказательство | Статус |
|---|--------|----------------------|------------------|----------------|--------|
| T-01 | §5.5, CN-02, шаг 4 | Тогл `enable_feed_precalc_commission`, default `false` | grep `repositories/` и `analytics/` → 0 совпадений | — | NOT FOUND (TO BE) |
| T-02 | §5.5 | Тоглы читаются через AUTH `getSession` (`MicroserviceFeatureToggleProto`, `toggleName`/`isActive`) | `repositories/ИО/history-ops-screen-api/src/main/java/.../services/SessionService.java` | `getFeatureToggles` try/catch → `Collections.emptyMap()`; читает `MicroserviceFeatureToggleProto` (`toggleName.data` / `isActive.data`); `serviceName "history_ops_screen_api"` | CONFIRMED |
| T-03 | §5.5 | Ретраи/дедлайн канала AUTH | `repositories/ИО/history-ops-screen-api/src/main/java/.../services/SessionServiceGrpcProxy.java` | `@Retryable(maxAttemptsExpression = "${session.service.channel.retrySettings.retries:1}")`, `exceptionExpression = "@sessionServiceRetryPolicy.shouldRetry(#root)"`, deadline из `ChannelProperties` | CONFIRMED |
| T-04 | §5.5 | Отсутствие ключа `feature_toggle_grpc_enabled` | `application.yml` (отсутствует) | ключа нет — SPEC корректно помечает его как unconfirmed/legacy | CONFIRMED |

### Поведение и алгоритмы

| # | Раздел | Утверждение (цитата) | Код (path:lines) | Доказательство | Статус |
|---|--------|----------------------|------------------|----------------|--------|
| B-01 | §4.1.1.5, §3.2 | Форматирование `DecimalFormatter`: `setScale(2, HALF_UP).stripTrailingZeros()`, `#,##0.##`, ru_RU | `repositories/ИО/history-ops-screen-api/src/main/java/.../services/DecimalFormatter.java` | `setScale(2, HALF_UP).stripTrailingZeros()`; `DecimalFormat("#,##0.##", ru_RU)` (разделитель `,`, группировка ` `); catch `NumberFormatException` → `"—"` | CONFIRMED |
| B-02 | §4.2.3.5 | `CurrencyConverter.getCurrencyFrom(GetDetailsResponse)`: `if (!hasCurrency()) return "";` → символ или исходный код | `repositories/ИО/history-ops-screen-api/src/main/java/.../services/CurrencyConverter.java:15-27` | `boolean hasCurrency = operation.hasCurrency(); if (!hasCurrency) return "";` → `Optional...filter(isNotBlank).flatMap(getSymbol).orElseGet(operation::getCurrency)` | CONFIRMED |
| B-03 | §4.2.3.5 | `CurrencyConverter.getSymbol` catch `IllegalArgumentException` → `log.warn("Didn't manage to get currency symbol for {}")` → `Optional.empty()` | `.../CurrencyConverter.java:79-89` | совпадает побайтово | CONFIRMED |
| B-04 | §4.1.1.5 | `AbstractSectionCreator.ACTIVE_STATUSES = Set.of(CANCELLING, IN_PROGRESS)` | `.../AbstractSectionCreator.java:25-26` | совпадает | CONFIRMED |
| B-05 | §4.1.1.5 | `ChipsContent.resolveValueByOrderType` для `stop_limit`/`stop_loss_by_market`/`take_profit`/`take_profit_by_market`/`take_profit_and_stop_limit`/`limit`/`negotiated` | `.../ChipsContent.java` (`resolveValueByOrderType`) | перечисленные ветки присутствуют | CONFIRMED |
| B-06 | §4.1.1.5 | `resolvePostfix`: futures → `"пт"`, иначе `currencyConverter.getCurrencyFrom(operation)` | `.../ChipsContent.java` (`resolvePostfix`) | совпадает | CONFIRMED |
| B-07 | §4.1.1.5 | `enrichWithLogo` — иконка `ds_ic_24_clock_fill` | `.../ChipsContent.java` (`enrichWithLogo`) | совпадает | CONFIRMED |
| B-08 | §4.2.3.6 | Падение символа валюты → показ исходного кода (graceful degradation) | `.../CurrencyConverter.java` (catch → `Optional.empty()` → `orElseGet(... : getCurrency)`) | подтверждает деградацию до исходного кода | CONFIRMED |

### Тесты и фикстуры

| # | Раздел | Утверждение | Код | Статус |
|---|--------|-------------|-----|--------|
| TS-01 | §4.1.1.5, §4.2.3.6 | Тесты `DecimalFormatter`/`CurrencyConverter`/`ChipsContent` для значений комиссии | в `repositories/` тесты на шильдик комиссии отсутствуют (фича TO BE) | NOT FOUND (TO BE) |

## Замечания (Info)

| # | Раздел | Утверждение | Код | Статус |
|---|--------|-------------|-----|--------|
| N-01 | §4.1.1.1 | OG `commission_value` показан как объект `{value}` | `order-gateway.proto:82` — `optional google.type.Decimal commission_value = 11` (значение через `getValue()`) | Info (форма записи не совпадает с proto) |
| N-02 | CN-04, BR-03 | Семантика `commission_value` (предрасчёт) vs `total_deals_commission` (факт по сделкам) | `OgTradeOperationCreator` — два независимых вычисления | CONFIRMED (различие семантики подтверждено кодом) |

## Рекомендуемые действия

1. **F-03 / I-10 (Major, TO BE)** — реализация шильдика в `ChipsContent`/`ChipsContentCustomizer`; при появлении кода — повторный аудит.
2. **F-01 / C-14 (Major, TO BE)** — договорённость с BPH по `tradeOrder.lead.precalc_commission {value, currency}` и нормализация в HO `commission_value` (proto 65); новых полей proto не вводить (CN-15).
3. **F-02 / T-01 (Major, TO BE)** — ввод тогла `enable_feed_precalc_commission` (default `false`) через AUTH `getSession`.
4. **F-04 / K-08 (Minor)** — уточнить в SPEC §5.2/§5.4 имя config-ключа: фактически `history.ops.feed.transactions.executor.threads` (значение `5` верно). Правит `alignment-resolver` или `spec-reviewer`.
5. **N-01 (Info, опционально)** — в §4.1.1.1 привести тип OG-поля к proto (`google.type.Decimal`).
6. **F-05 / I-11 (UNVERIFIABLE)** — подтвердить заполненность `TradeOrder.commission_value` для активных заявок OG тестовыми данными источника (вне репозиториев).

## Пропущено

- Полнотекстовый аудит субдеревьев репозиториев, не относящихся к фиче (деплой-манифесты,
  CI, прочие модули) — вне scope.
- Проверка реальной заполненности данными внешних источников (OG/BPH/AUTH) — невозможно по коду.
- Аудит БД-экспорта `db-export/` на предмет расхождений схемы — изменения схемы фичей не
  заявляются, миграций нет; словарь не требовался.

---
report_type: code-alignment
slug: bph-linked-events-yield
source_document: Feature-writing/bph-linked-events-yield/bph-linked-events-yield.md
generated_at: 2026-09-20
alignment_iteration: 1
scope: repositories/ only
language: ru
verdict: PASS WITH GAPS
---

# Отчёт о соответствии коду: bph-linked-events-yield

**Документ:** `Feature-writing/bph-linked-events-yield/bph-linked-events-yield.md`
**Отчёт:** `Feature-writing/bph-linked-events-yield/bph-linked-events-yield-code-alignment.md`
**Область проверки:** только код в `repositories/`

## Сводка
- CONFIRMED: 23 · MISMATCH: 1 · PARTIAL: 0 · NOT FOUND: 7 · UNVERIFIABLE: 0
- **Вердикт:** PASS WITH GAPS

## Приоритетные находки

Запрошенные пользователем фокус-области проверены в первую очередь:

1. **Поле 99 в gRPC `historyOperationDetails.proto` свободно — ДА.** Последнее занятое поле
   `optional bool auto_follow = 98;`; поля 99 в `GetDetailsResponse` нет. CONFIRMED.
2. **Типа `PriceData` в proto нет — верно, его нужно вводить.** Grep по `*.proto` (все
   репозитории `ИО`): `PriceData`/`yield` не найдены; `message PriceData` в
   `historyOperationDetails.proto` отсутствует. NOT FOUND (ожидаемо TO BE).
3. **Конфликтов по общим контрактам с OG-фичей нет.** Обе фичи TO BE: поле 99 свободно,
   `PriceData` нигде не определён, `yield` отсутствует во всех контрактах (proto, `history.yml`,
   BPH-схема). Единственный «прецедент» `commission_value = 65` подтверждён.
4. **Единственное расхождение с кодом (Minor):** заголовок `systemName` во входящем
   контракте BPH. SPEC §4.1.1.1 пишет `systemName = si2-ops`, код (`BphClient.java`)
   использует `systemName = history_ops`. Имена заголовков (`rqUID`, `systemName`) верны,
   ошибочно значение.

## Находки по категориям

### Контракты
| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|----|------------------|-------------|-----------------------|--------|-------------|
| C-01 | §4.1.1.2, CN-02 | Последнее занятое поле `auto_follow = 98`; поле 99 свободно | `repositories/ИО/history-ops-grpc-client/history-ops-grpc-client-api/src/main/proto/historyOperationDetails.proto` — `optional bool auto_follow = 98;` (последнее поле `GetDetailsResponse`), поле 99 отсутствует | CONFIRMED | Info |
| C-02 | §4.1.1.2 | `commission_value = 65` (прецедент поля из источника) | там же — `optional double commission_value = 65;` | CONFIRMED | Info |
| C-03 | §4.1.1.2, CN-06 | `PriceData` в proto отсутствует, вводится инлайн `message PriceData {value, currency}`; `optional PriceData yield = 99` | proto не содержит `message PriceData` и поля `yield` (grep `PriceData|yield` по `*.proto` — 0 совпадений) | NOT FOUND (TO BE) | Major |
| C-04 | §4.1.1.2 | Плоская структура `GetDetailsResponse`: `HistoryOperationLead` = поля 17–33 | proto: `id = 17` … `channel = 33` (блок `// HistoryOperationLead`) | CONFIRMED | Info |
| C-05 | §4.1.1.2 (примечание) | `getOperationsFeed` возвращает `repeated GetDetailsResponse operations_details` → `yield` присутствует и в ленте, и в деталке | proto: `message GetOperationsFeedResponse { repeated GetDetailsResponse operations_details = 1; ... }` | CONFIRMED | Info |
| C-06a | §4.1.1.3 | `HistoryOperationLead` поля `id`…`channel` (17 полей); поля `yield` нет | `repositories/ИО/history-ops/src/main/swagger/history/history.yml:456` — `HistoryOperationLead:` свойства `id`…`channel`; `yield` отсутствует | CONFIRMED | Info |
| C-06b | §4.1.1.3, CN-06 | Схемы `PriceData` в `components.schemas` нет, поле `yield` нет | grep `PriceData|yield|profitab` по `history.yml` — 0 совпадений | NOT FOUND (TO BE) | Major |
| C-07a | §4.1.1.1 | BPH `OperationData` содержит `price`/`totalPrice` типа `PriceData {value, currency}`; поля `yield` нет | `repositories/ИО/history-ops/sowa/sigma_alpha/to_bph_rq_http/history_get_linked_events/schemes/json/POST_api_v1_incoming-gateway_operations_linked-events_response_200.json` — `definitions.PriceData` (`value` string, `currency` string), `OperationData.price`/`totalPrice` → `$ref: PriceData`; `yield` отсутствует | CONFIRMED | Info |
| C-07b | §4.1.1.1, CN-01 | Новое поле `OperationData.yield` (lead, `tradeOrder`) — TO BE на стороне BPH | в `OperationData` (схема) поля `yield` нет (`additionalProperties: false`) | NOT FOUND (TO BE, внешний контракт) | Major |
| C-08 | §4.1.1.1 | `RequestLinkedData` required `[agreements, dateForFilter, pageSize]`; остальные опциональны | `..._request.json` — `required: [agreements, dateForFilter, pageSize]` | CONFIRMED | Info |
| C-09 | §4.1.1.1 | `dateForFilter` enum `EVENT_DATE/FORMATION_DATE/ADDITIONAL_DATE` | `..._request.json` — `FilterDateEnum` enum | CONFIRMED | Info |
| C-10 | §4.1.1.1 | `details[]` = `DetailData {key, value}` | `..._response_200.json` — `definitions.DetailData` (`key`, `value`) | CONFIRMED | Info |
| C-11 | §4.1.1.1 | `tradeOrder`/`condTradeOrder` = `lead` (`OperationData`) + `details[]` | `..._response_200.json` — `LinkedEventsData.linkedEvents[]` с `condTradeOrder`/`tradeOrder` (`lead` + `details`) | CONFIRMED | Info |
| C-12 | §4.1.1.1 | Заголовок `systemName` = `si2-ops` | `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/adapter/bph/BphClient.java:21,31,43,54` — `HISTORY_OPS = "history_ops"`, `.header(SYSTEM_NAME, HISTORY_OPS)`. Имя заголовка `systemName` и `rqUID` верны, но значение — `history_ops`, не `si2-ops` | MISMATCH | Minor |
| C-13 | §4.1.1.1 | `status` (`SUBMITTED`/`COMPLETED`/`CANCELLED`) | код маппит `COMPLETED→EXECUTED`, `CANCELLED→CANCELED`, `EXECUTED`, `PARTIALLY_EXECUTED` (`BphLinkedEventsRawConverter.GENERAL_STATUS_MAP`, `BphLinkedUnconditionalTradeOrderConverterForTrades.STATUS_MAP`); `SUBMITTED` в коде нет; схема BPH — просто `string` (пример `DONE`) | Minor | Info |

### БД и миграции
| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|----|------------------|-------------|-----------------------|--------|-------------|
| DB-01 | CN-10, BR-06 | Доходность транзитна: колонки/чанджесета под `yield` нет; схема БД не меняется | grep `yield|доходност` по `*.xml|*.sql` (`src/main/resources/db/`, `liquibase/`) — 0 совпадений. Таблицы — справочники (`bph`, `operation`, `cancellation_bph`, `status`, `type`, `operation_type`, `general_status` …), хранилища деталей заявки нет | CONFIRMED | Info |
| DB-02 | CN-10 | Миграции под доходность не требуются (транзитное поле) | отсутствие любой `yield`-миграции; модель `HistoryOperationLead` — runtime DTO из swagger (не `@Entity`) | CONFIRMED | Info |

### Интеграции
| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|----|------------------|-------------|-----------------------|--------|-------------|
| I-01 | §4.1.1.1 | Endpoint `POST /api/v1/incoming-gateway/operations/linked-events` | `BphClient.java:16` — `LINKED_EVENTS_URL = "/api/v1/incoming-gateway/operations/linked-events"`; `getLinkedEvents()` → `.post().uri(LINKED_EVENTS_URL)` | CONFIRMED | Info |
| I-02 | CN-05, §4.1.1.1 | `BphLinkedOperationsGateway`: `eventType()="GET_LINKED_EVENTS"`, `exSystem()="BPH"`, `SUPPORTED_OPERATION_TYPES={TRANSACTION_BUY, TRANSACTION_SELL, COMISSION}`, `enabled()` = `isBphLinkedCommissionsEnabled() || isBphLinkedTradingOpsEnabled()` | `repositories/ИО/history-ops/.../adapter/bph/linked_events/BphLinkedOperationsGateway.java` — все три метода и `SUPPORTED_OPERATION_TYPES` совпадают | CONFIRMED | Info |
| I-03 | CN-13 | Слияние OG↔BPH по `exchange_order_id`; `OrderMerger` дедуплицирует по `exchangeOrderId` (OG) / `selfIdTs` (BPH) | `repositories/ИО/history-ops/.../service/conversion/operation/merger/OrderMerger.java` — `ogOrdersWithExchangeOrderId` (по `exchangeOrderId()`), `bphOrdersWithExchangeOrderId` (по `getSelfIdTs()`); приоритет OG (ветвление `isOgOrderPresent`) | CONFIRMED | Info |
| I-04 | §4.1.1.2 | gRPC-статусы `getOperationDetails`: `INVALID_ARGUMENT` («Incorrect request»), `NOT_FOUND` («Didn't manage to find operation from cache»), `INVALID_ARGUMENT` («Didn't manage to fill required fields» / «Didn't manage to create response»), `UNAVAILABLE` («Didn't manage to get data from cache») | `repositories/ИО/history-ops/.../service/HistoryOpsGrpcService.java:58–70` — все четыре `Status.*.withDescription(...)` совпадают | CONFIRMED | Info |

### Конфигурация
| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|----|------------------|-------------|-----------------------|--------|-------------|
| CF-01 | §4.1.1.1, §4.1.1.3 | Timeout BPH задаётся runtime-конфигом (`WebClientBphConfiguration`, `BphProperties.deadline`) | `repositories/ИО/history-ops/.../configuration/WebClientBphConfiguration.java` — `webClientUtil.webClient(builder, bphProperties.url(), bphProperties.deadline())`; `BphProperties(deadline, url, pageSizeForLinkedEvents, pageSizeForTrades)` | CONFIRMED | Info |
| CF-02 | §4.1.1.1 | `pageSizeForLinkedEvents` = 200 | `repositories/ИО/history-ops/src/test/resources/application-test.yml:133` — `pageSizeForLinkedEvents: 200` (продакшн-значение в Helm/ConfigMap вне репозитория) | CONFIRMED | Info |
| CF-03 | §4.1.1.1 (примечание) | «HO всегда шлёт `page=0`» | `BphLinkedOperationsGateway.createRequest()` устанавливает `pageSize`, но `page` не устанавливает (`request.setPage(...)` отсутствует) — аналитическое «page=0» не подтверждается кодом | Minor | Info |

### Feature toggles
| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|----|------------------|-------------|-----------------------|--------|-------------|
| T-01 | CN-05, §4.1.1.1 | Признак `isBphLinkedTradingOpsEnabled()` (и `isBphLinkedCommissionsEnabled()`) | `ExecutionProcess.java:100,104` → `featureToggles.get(FeatureToggleName.ENABLE_BPH_LINKED_COMMISSIONS / ENABLE_BPH_LINKED_TRADING_OPS)`; `FeatureToggleName` enum (`enableBphLinkedCommissions`, `enableBphTradingOperations`) | CONFIRMED | Info |
| T-02 | CN-14 | Новый фича-тогл BPH-ветки доходности (OFF до готовности BPH, kill-switch) | в `FeatureToggleName` нет тогла под `yield`/доходность; в коде нет `if`-ветки на него | NOT FOUND (TO BE) | Major |
| T-03 | CN-14 | «аналог OG-фичи `precalc_commission`» | grep `precalc_commission` по `history-ops` — 0 совпадений (тогл относится к `composite-active-order-commission`, не к OG); ссылка в CN-14 неточна по принадлежности | Minor | Info |

### Поведение и алгоритмы
| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|----|------------------|-------------|-----------------------|--------|-------------|
| B-01 | §4.2.2, CONTEXT_DOC | Цепочка `BphLinkedOperationsGateway → BphLinkedEventsRawConverter → BphLinkedEventsConverterForTrades → BphLinkedTradeOrderBaseConverterForTrades → BphLinkedMainTradeOrderWrapperForTrades → BphLinkedTradeOperationCreator → HistoryOperationBase` существует | все классы найдены в `.../adapter/bph/linked_events/**` и `.../service/conversion/operation/creator/BphLinkedTradeOperationCreator.java` | CONFIRMED | Info |
| B-02 | §4.2.2, D-05 | Чтение из `lead` (`OperationData`) напрямую: `lead.getPrice()`/`lead.getTotalPrice()` дают `PriceData` | `BphLinkedTradeOrderBaseConverterForTrades.convert()` — `PriceData priceData = lead.getPrice(); priceData.getValue()` и `lead.getTotalPrice()` → `totalPriceData.getCurrency()` | CONFIRMED | Info |
| B-03 | §4.2.3-mapping | В wrapper `BphLinkedMainTradeOrderWrapperForTrades` поля `yield` нет (добавляется) | `BphLinkedMainTradeOrderWrapperForTrades.java` — поля `type…trdForcedClose`, `yield` отсутствует | NOT FOUND (TO BE) | Major |
| B-04 | §4.2.2, §4.2.3-mapping | `HistoryOperationLead.builder()` без доходности; перенос в lead | `BphLinkedTradeOperationCreator.createBphHistoryOperationLead()` — `HistoryOperationLead.builder().id(...)....comment(...).build()`, `yield` отсутствует | NOT FOUND (TO BE) | Major |
| B-05 | §4.1.1.2, §4.2.3-mapping | `DetailsResponseMapper.convert(JsonNode)` → `setYield(...)` (пока отсутствует) | `DetailsResponseMapper.java` — `convert(JsonNode source)` с `setCommissionValue(...)` и др., `setYield` отсутствует | NOT FOUND (TO BE) | Major |
| B-06 | §4.1.1.4, CN-11 | Кастомайзер-образец `CommissionCustomizer` (`hasCommissionValue()`/`getCommissionValue()` → `ContentParameter`) | `.../composite/screen/details/operation/sections/customizers/CommissionCustomizer.java` — `operation.hasCommissionValue()`/`getCommissionValue()`, `new ContentParameter("Комиссия", ...)` | CONFIRMED | Info |
| B-07 | CN-15, D-17 | Метрика `history_ops_integration` (`comment=parse_error`, `ex_system=BPH`, `event_type=GET_LINKED_EVENTS`) | `MeterService.java` (`counter("history_ops_integration", ...)`); тестовая фикстура `prometheus-metrics-feed-screen-linked-orders-for-feed.txt:44` — `history_ops_integration_total{comment="parse_error",event_type="GET_LINKED_EVENTS",ex_system="BPH",status="error"}` | CONFIRMED | Info |

## Рекомендуемые действия
1. **C-12 (Minor MISMATCH):** в §4.1.1.1 таблицу «Request headers» исправить значение `systemName` с `si2-ops` на `history_ops` (источник истины — `BphClient.HISTORY_OPS`). Правка через `/resolve-code-alignment` или targeted `/check-feature`.
2. **C-13 (Minor):** уточнить в §4.1.1.1 перечень значений `status` в `OperationData` — в схеме BPH поле строковое (пример `DONE`), в коде маппятся `COMPLETED→EXECUTED`, `CANCELLED→CANCELED`, `EXECUTED`, `PARTIALLY_EXECUTED` (значения `SUBMITTED` нет).
3. **CF-03 (Minor):** снять/переформулировать примечание «HO всегда шлёт `page=0`» — код устанавливает только `pageSize`, `page` не шлёт.
4. **T-03 (Minor):** в CN-14 поправить атрибуцию аналога тогла — `precalc_commission` относится к `composite-active-order-commission`, а не к OG-фиче.
5. **C-03/C-06b/C-07b/B-03/B-04/B-05/T-02 (NOT FOUND, TO BE):** все отсутствующие сущности (`PriceData`, `yield` в proto/yml/BPH-схеме, поле wrapper/lead, `setYield`, тогл) — ожидаемы до реализации; блокеров нет, фиксации как TO BE достаточно.

## Пропущено
- Продакшн-значения `app-config.bph.*` (url, deadline) — живут в Helm/ConfigMap вне `repositories/`; сверены только структура конфига (`BphProperties`) и тестовое значение `pageSizeForLinkedEvents=200`.
- Реализация OG-фичи `og-trading-order-yield` не перепроверялась по коду (она также TO BE): «конфликт с OG» оценивался только по факту отсутствия `PriceData`/`yield`/поля 99 в общих контрактах.
- Внешний контракт BPH (`bph-incoming-gateway`) принадлежит команде BPH: `yield` в `OperationData` — NOT FOUND ожидаемо; проверялось отсутствие поля в локальной OpenAPI-схеме.

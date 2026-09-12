---
report_type: code-alignment
slug: bph-coupons-dividends-monthly-summary
source_document: Feature-writing/bph-coupons-dividends-monthly-summary/bph-coupons-dividends-monthly-summary.md
generated_at: 2026-08-30
alignment_iteration: 3
scope: repositories/ only
language: ru
verdict: PASS WITH GAPS
---

# Отчёт о соответствии коду: bph-coupons-dividends-monthly-summary

**Документ:** `Feature-writing/bph-coupons-dividends-monthly-summary/bph-coupons-dividends-monthly-summary.md`
**Отчёт:** `Feature-writing/bph-coupons-dividends-monthly-summary/bph-coupons-dividends-monthly-summary-code-alignment.md`
**Область проверки:** только код в `repositories/` (приоритет: миграции и entity в коде > `db-export/`)

## Сводка
- CONFIRMED: 40 · MISMATCH: 0 · PARTIAL: 0 · NOT FOUND: 6 · UNVERIFIABLE: 1
- **Вердикт:** PASS WITH GAPS

Блокирующих расхождений (Critical/Major MISMATCH) нет. Все `NOT FOUND` относятся к
проектируемому «с листа» контракту и его точкам встраивания (новый endpoint, новый
toggle, новое поле `history.yml`, новая секция) — ожидаемо до реализации (CN-01) и
не блокер. Описания **существующего** кода в SPEC точны (имена классов, пути,
числа констант/полей, механизмы `Mono.zip`/`onErrorResume`).

## Приоритетные находки

Итерация 3 — повторный прогон после правок раздела 4 (детализация исходящего ответа
`history-ops → screen-api` и структуры/рендера новой секции) и правки подписи поля
в маппинге. Все заявленные изменения перепроверены против фактического кода и
**CONFIRMED**; новых MISMATCH не порождено:

1. **§4.1.1.2 — таблица существующих полей `OperationHistoryResponse` (C-10)** —
   точна: `required`-набор из 6 полей (`clientRequestId`, `resp`, `responseCode`,
   `responseTime`, `bcDataComplete`, `failOperationTypes`), типы и позиции 533–568
   совпадают с `history.yml`.
2. **§4.1.1.2 — JSON-примеры «ДО/ПОСЛЕ» (C-11)** — существующие поля валидны против
   схемы; новое поле `couponsDividendsMonthlySummary` — проектируемое (TO BE).
3. **§4.2.3-mapping — исправление подписи `screen-api.sections[].order` (K-06)** —
   верно: `order` — сосед `content` в `FeedSectionData` (не вложен в `content`).
4. **§4.1.1.2 — ссылки на `FeedSectionData`/`TitleSectionCreator` (K-07)** — точны:
   `TitleSectionCreator.createSection()` (builder 49–56) заполняет `type`, `content`,
   `order` (+ служебные `id`, `container`, `metadata`, отмеченные в SPEC отдельно).
5. **§4.1.1.2/§4.2.3 — `SectionCreatorType` (29 значений) и `PriceData`** — перепроверены
   (K-02, C-05), остаются CONFIRMED.

## Находки по категориям

### Контракты
| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|----|------------------|-------------|-----------------------|--------|-------------|
| C-01 | §4.1.1 «Общая информация», CN-01 | Новый endpoint `POST /api/v1/incoming-gateway/operations/coupons-dividends-monthly-summary` отсутствует в текущем `bph.yml` (paths 13–970) | `repositories/ИО/history-ops/src/main/swagger/bph/bph.yml` — grep по `coupons-dividends-monthly-summary`/`CouponsDividendsMonthlySummary` не находит ни одного вхождения; существующие paths заканчиваются на `/operations/linked-events` (строки 924–970) | NOT FOUND (TO BE, ожидаемо) | Major — не блокер |
| C-02 | §4.1.1, CN-10 | Схемы-образцы существуют: `RequestLinkedData` (1053–1087), `PriceData` (1226), `ResponseStatusData` (1436), `ErrorData` (1443), `Response500Data` (1475) | `bph.yml`: `RequestLinkedData:` =1053, `PriceData:` =1226, `ResponseStatusData:` =1436, `ErrorData:` =1443, `Response500Data:` =1475 — все якоря совпадают | CONFIRMED | Info |
| C-03 | §4.1.1 заголовки | `rqUIDParam` (973, `format: uuid`), `systemNameParam` (982); пример `c4a5dccd-0fe2-4aa1-823e-a5a5d9ee04a4` | `bph.yml:973-981` (`name: rqUID`, `format: uuid`, example `c4a5dccd-0fe2-4aa1-823e-a5a5d9ee04a4`), `bph.yml:982-989` (`name: systemName`, example `si2-ops`) | CONFIRMED | Info |
| C-04 | §4.1.1 таблица запроса | `agreements` pattern `^[A-Za-z\d]{1,16}$`, `startSearchDate`/`endSearchDate` — по образцу `RequestLinkedData` | `bph.yml:1060-1067` (`agreements` pattern `'^[A-Za-z\d]{1,16}$'`), `bph.yml:1068-1075` (`startSearchDate`/`endSearchDate`, `format: date-time`) | CONFIRMED | Info |
| C-05 | §4.1.1 «Поля сводки data», §4.2.3 | Форма `value`+`currency` по образцу `PriceData` (big_decimal value + currency) | `bph.yml:1226-1237` — `PriceData` с `value` (`format: big_decimal`) и `currency` (string) | CONFIRMED | Info |
| C-06 | §4.1.1 «Коды ошибок» | 400 → `ErrorData` (`status`, `error="Bad Request"`, `timestamp`, `path`); 500 → `Response500Data` (`code=500`, `message`) | `bph.yml:1443-1474` (`ErrorData` enum `error: Bad Request / Internal Server Error`), `bph.yml:1475-1490` (`Response500Data` enum `code: 500`) | CONFIRMED | Info |
| C-07 | §4.1.1 «Коды ошибок» | 401 / 403 / 404 / 429 — «авторизация/лимит на уровне шлюза BPH» | В `bph.yml` для endpoint'ов задекларированы только 200/400/500 (см. `/operations/linked-events` `bph.yml:938-970`); 401/403/404/429 в схеме отсутствуют (шлюзовый уровень) | UNVERIFIABLE | Minor |
| C-08 | §4.1.1.2, §4.2.2 | `history.yml`: `PortfolioOperationType` (60–93), `HistoryOperationLead` (456–506, `currency` 481, `total_sum` 488), `OperationHistoryResponse` (533–568, `bcDataComplete` 563, `failOperationTypes` 565) | `repositories/ИО/history-ops/src/main/swagger/history/history.yml`: `PortfolioOperationType:` =60 (enum `coupon`=63, `coupon_output`=64, `dividend_input`=72, `dividend_output`=73), `HistoryOperationLead:` =456 (`currency`=481, `total_sum`=488), `OperationHistoryResponse:` =533 (`bcDataComplete`=563, `failOperationTypes`=565) | CONFIRMED | Info |
| C-09 | §4.1.1.2, маппинг | Новое поле `couponsDividendsMonthlySummary` в `OperationHistoryResponse` (`history.yml`) | `history.yml:533-568` — поле `couponsDividendsMonthlySummary` отсутствует (только `clientRequestId`, `resp`, `responseCode`, `responseTime`, `bcDataComplete`, `failOperationTypes`) | NOT FOUND (TO BE, ожидаемо) | Major — не блокер |
| C-10 | §4.1.1.2 таблица «Существующие поля `OperationHistoryResponse`» | Перечислены 6 существующих полей с типами и required-набором; позиции 533–568 | `history.yml:533-568`: `required` = `clientRequestId`(534), `resp`(535), `responseCode`(536), `responseTime`(537), `bcDataComplete`(538), `failOperationTypes`(539); `clientRequestId`=string(542-543), `resp`=array(544-557) items object required `[operations, counterId]` с `operations`→`HistoryOperationBase[]` и `counterId`=string, `responseCode`=integer(558-559), `responseTime`=string format date-time(560-562), `bcDataComplete`=boolean(563-564), `failOperationTypes`=array(565-568) items `$ref PortfolioOperationType` — совпадает построчно с таблицей SPEC | CONFIRMED | Info |
| C-11 | §4.1.1.2 JSON-примеры «ДО/ПОСЛЕ» | Существующие поля примеров валидны против схемы; отличие «после» — только новое поле `couponsDividendsMonthlySummary` | `history.yml:533-568` — поля примеров (`clientRequestId` uuid, `resp[]` с `operations`+`counterId`, `responseCode:0`, `responseTime` date-time, `bcDataComplete:true`, `failOperationTypes:[]`) соответствуют схеме; новое поле — проектируемое (не в схеме) | CONFIRMED | Info |

### БД и миграции
| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|----|------------------|-------------|-----------------------|--------|-------------|
| D-01 | BR-05, CN-04, §7.1.6 | Сумма за месяц приходит из BPH, а не вычисляется из БД `history_ops`; отдельной таблицы/колонки нет | `db-export/БД ИО.md` — в схеме `history_ops` нет таблицы/колонки для «суммы купонов/дивидендов за месяц» (grep по `monthly`/`summary`/«сводн» не находит); в коде `repositories/` нет entity/миграции под такую сумму | CONFIRMED | Info |
| D-02 | §1.2, BR-06, CN-03 | Типы купонов/дивидендов уже существуют: `coupon` (id 5), `dividend_input` (6), `dividend_output` (11), `coupon_output` (14) | `db-export/БД ИО.md:1540-1549` — `operation_type` id 5/6/11/14; `db-export/БД ИО.md:1695-1705` — маппинг `operation` (coupon→114→1, dividend_input→111→2, dividend_output→112→3, coupon_output→NULL→4) | CONFIRMED | Info |
| D-03 | CN-04, контекст | BPH-subtypes купонов/дивидендов: `INTEREST_PAYMENT_CREDIT`, `CASH_DIVIDEND_CREDIT`, `CASH_DIVIDEND_DEBIT`, `INTEREST_PAYMENT_DEBIT` (все `type_id=1 CA_CASH_MOVEMENT`) | `repositories/ИО/history-ops/.../adapter/bph/BphOperationWrapper.java:22-26` — `CA_CASH_MOVEMENT = "CA_CASH_MOVEMENT"`, `COUPON_DIVIDEND_SUBTYPES = Set.of("INTEREST_PAYMENT_CREDIT","CASH_DIVIDEND_CREDIT","CASH_DIVIDEND_DEBIT","INTEREST_PAYMENT_DEBIT")` | CONFIRMED | Info |

### Интеграции
| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|----|------------------|-------------|-----------------------|--------|-------------|
| I-01 | §4.1.1.1, CN-12 | `BphLinkedOperationsGateway`: `enabled()` (62–66), `exSystem()="BPH"` (127–129), `eventType()="GET_LINKED_EVENTS"` (131–134), `createRequest()` (86–119), `ruleKey()` (144–147) | `repositories/ИО/history-ops/.../adapter/bph/linked_events/BphLinkedOperationsGateway.java` — все якоря совпадают: `enabled()` =62-66, `exSystem()` =127-129 (return `"BPH"`), `eventType()` =131-134 (return `"GET_LINKED_EVENTS"`), `createRequest()` =86-119, `ruleKey()` =144-147 | CONFIRMED | Info |
| I-02 | §4.1.1.1 | `BphLinkedOperationsGateway` extends `AbstractSplitStatusGateway` (возвращает `TListHolder<BphRawLinkedEventsWrapper>`) | `BphLinkedOperationsGateway.java:39` — `extends AbstractSplitStatusGateway<..., BphRawLinkedEventsWrapper, String>`; `getOperationsInternal()` возвращает `Mono<TListHolder<BphRawLinkedEventsWrapper>>` (строки 69–83) | CONFIRMED | Info |
| I-03 | §4.1.1, §5.3.1 | `BphClient`: WebClient, 3 endpoint URL (`LINKED_EVENTS_URL` 17), `systemName=history_ops`, заголовок `rqUID` | `repositories/ИО/history-ops/.../adapter/bph/BphClient.java:15-58` — `OPERATIONS_URL`(15), `OPERATION_TYPES_URL`(16), `LINKED_EVENTS_URL`(17), `SYSTEM_NAME="systemName"`(19), `REQUEST_ID="rqUID"`(20), `HISTORY_OPS="history_ops"`(21) | CONFIRMED | Info |
| I-04 | §4.1.1.1 | `SourceOperationService`: record `SourceOperations` (65–81, 14 полей), `getOperationsFromSources()` (84–198), `Mono.zip(...)` (156–197) из 12 Mono-аргументов | `repositories/ИО/history-ops/.../service/operation/SourceOperationService.java` — record =65-81 (14 полей), метод =84-198, `Mono.zip` =156-197 (12 аргументов: bcMonos, ogOrderAndDeal, ibo, ipoSpo, corpActionsBuyback, corpActionsMeet, corpActionReports, corpActionsSecTransfer, bphDynamicConfig…, bphOperations, bphLinkedEvents, sourcesRequestsInfoMono) | CONFIRMED | Info |
| I-05 | §4.1.1.1 «Ключевая деталь» (строка 757) | Перечень 14 полей record `SourceOperations` перечисляет 13-е поле как `bphLinkedOperations` | `SourceOperationService.java:78` — 13-е поле record = `TListHolder<BphRawLinkedEventsWrapper> bphLinkedOperations`; переменная Mono называется `bphLinkedEvents` (строки 148–152). Перечень SPEC (строка 757) теперь полностью совпадает с фактическим порядком и именами 14 полей (bcOrders…currentRequestsInfo) | CONFIRMED | Info |
| I-06 | §4.1.1.1 | `RpcNamesForRequestCondition`: 9 констант (строки 8–25), включая `bphGetLinkedEvents`, `bphGetOperationsWithDetails` | `repositories/ИО/history-ops/.../adapter/RpcNamesForRequestCondition.java:8-25` — ровно 9 констант: OG_GET_TRADE_ORDERS, BPH_GET_LINKED_EVENTS, BPH_GET_OPERATIONS_WITH_DETAILS, BPH_GET_BPH_ORDERS, DCM_GET_INITIAL_BONDS_OFFERING_HISTORY, ECM_GET_ORDERS_HISTORY, DCA_GET_BUY_BACKS, DCA_GET_MEET_HISTORY, DCA_GET_SEC_TRANSFERS_ORDER_HISTORY | CONFIRMED | Info |
| I-07 | §4.1.1.1, Feature Toggles | `FeatureToggleName`: enum строки 7–28 (20 констант); `enableBphCouponsDividendsMonthlySummary` отсутствует | `repositories/ИО/history-ops/.../adapter/auth/FeatureToggleName.java:7-28` — 20 констант; `enableBphCouponsDividendsMonthlySummary` не найден | NOT FOUND (TO BE, ожидаемо) | Major — не блокер |
| I-08 | §4.1.1.1 | `ExecutionProcess.isBphLinkedCommissionsEnabled()` (100–102), `isBphLinkedTradingOpsEnabled()` (104–106); читает `featureToggles` map | `repositories/ИО/history-ops/.../model/ExecutionProcess.java:100-106` — оба метода `featureToggles.get(FeatureToggleName....)`; `featureToggles` поле =18 | CONFIRMED | Info |
| I-09 | §4.1.1.1, §4.2.2 | Новый метод `ExecutionProcess.isBphCouponsDividendsMonthlySummaryEnabled()` | `ExecutionProcess.java` — метод отсутствует | NOT FOUND (TO BE, ожидаемо) | Major — не блокер |
| I-10 | §4.1.1.1 | `AbstractOperationGateway.getOperations()` (48–84), `getOperationsSafe()` (86–103) с `onErrorResume` | `repositories/ИО/history-ops/.../adapter/AbstractOperationGateway.java:48-103` — `getOperations` =48-84 (enabled→matchFilter→matchInstrumentType→generalStatusFilter→isActiveGateway), `getOperationsSafe` =86-103 с `.onErrorResume(...)` | CONFIRMED | Info |
| I-11 | §4.1.1.1 | `AbstractSplitStatusGateway.generalStatusFilter()` (29–37), `ruleKey()` (25) | `repositories/ИО/history-ops/.../adapter/AbstractSplitStatusGateway.java:25,29-37` | CONFIRMED | Info |
| I-12 | §4.1.1.1, контекст | `BphCommonWrapper.isCouponDividendOperation()` (74–76): `"CA_CASH_MOVEMENT".equals(originalType) && COUPON_DIVIDEND_SUBTYPES.contains(bphType)` | `repositories/ИО/history-ops/.../adapter/bph/common/BphCommonWrapper.java:74-76` | CONFIRMED | Info |
| I-13 | §4.2.2, контекст | `FailOperationTypeService` строки 50–52: `DIVIDEND_INPUT`, `DIVIDEND_OUTPUT`, `COUPON` учитываются в `failOperationTypes` | `repositories/ИО/history-ops/.../service/FailOperationTypeService.java:50-52` — в `DG_DEPENDENT_OPERATION_TYPES` | CONFIRMED | Info |

### Конфигурация
| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|----|------------------|-------------|-----------------------|--------|-------------|
| CF-01 | CN-07, CN-08 | `AppConfigDynamicProperties`: `instrumentFilterRequestsDynamic` (17), `feedRequestsDynamic` закомментирован (18) | `repositories/ИО/history-ops/.../configuration/properties/AppConfigDynamicProperties.java:17-18` — `private Map<String, RequestRule> instrumentFilterRequestsDynamic;` (17), `//  private Map<String, RequestRule> feedRequestsDynamic;` (18) | CONFIRMED | Info |
| CF-02 | CN-07, Feature Toggles | `RequestRuleService`: `getRequestRule()` (15–24), `defaultRule()` (26–39), комментарий «поменять на false…» (33) | `repositories/ИО/history-ops/.../service/RequestRuleService.java:15-39` — `getRequestRule` =15-24, `defaultRule` =26-39, комментарий на строке 33 | CONFIRMED | Info |
| CF-03 | CN-07 | Для feed (`hasInstrumentFilter=false`) `RequestRuleService` подставляет пустую `rulesMap` (`Map.of()`) и возвращает дефолтное правило `RequestRule{active=true, inactive=true}` | `RequestRuleService.java:16-23` — `rulesMap = hasInstrumentFilter ? instrumentFilterRequestsDynamic : Map.of()` (строки 19–20: закомментированный `getFeedRequestsDynamic()` + `Map.of()`); `rulesMap.get(rpcName)` → `null` → `defaultRule(false)`; `defaultRule` =26-39: при `hasInstrumentFilter=false` `setActive(true); setInactive(true)` (строки 34–35). Формулировка CN-07 теперь точно соответствует коду | CONFIRMED | Info |

### Feature toggles
| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|----|------------------|-------------|-----------------------|--------|-------------|
| T-01 | Feature Toggles | Новый toggle `enableBphCouponsDividendsMonthlySummary` (enum `FeatureToggleName`) | `FeatureToggleName.java:7-28` — такого элемента нет | NOT FOUND (TO BE, ожидаемо) | Major — не блокер |
| T-02 | Feature Toggles, CN-07 | На ленте механизм `feedRequestsDynamic` не заведён (для включения нужен ключ `bphGetCouponsDividendsMonthlySummary`) | `AppConfigDynamicProperties.java:18` (закомментирован), `RequestRuleService.java:19` (для feed подставлен `Map.of()`) | CONFIRMED | Info |

### Поведение и алгоритмы
| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|----|------------------|-------------|-----------------------|--------|-------------|
| B-01 | §4.2.2 | `OperationCollectorAllOperationService.getOperations()` (37–50), `processOperations()` (60–78); таймер `history_ops_time{ex_system="NONE", event_type="PROCESS_OPERATIONS"}` (77) | `repositories/ИО/history-ops/.../service/execution/OperationCollectorAllOperationService.java:37-50,60-78` — `recordPercentile(result, "NONE", "PROCESS_OPERATIONS")` =77 | CONFIRMED | Info |
| B-02 | CN-13 | `BphConverter.printLocalDateTimeAtZeroTimeZone` — границы месяца в UTC | `repositories/ИО/history-ops/.../adapter/bph/BphConverter.java:186-190` — метод существует, конвертирует `LocalDateTime` в `ZoneId.of("GMT")` | CONFIRMED | Info |
| B-03 | §5.3.1 | `IntegrationLogService`: `callType`=`OUT` при `initiatedByHistoryOps=true` (88, 226); `toJson()` (301–310) с `bodyMaxBytes` | `repositories/ИО/history-ops/.../logger/IntegrationLogService.java:88,226,301-310` | CONFIRMED | Info |
| B-04 | §5.3.1 | `RequestService.execute`: `logRequest` (30), `logResponse` (33), `doOnError` (34), `recordPercentile` (35), `addIntegrationMetric` (36) | `repositories/ИО/history-ops/.../adapter/RequestService.java:30-36` — все якоря совпадают | CONFIRMED | Info |
| B-05 | §5.3.1 | `ListRequestService.convert` (74–76): WARN «Failed to convert …» + `countIntegrationError(..., "parse_error", ...)` | `repositories/ИО/history-ops/.../adapter/ListRequestService.java:73-77` | CONFIRMED | Info |
| B-06 | §5.3.2 | `MeterService`: `recordPercentile` (20–30), `addIntegrationMetric` (32–38), `countIntegrationError` (44–46), `countIntegrationInternal` (52–63); теги `ex_system`/`event_type`/`comment`/`status` | `repositories/ИО/history-ops/.../service/meter/service/MeterService.java:20-63` — percentiles `{0.5,0.75,0.85,0.95,0.99}` =16, counter `history_ops_integration` =57-62 | CONFIRMED | Info |
| B-07 | §5.3.2 | Метрика `response_size` (comment) применяется в `ListRequestService` (40), для новой ручки-агрегата не применяется | `ListRequestService.java:40` — `countIntegration(exSystem, eventType, "response_size", list.size())` | CONFIRMED | Info |
| B-08 | §5.3.1 | `ReactorMdcContext` (record, 8–19) | `repositories/ИО/history-ops/.../logger/ReactorMdcContext.java:8-19` | CONFIRMED | Info |

### Композит (history-ops-screen-api)
| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|----|------------------|-------------|-----------------------|--------|-------------|
| K-01 | §4.1.1.2, CN-09 | `SectionCreatorRegistry.resolveType()` switch (37–70): `COUPON → COUPON_INPUT`, `DIVIDEND_INPUT → DIVIDEND_INPUT` | `repositories/ИО/history-ops-screen-api/.../composite/sections/feed/SectionCreatorRegistry.java:37-70` — `case COUPON -> SectionCreatorType.COUPON_INPUT` =56, `case DIVIDEND_INPUT -> SectionCreatorType.DIVIDEND_INPUT` =58 | CONFIRMED | Info |
| K-02 | §4.1.1.2 | `SectionCreatorType` — 29 значений | `repositories/ИО/history-ops-screen-api/.../enums/SectionCreatorType.java:5-33` — ровно 29 значений (TITLE…TRANSACTION_SELL). Спека верна (29). Примечание: в `Feature-context/…md` указано «34 значения» — это не SPEC, но на будущее число в контексте следует поправить | CONFIRMED | Info |
| K-03 | §4.1.1.2, CN-11 | `TitleSectionCreator.createSection()` → тип `history.feed.title` (49–57) | `repositories/ИО/history-ops-screen-api/.../composite/sections/feed/section/creators/TitleSectionCreator.java:43-57` — `.type("history.feed.title")` =50 | CONFIRMED | Info |
| K-04 | §4.1.1.2 | `CompositeScreenService.getFeed()` / `getScreenForOperation()` (9–11) | `repositories/ИО/history-ops-screen-api/.../services/screen/composite/CompositeScreenService.java:9-11` | CONFIRMED | Info |
| K-05 | §4.1.1.2, §4.2.2 | Новый тип секции `history.feed.couponsDividendsSummary` (`SectionCreatorType`) | `SectionCreatorType.java` — такого значения нет | NOT FOUND (TO BE, ожидаемо) | Major — не блокер |
| K-06 | §4.1.1.2 «Структура и рендер», §4.2.3-mapping | `order` — сосед `content` в `FeedSectionData` (не вложен); подпись `screen-api.sections[].order` | `repositories/ИО/history-ops-screen-api/.../models/FeedSectionData.java:14-24` — поля `int id`(14), `String type`(16), `Integer order`(18), `Container container`(20), `Metadata metadata`(22), `ContentData content`(24): `order` и `content` — равноправные соседние поля. Исправление подписи `screen-api.sections[].content.order` → `screen-api.sections[].order` (§4.2.3, строка 1057) верно; JSON-пример (§4.2.3, строка 1117–1126) тоже корректен (`order` на верхнем уровне секции) | CONFIRMED | Info |
| K-07 | §4.1.1.2 «Структура и рендер», CN-11 | `TitleSectionCreator.createSection()` возвращает `FeedSectionData` (builder 49–56), заполняет `type`, `content`, `order` (+ служебные `id`, `container`, `metadata`) | `TitleSectionCreator.java:49-56` — `FeedSectionData.builder().type("history.feed.title").id(sectionId).container(titleContainer).content(titleContent).order(sectionId).metadata(metadata).build()`; SPEC корректно перечисляет `type`/`content`/`order` как прямые поля и отдельно отмечает `id`/`container`/`metadata` как служебные (строка 881) | CONFIRMED | Info |

## Рекомендуемые действия
1. **C-07 (UNVERIFIABLE)** — коды 401/403/404/429 не задекларированы в `bph.yml` (шлюзовый уровень). Для полноты можно пометить их в SPEC как «предполагаемые на уровне шлюза, в `bph.yml` не описаны» — не критично.
2. **Feature-context (не SPEC)** — число значений `SectionCreatorType` в контексте («34») расходится с фактическими 29; SPEC верна, но контекст стоит поправить при следующем refresh.

Замечаний по изменённому контенту (итерация 3) нет: таблица существующих полей
`OperationHistoryResponse`, JSON-примеры, структура секции и исправленная подпись
`screen-api.sections[].order` соответствуют коду.

## Пропущено
- Генерация DTO из OpenAPI (rebuild-конвейер) — не проверялась: за пределами `repositories/` (сборочный процесс).
- Runtime-поведение таймаутов/retry `BphClient` (значения в `application*.yml`/ConfigMap) — специфика наследует `BphClient`, конкретные числовые значения в SPEC не заявлены.
- Проверка ответов 401/403/404/429 на стенде — вне контура кода.
- Точные UI-лейблы/порядок строк сводной секции — помечены в SPEC как проектируемые (финализация UI), вне контура `repositories/`.

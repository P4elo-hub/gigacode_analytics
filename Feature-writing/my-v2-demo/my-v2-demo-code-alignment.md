---
report_type: code-alignment
slug: my-v2-demo
source_document: Feature-writing/my-v2-demo/my-v2-demo.md
generated_at: 2026-09-25
alignment_iteration: 1
scope: repositories/ only
language: ru
verdict: PASS WITH GAPS
---

# Отчёт о соответствии коду: my-v2-demo

**Документ:** `Feature-writing/my-v2-demo/my-v2-demo.md`
**Отчёт:** `Feature-writing/my-v2-demo/my-v2-demo-code-alignment.md`
**Область проверки:** только код в `repositories/` (справочник — `db-export/БД ИО.md`)

## Сводка
- CONFIRMED: 35 · MISMATCH: 0 · PARTIAL: 1 · NOT FOUND: 8 · UNVERIFIABLE: 0
- **Вердикт:** PASS WITH GAPS

## Приоритетные находки

Фокус по указаниям брифа проверен первым и глубже:

1. **Отсутствие endpoint месячной сводки в `bph.yml` — подтверждено.** Все 13 существующих paths перечислены; пути `monthly-summary`/`summary` нет (grep по `monthly|summary` даёт только OpenAPI-поля `summary:` описаний). CN-01/CN-04 корректны.
2. **Образец gateway `BphLinkedOperationsGateway` — подтверждён** как точная модель параллельного source-запроса: `eventType()="GET_LINKED_EVENTS"`, `exSystem()="BPH"`, `getOperationsInternal` → `bphClient.getLinkedEvents`, `createRequest` → `RequestLinkedData`.
3. **Типы операций — подтверждены:** `BphOperationWrapper.CA_CASH_MOVEMENT` + `COUPON_DIVIDEND_SUBTYPES`, предикат `BphCommonWrapper.isCouponDividendOperation()`, БД-маппинг `coupon`/`coupon_output`/`dividend_input`/`dividend_output` ↔ `operation_type` id 5/14/6/11 ↔ `bph` id 1/4/2/3.
4. **Проектируемый контракт monthly-summary — ожидаемо NOT FOUND** (ручки ещё нет): `getMonthlySummary`, `RequestMonthlySummaryData`, `MonthlySummaryData`, `eventType=GET_MONTHLY_SUMMARY`, тогл `enable_monthly_summary`, секция `history.feed.monthlySummary` — всё отсутствует в коде и не является MISMATCH.

## Находки по категориям

### Контракты
| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|---|---|---|---|---|---|
| C-01 | §4.1.1 (CN-01, CN-04) | `bph.yml` не содержит endpoint месячной сводки | `repositories/ИО/history-ops/src/main/swagger/bph/bph.yml` — 13 paths, нет `/operations/monthly-summary`; grep `monthly\|summary` → только `summary:` OpenAPI-описаний | CONFIRMED | Info |
| C-02 | §4.1.1 | `info.title` = `BPH Incoming-gateway` | `bph.yml:3` `title: BPH Incoming-gateway` | CONFIRMED | Info |
| C-03 | §4.1.1 | Существующие обмены: GET_OPERATIONS_WITH_DETAILS `POST /operations-with-details`, GET_OPERATION_TYPES `GET /operation-types`, GET_LINKED_EVENTS `POST /operations/linked-events` | `BphClient.java` (`OPERATIONS_URL`, `OPERATION_TYPES_URL`, `LINKED_EVENTS_URL`); `bph.yml:216/393/924` | CONFIRMED | Info |
| C-04 | §4.1.1 (CN-05) | Заголовки `rqUID` + `systemName`; `systemName = history_ops` (код побеждает analytics `si2-ops`) | `BphClient.java`: `HISTORY_OPS = "history_ops"`, `.header("systemName", HISTORY_OPS)`, `.header("rqUID", requestId)`. (Примечание: `bph.yml:996` `systemNameParam` example `si2-ops` — только OpenAPI-пример, runtime-значение из кода `history_ops`.) | CONFIRMED | Info |
| C-05 | §4.1.1 | Энвелоп `{status: ResponseStatusData{code,message}, data}`; ошибка `ErrorData` | `bph.yml:1434-1457` `ResponseStatusData` (code:integer, message:string), `ErrorData` (timestamp, status, error, path) | CONFIRMED | Info |
| C-06 | §4.1.1 | Образец `RequestLinkedData`: `agreements` (maxItems 100, pattern `^[A-Za-z\d]{1,16}$`, example `KJ28438H394L`), `startSearchDate`/`endSearchDate` (date-time), `dateForFilter` | `bph.yml:1043-1077` `RequestLinkedData` | CONFIRMED | Info |
| C-07 | §4.1.1 | `LinkedEventsData.agreement` maxLength 255, example `420012W` | `bph.yml:977-982` `LinkedEventsData.agreement` | CONFIRMED | Info |
| C-08 | §4.1.1 | `FilterDateEnum` = EVENT_DATE / FORMATION_DATE | `bph.yml:1420-1425` | CONFIRMED | Info |
| C-09 | §4.1.1 (CN-11) | `CurrencyEnum` = RUB / USD / SUR | `adapter/bph/enums/CurrencyEnum.java:4,6,33` | CONFIRMED | Info |
| C-10 | §4.1.1 | Новый endpoint `POST /api/v1/incoming-gateway/operations/monthly-summary`, request `RequestMonthlySummaryData`, response `MonthlySummaryData` | Нет в `bph.yml` (grep `monthly-summary` → 0); TO BE, ручка проектируется | NOT FOUND | Major (TO BE) |
| C-11 | §4.1.1 | Новый метод `getMonthlySummary` в `BphClient` | `BphClient.java` содержит только `getOperations`/`getLinkedEvents`/`getConfig`; `getMonthlySummary` нет | NOT FOUND | Major (TO BE) |
| C-12 | §4.1.1 | Коды ответов 400/500; `ErrorData` error enum `Bad Request`/`Internal Server Error` | `bph.yml:1451-1463` `ErrorData` enum; linked-events `'400'`→`ErrorData`, `'500'`→`Response500Data` | CONFIRMED | Info |

### БД и миграции
| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|---|---|---|---|---|---|
| DB-01 | §4.2.3 | `type` id=1 → `CA_CASH_MOVEMENT` | `db-export/БД ИО.md:312,1519,2785` | CONFIRMED | Info |
| DB-02 | §4.2.3 | `operation_type`: id=5 `coupon`, id=6 `dividend_input`, id=11 `dividend_output`, id=14 `coupon_output` | `db-export/БД ИО.md:329-338,1540-1549` | CONFIRMED | Info |
| DB-03 | §4.2.3 | `bph`: id=1 INTEREST_PAYMENT_CREDIT, id=2 CASH_DIVIDEND_CREDIT, id=3 CASH_DIVIDEND_DEBIT, id=4 INTEREST_PAYMENT_DEBIT (все type_id=1) | `db-export/БД ИО.md:410-413,1637-1640,2878-2881` | CONFIRMED | Info |
| DB-04 | §4.2.3 | `operation`: id=5→(5, bph 1), id=6→(6, bph 2), id=12→(11, bph 3), id=15→(14, bph 4); `bc_id` для id=15 отсутствует (NULL) | `db-export/БД ИО.md:1695-1705` | CONFIRMED | Info |
| DB-05 | §4.2.3 | `MonthlySummary` — транзитная сущность, НЕ персистируется, не попадает в `operation_type`/`operation` | Новых сущностей/миграций под сводку нет (grep `MonthlySummary` → 0); TO BE-транзит | NOT FOUND | Major (TO BE) |
| DB-06 | §4.2.3 | Существующие таблицы `type`/`operation_type`/`bph`/`operation`/`info` не изменяются | `db-export/БД ИО.md` (AS IS-данные не затрагиваются фичей; миграции без новых changeset под сводку) | CONFIRMED | Info |

### Интеграции
| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|---|---|---|---|---|---|
| I-01 | §4.1.1 (CN-02) | `BphLinkedOperationsGateway extends AbstractSplitStatusGateway`; `eventType()="GET_LINKED_EVENTS"`, `exSystem()="BPH"` | `BphLinkedOperationsGateway.java:38,124-132` | CONFIRMED | Info |
| I-02 | §4.1.1 | `createRequest` → `RequestLinkedData` (agreements, startSearchDate/endSearchDate, pageSize=`pageSizeForLinkedEvents()`, `FilterDateEnum`) | `BphLinkedOperationsGateway.java:82-118` | CONFIRMED | Info |
| I-03 | §4.1.1 | `getOperationsInternal` → `bphClient.getLinkedEvents(requestId, request)` | `BphLinkedOperationsGateway.java:63-77` | CONFIRMED | Info |
| I-04 | §4.1.1 (CN-08) | `SourceOperationTradeService.getOperationsFromSources` объединяет источники через `Mono.zip` (bcMonos, dealsFromOg, bphLinkedEvents) | `SourceOperationTradeService.java:66-99` | CONFIRMED | Info |
| I-05 | §4.1.1 (CN-08) | `SourceOperationService.getOperationsFromSources` — `Mono.zip` по множеству источников (включая `bphLinkedEvents`) | `SourceOperationService.java:141-197` | CONFIRMED | Info |
| I-06 | §1.1 Use Case (4a.1) | `DG_DEPENDENT_OPERATION_TYPES` включает DIVIDEND_INPUT, DIVIDEND_OUTPUT, COUPON (без COUPON_OUTPUT) | `FailOperationTypeService.java:37-50` | CONFIRMED | Info |
| I-07 | §4.2.2 | Новый gateway месячной сводки + параллельный source-запрос к `monthly-summary` | Нет в `repositories/` (grep `getMonthlySummary`/`MonthlySummary` → 0); TO BE | NOT FOUND | Major (TO BE) |

### Конфигурация
| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|---|---|---|---|---|---|
| CFG-01 | §4.1.1, §5 | `BphProperties @ConfigurationProperties(prefix="app-config.bph")`: `deadline`, `url`, `pageSizeForLinkedEvents`, `pageSizeForTrades` | `configuration/properties/BphProperties.java:5-11` | CONFIRMED | Info |
| CFG-02 | §5 (D-01) | Новый ключ конфига (URL/pageSize сводки) в `BphProperties` | `BphProperties.java` — только 4 существующих поля; нового ключа нет | NOT FOUND | Major (TO BE) |
| CFG-03 | §5.2.x | `application.yml` композита: `spring.cache.type=caffeine` spec `expireAfterWrite=1m`; hikari `schema=history_ops_screen_api`, `connection-timeout=30000`, `maximum-pool-size=10`; `history.ops.feed.transactions.executor.threads=5`; `history.ops.details.transaction.executor.threads=5`; `ignite.threads.pool` coreSize=3/maxSize=5/queueCapacity=100; `history.ops.details.service.channel.deadline=1s`, `negotiationType=PLAINTEXT` | `history-ops-screen-api/src/main/resources/application.yml` (соответствующие ключи) | CONFIRMED | Info |

### Feature toggles
| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|---|---|---|---|---|---|
| T-01 | §5 (CN-09, D-07) | Тогл `enable_monthly_summary`, default `false` (OFF), runtime через AUTH `getSession` (не `application.yml`) | Самого toggle нет (grep `enable_monthly_summary` → 0); механизм runtime-тоглов через `getSession` подтверждён (`test/.../expected_integration_log_...txt` — `GET_SESSION` с `microservicefeaturetoggles`). TO BE | NOT FOUND | Major (TO BE) |

### Поведение и алгоритмы
| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|---|---|---|---|---|---|
| B-01 | §4.1.1, CN-07 | `BphOperationWrapper.CA_CASH_MOVEMENT="CA_CASH_MOVEMENT"`; `COUPON_DIVIDEND_SUBTYPES={INTEREST_PAYMENT_CREDIT, CASH_DIVIDEND_CREDIT, CASH_DIVIDEND_DEBIT, INTEREST_PAYMENT_DEBIT}` | `BphOperationWrapper.java:20,22-24` | CONFIRMED | Info |
| B-02 | §4.1.1 | `BphCommonWrapper.isCouponDividendOperation() = "CA_CASH_MOVEMENT".equals(originalType) && COUPON_DIVIDEND_SUBTYPES.contains(bphType)` | `BphCommonWrapper.java:68-70` | CONFIRMED | Info |
| B-03 | §1.x, §4.2.2 | `ScreenController`: `POST /history/api/public/v1/screens/feed` (`getFeed`), `GET /operationDetails/{id}` (`getOperationById`) | `ScreenController.java:32,55,77` | CONFIRMED | Info |
| B-04 | §4.2.2 | `AbstractSectionCreator`: типы секций `history.feed.operationActive` / `history.feed.operation` | `AbstractSectionCreator.java:69-76` | CONFIRMED | Info |
| B-05 | §4.2.2 | `TitleSectionCreator`: `history.feed.title` | `TitleSectionCreator.java:47-56` | CONFIRMED | Info |
| B-06 | §1.x, §4.2.2 | `InstrumentFeedFilter` (isin, ticker); subtype `INSTRUMENT` | `InstrumentFeedFilter.java:11-15`; `AbstractFeedFilter.java:23` `@JsonSubTypes ... name="INSTRUMENT"`; `FeedFilterType.java:9` `INSTRUMENT` | CONFIRMED | Info |
| B-07 | §4.2.2 (D-06) | Новая секция `history.feed.monthlySummary` (транзитный рендер) | Нет в `repositories/` (grep `monthlySummary` → 0); TO BE | NOT FOUND | Major (TO BE) |
| B-08 | §4.2.4 | Источник подтверждения — код `BphOperationWrapper.COMPUTED_SUBTYPES`/`COUPON_DIVIDEND_SUBTYPES` | `BphOperationWrapper.java` — есть только `COUPON_DIVIDEND_SUBTYPES`; константы `COMPUTED_SUBTYPES` в коде нет (grep `COMPUTED_SUBTYPES` → 0) | PARTIAL | Minor |

### Логирование и метрики (observability)
| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|---|---|---|---|---|---|
| O-01 | §5 (Логирование) | `LoggerConstants.HIDDEN_TEXT = "*****"` | `logger/LoggerConstants.java:5` | CONFIRMED | Info |
| O-02 | §5 (Логирование) | `IntegrationLogService`: `callType = initiatedByHistoryOps ? "OUT" : "IN"`; `toJson` усечение до `bodyMaxBytes` с текстом `"Oops.. content is too long"`; сообщение `"Integration log entry"` | `logger/IntegrationLogService.java:20,88,226,301-304` | CONFIRMED | Info |
| O-03 | §5 (Метрики) | `MeterService`: `recordPercentile`, `addIntegrationMetric`, `countIntegration*`, `countGeneral*`, `countOperationTypes` | `service/meter/service/MeterService.java:20,32,40-80` | CONFIRMED | Info |
| O-04 | §5 (Метрики) | Композит: `operations_feed_requests_total/duration/errors_total`, `operation_details_requests_total/duration/errors_total` | `history-ops-screen-api/.../HistoryOpsServiceProxy.java:58-64` | CONFIRMED | Info |
| O-05 | §5 (Логирование) | `system="SI"` (`SystemLogJsonProvider`); журнал `system.log` | `logger/layout/SystemLogJsonProvider.java:16,44`; `logback-test.xml` `system_log_file=./log/system.log` | CONFIRMED | Info |
| O-06 | §5 (Логирование) | `ReactorMdcContext`: `traceId`, `sessionId`, `ucpId`, `requestId`, `eventType`, `exSystem`, `duration` | `logger/ReactorMdcContext.java:9-16` | CONFIRMED | Info |
| O-07 | §5 (Логирование, D-01) | `eventType = GET_MONTHLY_SUMMARY` | Нет в `repositories/` (grep `GET_MONTHLY_SUMMARY` → 0); TO BE | NOT FOUND | Major (TO BE) |

## Рекомендуемые действия
1. **B-08 (§4.2.4)** — убрать несуществующую константу `BphOperationWrapper.COMPUTED_SUBTYPES` из ссылки на источник: в коде есть только `COUPON_DIVIDEND_SUBTYPES`. Формулировка «код `BphOperationWrapper.COMPUTED_SUBTYPES`/`COUPON_DIVIDEND_SUBTYPES`» → оставить только `COUPON_DIVIDEND_SUBTYPES`. Правка — через `/check-feature` (формулировка, не блокер).
2. **C-10/C-11/CFG-02/B-07/O-07/T-01 (TO BE)** — оставить как есть: все NOT FOUND относятся к проектируемому контракту/секции/тоглу, которые BPH и history-ops реализуют по спеке; фиксировать «TO BE до реализации» не требуется (уже явно зафиксировано в документе). После реализации ручки BPH и подключения gateway — повторный прогон `/check-feature-code`.

## Пропущено
- Проверка фактических значений внешнего конфига `app-config.bph.deadline`/`url` (значения вне репозитория, в `repositories/` отсутствуют) — документ сам помечает их «значение вне репозитория», что корректно.
- Значения prod-логов `service`/`environment` (конфигурация вне репозитория) — документ помечает как «не задаётся» (CN-13), расхождений нет.

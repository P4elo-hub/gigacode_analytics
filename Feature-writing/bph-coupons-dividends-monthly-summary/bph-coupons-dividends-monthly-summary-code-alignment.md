---
report_type: code-alignment
slug: bph-coupons-dividends-monthly-summary
source_document: Feature-writing/bph-coupons-dividends-monthly-summary/bph-coupons-dividends-monthly-summary.md
generated_at: 2026-09-16
alignment_iteration: 1
scope: repositories/ only
language: ru
verdict: PASS WITH GAPS
---

# Отчёт о соответствии коду: bph-coupons-dividends-monthly-summary

**Документ:** `Feature-writing/bph-coupons-dividends-monthly-summary/bph-coupons-dividends-monthly-summary.md`
**Отчёт:** `Feature-writing/bph-coupons-dividends-monthly-summary/bph-coupons-dividends-monthly-summary-code-alignment.md`
**Область проверки:** только код в `repositories/` (сервисы `history-ops`, `history-ops-screen-api`)

## Сводка
- CONFIRMED: 32 · MISMATCH: 0 · PARTIAL: 1 · NOT FOUND: 5 · UNVERIFIABLE: 0
- **Вердикт:** PASS WITH GAPS

Обоснование вердикта: фича интеграционно-экранная, TO BE-часть (новая ручка BPH, новый gateway, расширение `history.yml`, новая секция композита) проектируется в спеке и ещё не реализована в коде — все TO BE-заявления ожидаемо NOT FOUND. Все AS IS-якоря спеки (BphClient, BphLinkedOperationsGateway, bph.yml/history.yml схемы, справочники БД, toggles, конфиги, метрики, лог-фреймворк, screen-api) подтверждены по коду с путём и якорем. Critical/Major MISMATCH нет.

## Приоритетные находки

Пользователь запросил углублённую проверку расхождения `systemName` (`si2-ops` в swagger vs `history_ops` в коде). Результат — **CONFIRMED, расхождение корректно зафиксировано в спеке**:

- `repositories/ИО/history-ops/src/main/swagger/bph/bph.yml:982-989` — параметр `systemNameParam`, `example: si2-ops`.
- `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/adapter/bph/BphClient.java:24` — `private static final String HISTORY_OPS = "history_ops";` (значение заголовка `systemName` в коде).
- Спека (§2 CN-01, §4.1.1, §5.1, §5.4) фиксирует `systemName = history_ops` по решению D-05 — это значение из кода (источник истины), swagger-пример `si2-ops` — задокументированное расхождение. **Нет MISMATCH**: спека корректно приняла код.

## Находки по категориям

### Контракты

| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|----|------------------|-------------|-----------------------|--------|-------------|
| C-01 | §2 CN-01, §4.1.1 | `BphClient` имеет ровно три метода `getOperations`/`getLinkedEvents`/`getConfig`, константы URL и `HISTORY_OPS="history_ops"` | `repositories/ИО/history-ops/src/main/java/.../adapter/bph/BphClient.java:16-60` — `OPERATIONS_URL`, `OPERATION_TYPES_URL`, `LINKED_EVENTS_URL`, `HISTORY_OPS="history_ops"`, `SYSTEM_NAME="systemName"`, `REQUEST_ID="rqUID"`; три метода POST/GET | CONFIRMED | Info |
| C-02 | §4.1.1 | `RequestLinkedData`: `agreements` maxItems 100, `dateForFilter`=`FilterDateEnum`, `page` 0–1000, `pageSize` 1–4000 | `repositories/ИО/history-ops/src/main/swagger/bph/bph.yml:1053-1087` — `agreements` `maxItems: 100`, `dateForFilter: $ref FilterDateEnum`, `page` min 0 max 1000, `pageSize` min 1 max 4000 | CONFIRMED | Info |
| C-03 | §4.1.1 | `OperationData` (`type/subType/subtype/additionalType/formationDate/eventDate/price/totalPrice/quantity/status/instrument/…`) и `DetailsData` (`lead`+`details`) | `bph.yml:1088` (OperationData), `bph.yml:1238` (DetailsData: `lead $ref OperationData` + `details[] DetailData`) | CONFIRMED | Info |
| C-04 | §4.1.1 | `PriceData`: `value` (string, big_decimal) + `currency` | `bph.yml:1226-1235` — `value: format: big_decimal`, `currency: string` | CONFIRMED | Info |
| C-05 | §4.1.1 | `ResponseStatusData`: `code` (integer) + `message` (string) | `bph.yml:1436-1442` | CONFIRMED | Info |
| C-06 | §4.1.1 | `FilterDateEnum`: `EVENT_DATE` / `FORMATION_DATE` | `bph.yml:1420-1426` — enum из двух значений | CONFIRMED | Info |
| C-07 | §4.1.1 | Коды ошибок: `ErrorData` (status 400/500) и `Response500Data` (code=500) | `bph.yml:1443-1473` (ErrorData: required timestamp/status/error/path, enum 400/500), `bph.yml:1475` (Response500Data enum 500) | CONFIRMED | Info |
| C-08 | §4.1.1.1 | `OperationHistoryResponse`: `clientRequestId`, `resp[operations+counterId]`, `responseCode`, `responseTime`, `bcDataComplete`, `failOperationTypes` | `repositories/ИО/history-ops/src/main/swagger/history/history.yml:533-577` — required/свойства совпадают, `failOperationTypes` → `PortfolioOperationType[]` | CONFIRMED | Info |
| C-09 | §4.1.1.1 | `HistoryOperationBase` = `lead` (HistoryOperationLead) + `agreementDetails` + `instrumentDetails` + `details` | `history.yml:507-533` — `HistoryOperationBase` c `lead`/`agreementDetails`/`instrumentDetails`/`details` | CONFIRMED | Info |
| C-10 | §4.1.1 (TO BE) | Endpoint `POST /api/v1/incoming-gateway/operations/coupons-dividends-monthly-summary`, схемы `RequestCouponsDividendsMonthlySummaryData`/`CouponsDividendsMonthlySummaryData` | Grep по `coupons-dividends-monthly-summary|monthlySummary|monthly-summary|CouponsDividends` в `repositories/ИО` — **0 совпадений**; `bph.yml` endpoint отсутствует | NOT FOUND (TO BE) | Major |
| C-11 | §4.1.1.1 (TO BE) | Поле `couponsDividendsMonthlySummary` в `OperationHistoryResponse` (history.yml) | `history.yml` — поле отсутствует (grep `couponsDividends` — 0 совпадений) | NOT FOUND (TO BE) | Major |
| C-12 | §2 CN-01, §5.1 | `systemName = history_ops` (решение D-05), swagger-пример `si2-ops` — расхождение задокументировано | `BphClient.java:24` (`HISTORY_OPS="history_ops"`) vs `bph.yml:982-989` (`example: si2-ops`) | CONFIRMED | Info |
| C-13 | §5.1 | Security scheme в `bph.yml` не объявлена (AS IS) | `bph.yml` — есть `openapi: 3.0.1`/`paths:`/`components:`, нет `securitySchemes`/`security:` | CONFIRMED | Info |
| C-14 | §4.1.1.2 | Вход композита `POST /history/api/public/v1/screens/feed` | `repositories/ИО/history-ops-screen-api/src/main/java/.../controllers/ScreenController.java:15` `@RequestMapping("/history/api/public/v1/screens")` + `:67` `@PostMapping("/feed")` | CONFIRMED | Info |

### БД и миграции

| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|----|------------------|-------------|-----------------------|--------|-------------|
| D-01 | §4.2.3 | Маппинг `operation.id`: coupon→5, dividend_input→6, dividend_output→12, coupon_output→15 | `repositories/ИО/history-ops/src/test/resources/db/init/create_schema.sql:189-204` — `(5,5,114,1,'Зачисление купона')`, `(6,6,111,2,'Зачисление дивидендов')`, `(12,11,112,3,'Списание дивидендов')`, `(15,14,NULL,4,'Списание купонов')` | CONFIRMED | Info |
| D-02 | §4.2.3 | `bph`: id 1–4 = INTEREST_PAYMENT_CREDIT / CASH_DIVIDEND_CREDIT / CASH_DIVIDEND_DEBIT / INTEREST_PAYMENT_DEBIT, `type_id=1` | `create_schema.sql:159-163` — `(1,'INTEREST_PAYMENT_CREDIT',1)`, `(2,'CASH_DIVIDEND_CREDIT',1)`, `(3,'CASH_DIVIDEND_DEBIT',1)`, `(4,'INTEREST_PAYMENT_DEBIT',1)` | CONFIRMED | Info |
| D-03 | §4.2.3 | `type.id=1` = `CA_CASH_MOVEMENT` | `create_schema.sql:135-137` — `(1, 'CA_CASH_MOVEMENT')` | CONFIRMED | Info |
| D-04 | §4.2.3 | Таблица `bph_bc` (id, bph_type_id FK→type.id, bph_subtype, is_active) | `create_schema.sql:91-96` — `bph_type_id INTEGER NOT NULL REFERENCES history_ops.type(id)`, `bph_subtype`, `is_active` | CONFIRMED | Info |
| D-05 | §4.2.3 | `operation.bc_id` → `bph_bc.id` | В тестовой схеме `create_schema.sql:50` `bc_id INTEGER REFERENCES history_ops.bc(id)` (ссылка на legacy `bc`), тогда как `db-export/БД ИО.md:42,2735` фиксирует актуальную BC-ветку `bc_id → bph_bc.id` (changeset `20250813_SIHIST-3426_create_bph_bc_tables.sql` отсутствует в main-changelog репозитория). Значения id совпадают (114/111/112 в обеих таблицах) | PARTIAL | Minor |
| D-06 | §4.2.3 | Нет DDL-миграции; `CouponsDividendsMonthlySummaryData` не персистируется | В main-changelog `repositories/ИО/history-ops/src/main/resources/db/changesets/` нет новых таблиц под агрегат; схема не меняется — заявление о «без миграции» согласуется | CONFIRMED | Info |
| D-07 | §4.2.3 | screen-api таблицы `section`/`content`/`container`/`screen`/`screen_section` | `repositories/ИО/history-ops-screen-api/liquibase/changesets/init_schema_SIHIST_3380.xml` — createTable `container`/`content`/`section`/`screen_section` (столбец `is_visible` boolean default true)/`screen_data`/`screen` | CONFIRMED | Info |

### Интеграции

| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|----|------------------|-------------|-----------------------|--------|-------------|
| I-01 | §2 CN-04, §4.1.1 | `BphLinkedOperationsGateway`: `eventType()="GET_LINKED_EVENTS"`, `exSystem()="BPH"`, `ruleKey()=BPH_GET_LINKED_EVENTS`, `enabled()=isBphLinkedCommissionsEnabled()\|\|isBphLinkedTradingOpsEnabled()` | `repositories/ИО/history-ops/src/main/java/.../adapter/bph/linked_events/BphLinkedOperationsGateway.java:110-130` — `exSystem()→"BPH"`, `eventType()→"GET_LINKED_EVENTS"`, `ruleKey()→RpcNamesForRequestCondition.BPH_GET_LINKED_EVENTS.getConfigMapKey()`, `enabled()` строка 64 | CONFIRMED | Info |
| I-02 | §4.1.1 (TO BE) | Новый gateway `GET_COUPONS_DIVIDENDS_MONTHLY_SUMMARY` / `bphGetCouponsDividendsMonthlySummary` (`RpcNamesForRequestCondition`) | `RpcNamesForRequestCondition.java` — нет `BPH_GET_COUPONS_DIVIDENDS_MONTHLY_SUMMARY`; класса gateway нет | NOT FOUND (TO BE) | Major |
| I-03 | §5.1 | BPH WebClient — `@Bean("BPH")` (`WebClientBphConfiguration` через `WebClientUtil`), base URL `app-config.bph.url` | `repositories/ИО/history-ops/src/main/java/.../configuration/WebClientBphConfiguration.java:19-27` — `@Bean(name="BPH")` использует `bphProperties.url()/deadline()` | CONFIRMED | Info |

### Конфигурация

| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|----|------------------|-------------|-----------------------|--------|-------------|
| CF-01 | §5.4 | `BphProperties` prefix `app-config.bph` (`deadline`, `url`, `pageSizeForLinkedEvents`, `pageSizeForTrades`) | `repositories/ИО/history-ops/src/main/java/.../configuration/properties/BphProperties.java:5-10` — `@ConfigurationProperties(prefix="app-config.bph")` | CONFIRMED | Info |
| CF-02 | §5.4 | test-default: `url=http://localhost:9843`, `deadline=50000`, `cacheRefreshMs=3600000`, `pageSizeForLinkedEvents=200` | `repositories/ИО/history-ops/src/test/resources/application-test.yml` (блок `app-config.bph`); `cacheRefreshMs` читается `@Scheduled(fixedRateString="${app-config.bph.cacheRefreshMs}")` в `BphDynamicConfigService.java` | CONFIRMED | Info |
| CF-03 | §5.4 (TO BE) | Отдельный `app-config.bph.monthlySummary.deadline` (1500–3000 мс) | Ключ в коде отсутствует; в `application-test.yml` нет `monthlySummary` | NOT FOUND (TO BE) | Major |

### Feature toggles

| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|----|------------------|-------------|-----------------------|--------|-------------|
| T-01 | §2 CN-04, §5.5 | `FeatureToggleName`: `ENABLE_BPH("enableServiceBPH")`, `ENABLE_BPH_LINKED_COMMISSIONS("enableBphLinkedCommissions")`, `ENABLE_BPH_LINKED_TRADING_OPS("enableBphTradingOperations")` | `repositories/ИО/history-ops/src/main/java/.../adapter/auth/FeatureToggleName.java:10,12,13` | CONFIRMED | Info |
| T-02 | §2 CN-04, §5.5 (TO BE) | `enableBphCouponsDividendsMonthlySummary` (новое значение enum `FeatureToggleName`) | `FeatureToggleName.java` — значение отсутствует | NOT FOUND (TO BE) | Major |

### Поведение и алгоритмы

| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|----|------------------|-------------|-----------------------|--------|-------------|
| B-01 | §5.4 | `RpcNamesForRequestCondition.BPH_GET_LINKED_EVENTS = "bphGetLinkedEvents"` | `repositories/ИО/history-ops/src/main/java/.../adapter/RpcNamesForRequestCondition.java:6` | CONFIRMED | Info |
| B-02 | §5.3.2 | Метрики: `history_ops_time` (перцентили 0.5/0.75/0.85/0.95/0.99), `history_ops_integration` (→`_total` counter и `_flow_duration_seconds` timer), `history_ops_absent_operation_types` | `repositories/ИО/history-ops/src/main/java/.../service/meter/service/MeterService.java` (`recordPercentile`/`addIntegrationMetric`/`countIntegration`/`countOperationTypes`); имена подтверждены `src/test/resources/.../prometheus_metrics/prometheus-metrics-*.txt` | CONFIRMED | Info |
| B-03 | §5.3.1 | Лог-фреймворк `RequestService`→`IntegrationLogService`→`ReactorLogger`; `ListRequestService.convert`→`logWarn("Failed to convert operations...")` + `parse_error`; `execute`→`response_size` | `.../adapter/ListRequestService.java:40,74-76`; классы `RequestService.java`, `logger/IntegrationLogService.java`, `logger/ReactorLogger.java` существуют | CONFIRMED | Info |
| B-04 | §5.3.1 | Системный журнал «The response was successfully sent» / «The response was failed» | `.../infrastructure/grpc/interceptors/AbstractHistoryOpsOperationForwardingServerCall.java:48,69` | CONFIRMED | Info |
| B-05 | §5.3.1 | Обрезка тела лога `app-config.integration-log.bodyMaxBytes`, строка «Oops.. content is too long» | `.../logger/IntegrationLogService.java:20,304`, `.../configuration/properties/IntegrationLogProperties.java:7` | CONFIRMED | Info |
| B-06 | §2 CN-04 | `ExecutionProcess.isBphLinkedCommissionsEnabled()`/`isBphLinkedTradingOpsEnabled()` | `repositories/ИО/history-ops/src/main/java/.../model/ExecutionProcess.java:100,104` | CONFIRMED | Info |

### Тесты и фикстуры

| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|----|------------------|-------------|-----------------------|--------|-------------|
| F-01 | § «Enum / status mapping» | Маппинг типов в `CommissionTest.java` (`app-config.operation-cache.default-value`): coupon/dividend_input/dividend_output/coupon_output → CA_CASH_MOVEMENT (INTEREST_PAYMENT_CREDIT/CASH_DIVIDEND_CREDIT/CASH_DIVIDEND_DEBIT/INTEREST_PAYMENT_DEBIT) | `repositories/ИО/history-ops/src/test/java/.../CommissionTest.java` (`@TestPropertySource` c `operation-cache.default-value`); дублируется в `application-test.yml` (`coupon`→bc 114/INTEREST_PAYMENT_CREDIT, `dividend_input`→111/CASH_DIVIDEND_CREDIT, `dividend_output`→112/CASH_DIVIDEND_DEBIT, `coupon_output`→null/INTEREST_PAYMENT_DEBIT) | CONFIRMED | Info |
| F-02 | §5.3.2 | Имена метрик в test-ресурсах `prometheus-metrics-*.txt` | `src/test/resources/.../prometheus_metrics/prometheus-metrics-*.txt` (напр. `history_ops_integration_flow_duration_seconds_count`, `history_ops_integration_total`, `history_ops_absent_operation_types_total`) | CONFIRMED | Info |
| F-03 | §2 CN-05, §1.3 | Существующие деталки `HISTORY_OPS_COUPON_DETAILS_SCREEN` и др.; типы секций `history.feed.title`/`history.feed.operationActive`/`history.feed.operation` | `repositories/ИО/history-ops-screen-api/src/test/resources/db/init-test-screens.sql:277,329,381,433`; фикстуры `src/test/resources/responses/.../feed/*.json` | CONFIRMED | Info |

## Рекомендуемые действия

1. **Нет обязательных правок (нет Critical/Major MISMATCH).** Все TO BE-заявления (§4.1.1 контракт ручки BPH, gateway `GET_COUPONS_DIVIDENDS_MONTHLY_SUMMARY`, поле `couponsDividendsMonthlySummary` в `history.yml`, секция `HISTORY_OPS_COUPONS_DIVIDENDS_MONTHLY_SUMMARY_SECTION`, `app-config.bph.monthlySummary.deadline`, флаг `enableBphCouponsDividendsMonthlySummary`) — ожидаемо NOT FOUND до реализации; реализуется командами BPH / history-ops / screen-api по спеке, повторный прогон аудита после реализации подтвердит CONFIRMED.
2. **Опционально (не блокер):** уточнить формулировку §4.2.3 про FK `operation.bc_id` — в актуальной тестовой схеме `create_schema.sql` `bc_id` ссылается на legacy-таблицу `bc`, а не `bph_bc`; production (`db-export/БД ИО.md`, changeset `20250813_SIHIST-3426_create_bph_bc_tables.sql`, отсутствующий в main-changelog репозитория) фиксирует `bc_id → bph_bc.id`. Спека корректно следует production-выгрузке, но стоит явно пометить, что main-changelog репозитория отстаёт от прода (сам факт уже частично покрыт GAP-DM-07). Правки — через `/check-feature` или `/resolve-code-alignment`, не в этом отчёте.
3. **После реализации TO BE-части** — обязательный повторный прогон `/check-feature-code` для перевода NOT FOUND → CONFIRMED.

## Пропущено

- Prod-значения конфигов (`app-config.bph.deadline`/`url`/`cacheRefreshMs` в prod) — в репозитории только `application-test.yml`; спека честно фиксирует их как `GAP-NFR-05`. Не проверялись (UNVERIFIABLE без app-config эксплуатации) — не отражены как находки, т.к. спека сама помечает их гэпом.
- NFR-метрики (p85/RPS/CCU/Web Vitals/SLO) — значения в спеке помечены `[GAP-NFR-*]`, в коде не проверяемы (target-величины, не реализация).
- Поведение нового gateway/секции (алгоритм §4.2.2) — целиком TO BE, кода нет; проверка сводится к NOT FOUND (зафиксировано в категориях выше).

---
report_type: code-alignment
slug: bph-moex-tax
source_document: Feature-writing/bph-moex-tax/bph-moex-tax.md
generated_at: 2026-10-05
alignment_iteration: 2
scope: repositories/ only
language: ru
verdict: PASS WITH GAPS
---

# Отчёт о соответствии коду: bph-moex-tax

**Документ:** `Feature-writing/bph-moex-tax/bph-moex-tax.md`
**Отчёт:** `Feature-writing/bph-moex-tax/bph-moex-tax-code-alignment.md`
**Область проверки:** только код в `repositories/` (источник истины — `repositories/ИО/history-ops`)

## Сводка
- CONFIRMED: 40 · MISMATCH: 0 · PARTIAL: 0 · NOT FOUND: 1 · UNVERIFIABLE: 1
- **Вердикт:** PASS WITH GAPS

## Приоритетные находки

Пользователь задал фокус на повторной проверке трёх закрытых MISMATCH из итерации 1
(CFG-03, CFG-05/C-08, C-07) и перепроверке остальных TO BE-claims.

**Все три закрытых MISMATCH теперь CONFIRMED:**
- CFG-03 — ключ кэш-обновления `app-config.operation-cache.updateDelayMs` подтверждён
  (`OperationCacheLoaderProperties.java`, `OperationCacheLoader.java:40`); стейл-ключ
  `bd_response_cron_time` полностью убран из SPEC (grep: 0 совпадений).
- CFG-05 / C-08 — источник `pageSize` = `app-config-dynamic.bph-dynamic.maxRecordsFromBph`
  подтверждён (`BphGateway.java:117`, `BphDynamicProperties.java:15-17`); SPEC обновлён,
  стейл `history_ops.reporting.maxRecords` убран.
- C-07 — `formationDate` обязательное поле (`BphOperationConverter.validateSimpleAttributes()`
  → `checkNotNull(..., "formationDate")`); SPEC помечает поле Nullable «Нет».

Оставшиеся открытые пункты — только ожидаемые для TO BE (строки `MOEX_TAX` ещё не пролиты)
и рантайм-факт из `db-export/` (не верифицируется в коде).

## Находки по категориям

### Контракты
| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|---|---|---|---|---|---|
| C-01 | §4.1.1 | Endpoint `POST /api/v1/incoming-gateway/operations-with-details` | `BphClient.java:15` — `OPERATIONS_URL = "/api/v1/incoming-gateway/operations-with-details"`; `bph.yml:216` — path | CONFIRMED | Info |
| C-02 | §4.1.1 | Headers `rqUID` + `systemName`, значение `history_ops` | `BphClient.java:19-21,31` — `SYSTEM_NAME="systemName"`, `REQUEST_ID="rqUID"`, `HISTORY_OPS="history_ops"`; `.header(SYSTEM_NAME, HISTORY_OPS)` | CONFIRMED | Info |
| C-03 | §4.1.1 (прим.) | `si2-ops` — только `example` в OpenAPI, код шлёт `history_ops` | `BphClient.java:21,31` — фактически `history_ops`; в `bph.yml` у ряда endpoint `example: si2-ops`, у `operations-with-details` без example | CONFIRMED | Info |
| C-04 | §4.1.1 | `RequestParamsData` + `subtypesAndStatuses[]` (`type`/`subtype`/`statuses` required; `additionalTypes` опц., `maxLength 225`, `maxItems 1000`) | `bph.yml:1292-1326` — `subtypesAndStatuses` `maxItems: 1000`; `type`/`subtype`/`statuses` `maxLength: 225`; `required` содержит `subtype`; `additionalTypes` опц. | CONFIRMED | Info |
| C-05 | §4.1.1 | `OperationData` содержит оба имени подтипа `subType` и `subtype` | `bph.yml:1093-1095` — свойства `subType` и `subtype` оба присутствуют | CONFIRMED | Info |
| C-06 | §4.1.1 | `ResponseStatusData{code,message}`, `DetailsData{lead,details}`, `ErrorData{timestamp,status(400/500),error}` | `bph.yml` — `ResponseStatusData`, `DetailsData`, `ErrorData`; enum `status: [400,500]`, enum `error: [Bad Request, Internal Server Error]` | CONFIRMED | Info |
| C-07 | §4.1.1 (таблица OperationData) | `formationDate` — Nullable «Нет» (обязательное) | `BphOperationConverter.java:validateSimpleAttributes()` — `Preconditions.checkNotNull(operationData.getFormationDate(), "formationDate")` | CONFIRMED | Info |
| C-08 | §4.1.1 (таблица RequestParamsData) | `pageSize` заполняется из `app-config-dynamic.bph-dynamic.maxRecordsFromBph` | `BphGateway.java:117` — `request.setPageSize(bphDynamicProperties.getMaxRecordsFromBph())`; `BphDynamicProperties.java:15-17` | CONFIRMED | Info |

### БД и миграции
Источник DDL/DML: `repositories/ИО/history-ops/src/test/resources/db/init/create_schema.sql` (Liquibase-чанжсеты в комментариях).

| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|---|---|---|---|---|---|
| DB-01 | §4.2.3 | Таблицы `type`, `operation_type`, `bph`, `operation`, `info`, `status`, `general_status`, `status_to_operation` существуют | `create_schema.sql:4,10,22,31,37,45,54,61` — `CREATE TABLE history_ops.*` | CONFIRMED | Info |
| DB-02 | §2 CN-05, §4.2.3 | `type` id 7 = `TAXES` | `create_schema.sql:628` — `update history_ops.type set name = 'TAXES' where id = 7;` | CONFIRMED | Info |
| DB-03 | §2 CN-05, §4.2.3 | `operation_type` id 2 = `tax`, id 20 = `tax_input` | `create_schema.sql:170` — `(2, 'tax')`; `:589` — `values (20, 'tax_input')` | CONFIRMED | Info |
| DB-04 | §1.2/§1.3, §4.2.3 | `bph` id 19 = `TAX_RETAIN` (type_id 7), id 20 = `TAX_REFUND_BROK_ACCOUNT` (type_id 7) | `create_schema.sql:593-596` — `values (19, 'TAX_RETAIN', 7, true)`, `(20, 'TAX_REFUND_BROK_ACCOUNT', 7, true)` | CONFIRMED | Info |
| DB-05 | §2 CN-07, §4.2.3 | `operation` id 2 = `tax` (bc_id 110), id 23 = `tax_input` (bc_id NULL, bph_id 20) | `create_schema.sql` — `(2, 2, 110, ...)`, `(23, 20, null, 20, ...)` (см. ит. 1 DB-05) | CONFIRMED | Info |
| DB-06 | §4.2.3, §4.2.4 | `info` для operation 2 (4 строки с non-null `additional_type`) и operation 23 (`NULL`) | `create_schema.sql` — `info`-строки `OUT_MONEY`/`INCENTIVE_PAYMENT`/`OUT_SECURITIES`/`TAX_PERIOD_END` и `(49, 23, NULL, ...)` | CONFIRMED | Info |
| DB-07 | §2, §4.2.3, §4.2.4 | `status` id 19 = `COMPLETE` → `general_status_id` 1 (`executed`) | `create_schema.sql:608` — `values (19, 'COMPLETE', 1)` | CONFIRMED | Info |
| DB-08 | §2 CN-03, §4.2.3 | `status_to_operation` operation 2 ↔ status 19, operation 23 ↔ status 19 | `create_schema.sql:611-613` — `insert into ... status_to_operation ... (28, 2, 19), (29, 23, 19)` | CONFIRMED | Info |
| DB-09 | §4.2.3/§4.2.4 (TO BE) | Новые строки `bph`/`operation`/`info`/`status_to_operation` для `MOEX_TAX` | В `repositories/` `MOEX_TAX` отсутствует (grep: 0 совпадений) — строки ещё не пролиты | NOT FOUND | Major (ожидаемо для TO BE) |
| DB-10 | §4.2.3 | «max id»: bph 24, operation 26, info 77, status_to_operation 56 | Рантайм-значения из `db-export/БД ИО.md`; тестовая схема `create_schema.sql` содержит меньше строк | UNVERIFIABLE | Info |

### Интеграции
| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|---|---|---|---|---|---|
| I-01 | §4.1.1, §5.3.2 | `exSystem=BPH`, `eventType=GET_OPERATIONS_WITH_DETAILS` | `BphGateway.java` — `exSystem()` → `"BPH"`, `eventType()` → `"GET_OPERATIONS_WITH_DETAILS"` | CONFIRMED | Info |
| I-02 | §4.1.1/§5 | BPH-шлюз включается feature toggle | `BphGateway.java:enabled()` — `FeatureToggleName.ENABLE_BPH` | CONFIRMED | Info |
| I-03 | §2 CN-08, §4.2.2 BR-05 | `additionalTypes[]` — только non-null `info.additional_type`, не передаётся при пустоте | `BphBcFilterService.java:116` — `.filter(Objects::nonNull)` | CONFIRMED | Info |
| I-04 | §2 CN-07, §4.2.2 BR-07 | При `bc_id=NULL` — ранний `return true` (watershed/additionalType не блокируют) | `BphBcFilterService.java:190,194,264` — `return true` (нет BC-контекста → true) | CONFIRMED | Info |
| I-05 | §2 CN-03, §4.2.2 BR-07/BR-10 | Статус-членство `statusMap.containsKey(status)` | `BphBcFilterService.java:85,353` — `statusMap.containsKey(status)` | CONFIRMED | Info |
| I-06 | §4.1.1 | HTTP/ошибка вызова → `dataCompleteFalse` + partial failure | `AbstractOperationGateway.getOperationsSafe()` — `.onErrorResume(...)` → `meterService.countIntegrationDataCompleteFalse(...)` | CONFIRMED | Info |

### Конфигурация
| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|---|---|---|---|---|---|
| CFG-01 | §1.2/§1.3, §4.1.1 | Timeout задаётся `WebClientBphConfiguration` | `WebClientBphConfiguration.java` — `webClientUtil.webClient(builder, bphProperties.url(), bphProperties.deadline())`; `BphProperties` prefix `app-config.bph` | CONFIRMED | Info |
| CFG-02 | §2 CN-02 | Префикс `app-config.operation-cache` существует | `OperationCacheLoaderProperties.java` — `@ConfigurationProperties(prefix = "app-config.operation-cache")` | CONFIRMED | Info |
| CFG-03 | §2 CN-02, §5.3.1, GAP-CONS-08/DM-08/MIG-08 | Ключ кэш-обновления = `app-config.operation-cache.updateDelayMs` (стейл `bd_response_cron_time` убран, «default 60 мин» убрано) | `OperationCacheLoaderProperties.java` — record с полем `long updateDelayMs`; `OperationCacheLoader.java:40` — `loadDataTask(properties.updateDelayMs())`; grep `bd_response_cron_time` в SPEC — 0 совпадений | CONFIRMED | Info |
| CFG-04 | §5.3.1 | Лимит тела лога `IntegrationLogProperties.bodyMaxBytes` | `IntegrationLogProperties.java` — `@ConfigurationProperties(prefix = "app-config.integration-log")`, поле `bodyMaxBytes` | CONFIRMED | Info |
| CFG-05 | §4.1.1 | `pageSize` из `app-config-dynamic.bph-dynamic.maxRecordsFromBph` | `BphDynamicProperties.java:15-17` — prefix `app-config-dynamic.bph-dynamic`, поле `maxRecordsFromBph`; `BphGateway.java:117`; `application-test.yml:66-67` — `maxRecordsFromBph: 1000` | CONFIRMED | Info |

### Feature toggles
| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|---|---|---|---|---|---|
| FT-01 | §4.1.1/§5 | BPH включается toggle `ENABLE_BPH` | `BphGateway.java:enabled()` → `FeatureToggleName.ENABLE_BPH` | CONFIRMED | Info |

### Поведение и алгоритмы
| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|---|---|---|---|---|---|
| B-01 | §4.2.4 | `id = bph_{operation_type}_{externalSystemId}` | `BphCommonClientConverter.java:getId()` — `"bph_%s_%s".formatted(...)` | CONFIRMED | Info |
| B-02 | §2 CN-09, §4.2.4 | Матчинг `additional_type == additionalType`, NULL ↔ `""` | `BphCommonClientConverter.java:isCorrectAdditionalType()` — `orElse("")` equals `orElse("")` | CONFIRMED | Info |
| B-03 | §2 CN-09, §4.2.2 BR-06 | Для `TAXES` при пустом comment — fallback `lead.accComment` | `BphCommonClientConverter.java:convert()` — `if (TAXES.equals(...) && commentFromTable.isBlank()) ... accComment()` | CONFIRMED | Info |
| B-04 | §4.2.4 | `totalSum = abs(totalPrice)` | `BphCommonClientConverter.java:convert()` — `map(BigDecimal::abs)` | CONFIRMED | Info |
| B-05 | §4.2.4 | `operationDisplayName` ← `info.displayed_name` | `BphCommonClientConverter.java:enrichOperationDisplayName()` — присваивание `displayedName` | CONFIRMED | Info |
| B-06 | §4.1.1 | Читаются оба имени `subtype` и `subType` | `BphOperationConverter.java:getSubType()` — `if (subtype != null) ... else if (subType != null) ...` | CONFIRMED | Info |
| B-07 | §5.3.2 | Метрики `history_ops_time` (перцентили 0.5/0.75/0.85/0.95/0.99), `history_ops_integration_flow_duration_seconds`, `history_ops_integration_total`, `history_ops_general_total` | `MeterService.java:16` — `METRIC_PERCENTILES = {0.5,0.75,0.85,0.95,0.99}`; `:22` — `history_ops_time`; `:33` — `history_ops_integration` (timed → `..._flow_duration_seconds`); `:57` — counter `history_ops_integration` (`_total` — Prometheus-конвенция для counter); `:74` — `history_ops_general`; тестовые фикстуры `prometheus_metrics/*.txt` подтверждают экспортные имена `history_ops_integration_total`, `history_ops_general_total`, `history_ops_integration_flow_duration_seconds_*` | CONFIRMED | Info |
| B-08 | §5.3.1/§5.3.2 | Метрика/лог `unexpected_additional_type_for_common_operation` | `BphBcFilterService.java:246` — `meterTemplate = "unexpected_additional_type_for_common_operation"` | CONFIRMED | Info |
| B-09 | §5.3.2 | `parse_error` metric | `ListRequestService.java` — `countIntegrationError(..., "parse_error", ...)` | CONFIRMED | Info |
| B-10 | §5.3.2 | `dataCompleteFalse` metric | `MeterService.java:48-49` — `countIntegrationDataCompleteFalse` → `"dataCompleteFalse"` | CONFIRMED | Info |
| B-11 | §4.1.1 | `BphConverter.SUPPORTED_DETAILS_KEY` содержит `comment`, `accComment`, `errorCode`, `statusErrorCode` | `BphConverter.java` — `SUPPORTED_DETAILS_KEY` | CONFIRMED | Info |
| B-12 | §4.2.4 | `COMPLETE` → `executed` (`getGeneralStatusMap`) | `BphConverter.java:getGeneralStatusMap()` — `statusesMap.put(COMPLETED, EXECUTED)` + из кэша | CONFIRMED | Info |
| B-13 | §1.2/§1.3 | gRPC `SEND_OPERATIONS` (`HistoryOpsGrpcService`) | `HistoryOpsGrpcService.java` — extends `HistoryOperationDetailsServiceGrpc...`; фикстуры — `SEND_OPERATIONS{ex_system="MOBILE"}` | CONFIRMED | Info |
| B-14 | §2 CN-05, §4.2.2 | «Java-код не меняется» (data-only) | grep `MOEX_TAX` по `repositories/` — 0 совпадений; нет классов/методов под `MOEX_TAX` | CONFIRMED | Info |

### Тесты и фикстуры
| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|---|---|---|---|---|---|
| T-01 | §5.3.2 | Метрики для BPH подтверждены тестовыми выгрузками `prometheus_metrics` | `src/test/resources/com/sberbank/si20/history/ops/prometheus_metrics/*.txt` — `history_ops_integration_total{...ex_system="BPH",event_type="GET_OPERATIONS_WITH_DETAILS"...}` | CONFIRMED | Info |

## Рекомендуемые действия
1. **DB-09 (NOT FOUND, ожидаемо для TO BE):** строки `MOEX_TAX` ещё не пролиты в `repositories/` — фича корректно описана как data-only TO BE; закрывается фактом пролива, а не правкой SPEC. Pre-check «0 строк» и сверка написания `MOEX_TAX` с контрактом BPH уже зафиксированы в SPEC (§4.3) — перед проливом подтвердить написание у команды BPH.
2. **DB-10 (UNVERIFIABLE):** «max id»-значения (`bph` 24, `operation` 26, `info` 77, `status_to_operation` 56) — рантайм-факт из `db-export/БД ИО.md`, в коде не верифицируется. Источник в SPEC уже помечен; дополнительных действий не требуется.
3. Все три ранее закрытых MISMATCH (CFG-03, CFG-05/C-08, C-07) — CONFIRMED; правок SPEC не требуется.

## Пропущено
- Значения prod-конфигурации (`updateDelayMs`, deadline BPH, `bodyMaxBytes`) — prod ConfigMap/Helm вне `repositories/`; сверялись только код и тестовые ресурсы.
- Рантайм-поведение Ignite-кэша (дедупликация `bph_{type}_{id}` постранично) — BR-11 проверен на уровне формата `getId`; сам Ignite-кэш в scope не детализировался.

## Журнал резолва (2026-10-05, итерация 2/3)

Повторный аудит после `/resolve-code-alignment` (итерация 1). Все три закрытых MISMATCH перепроверены против кода и переведены в CONFIRMED:

| ID | Статус (ит. 1 → ит. 2) | Подтверждение в коде |
|----|------------------------|----------------------|
| CFG-03 | MISMATCH (Major) → CONFIRMED | `OperationCacheLoaderProperties.java` (`updateDelayMs`), `OperationCacheLoader.java:40`; стейл `bd_response_cron_time` убран из SPEC |
| CFG-05 / C-08 | MISMATCH (Minor) → CONFIRMED | `BphDynamicProperties.java:15-17`, `BphGateway.java:117`; SPEC использует `app-config-dynamic.bph-dynamic.maxRecordsFromBph` |
| C-07 | MISMATCH (Minor) → CONFIRMED | `BphOperationConverter.java:validateSimpleAttributes()` → `checkNotNull(getFormationDate(), "formationDate")`; SPEC помечает `formationDate` Nullable «Нет» |

### Оставшиеся открытые пункты (ожидаемо / вне scope кода)

- **DB-09 (NOT FOUND, TO BE):** строки `MOEX_TAX` ещё не пролиты — ожидаемо до реализации; не closable ответом в чате.
- **DB-10 (UNVERIFIABLE):** «max id»-значения — рантайм-факт из `db-export/БД ИО.md`, в `repositories/` не верифицируется.

---
report_type: code-alignment
slug: bph-portfolio-size-tax
source_document: Feature-writing/bph-portfolio-size-tax/bph-portfolio-size-tax.md
generated_at: 2026-10-06
alignment_iteration: 1
scope: repositories/ only
language: ru
verdict: PASS WITH GAPS
---

# Отчёт о соответствии коду: bph-portfolio-size-tax

**Документ:** `Feature-writing/bph-portfolio-size-tax/bph-portfolio-size-tax.md`
**Отчёт:** `Feature-writing/bph-portfolio-size-tax/bph-portfolio-size-tax-code-alignment.md`
**Область проверки:** только код в `repositories/` (вспомогательно `db-export/`)

## Сводка
- CONFIRMED: 32 · MISMATCH: 0 · PARTIAL: 0 · NOT FOUND: 4 · UNVERIFIABLE: 0
- **Вердикт:** PASS WITH GAPS

Расхождений (MISMATCH/PARTIAL) с кодом не выявлено. Все заявленные механизмы
(контракт, таблицы маппинга, data-driven конвертация/фильтр, конфиги, метрики)
подтверждены фактическим кодом `history-ops` и данными `db-export`. Единственные
неподтверждённые элементы — **TO BE-данные** нового подтипа (`PORTFOLIO_SIZE_TAX`,
новые строки `bph`/`operation`/`info`/`status_to_operation`, новый `comment`),
которых в коде и выгрузках ожидаемо нет (0 совпадений) — фича data-only, ещё не
пролита.

## Приоритетные находки

Указания пользователя: контракт `GET_OPERATIONS_WITH_DETAILS`, таблицы маппинга БД
HO, data-driven механизм (`BphCommonClientConverter`, `BphBcFilterService`,
`BphOperationConverter`, `isActualBphOperation`, `statusMap.containsKey`), конфиги
(`app-config.bph.*`, `app-config.operation-cache.*`), метрики
(`unexpected_additional_type_for_common_operation`, `history_ops_integration_total`),
feature toggles. Все проверены первыми и глубже — результаты в таблицах ниже.
Критических расхождений нет.

## Находки по категориям

### Контракты

| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|---|---|---|---|---|---|
| K-01 | §4.1.1 | Endpoint `POST /api/v1/incoming-gateway/operations-with-details` | `src/main/swagger/bph/bph.yml:216` (`/api/v1/incoming-gateway/operations-with-details:` → `post:`); вызов `adapter/bph/BphClient.java:17` (`OPERATIONS_URL`) | CONFIRMED | Info |
| K-02 | §4.1.1 | Headers `rqUID` (обязат.) + `systemName=history_ops` | `bph.yml:222-234` (параметры `rqUID`/`systemName`, `required: true`); `BphClient.java:19-21` (`SYSTEM_NAME="systemName"`, `REQUEST_ID="rqUID"`, `HISTORY_OPS="history_ops"`), `.header(SYSTEM_NAME, HISTORY_OPS)` | CONFIRMED | Info |
| K-03 | §4.1.1 | Body `RequestParamsData` с `subtypesAndStatuses[]` (`type`/`subtype`/`statuses` required; `additionalTypes` опц.; maxItems 1000, maxLength 225) | `bph.yml:1252-1326` — `subtypesAndStatuses` (`maxItems: 1000`), поля `type`/`subtype`/`additionalTypes`/`statuses` (`maxLength: 225`), `required: [type, subtype, statuses]` | CONFIRMED | Info |
| K-04 | §4.1.1 | Ответ 200 `{status: ResponseStatusData, data: [DetailsData]}`; 400/500 → `ErrorData` | `bph.yml:245-265` (`status` → `ResponseStatusData`, `data` → array of `DetailsData`, `400`/`500` → `ErrorData`) | CONFIRMED | Info |
| K-05 | §4.1.1 | `OperationData` имеет оба поля `subType` и `subtype` | `bph.yml:1090-1095` (`subType: type: string`, `subtype: type: string`) | CONFIRMED | Info |
| K-06 | §4.1.1 | `ResponseStatusData`: `code` (integer), `message` (string) | `bph.yml:1436-1441` | CONFIRMED | Info |
| K-07 | §4.1.1 | `ErrorData`: `timestamp`, `status` (enum `400`/`500`), `error` (enum `Bad Request`/`Internal Server Error`), `path` | `bph.yml:1443-1473` (`required: timestamp/status/error/path`, `enum` совпадает) | CONFIRMED | Info |
| K-08 | §4.1.1 | `dateForFilter` enum `FORMATION_DATE \| EVENT_DATE` | `bph.yml:1420-1425` (`FilterDateEnum`, `enum: [EVENT_DATE, FORMATION_DATE]`) | CONFIRMED | Info |
| K-09 | §4.1.1 | `BphConverter.SUPPORTED_DETAILS_KEY` включает `comment`, `accComment`, `errorCode`, `statusErrorCode` | `adapter/bph/BphConverter.java:199-229` (множество ключей, в т.ч. `"comment"`, `"accComment"`); `errorCode`/`statusErrorCode` читаются в `BphOperationConverter.resolveErrorCode()` (строки 238-247) | CONFIRMED | Info |

### БД и миграции

| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|---|---|---|---|---|---|
| DB-01 | §4.2.3 | Таблицы `type`, `operation_type`, `bph`, `bph_bc`, `operation`, `info`, `status`, `status_to_operation`, `general_status` существуют | `liquibase/changesets/20241029_SIHIST-2774_*_create_*.xml` (1..9: bc, bph, info, status_to_operation, status, type, operation, general_status, operation_type); `20250813_SIHIST-3426_create_bph_bc_tables.sql` | CONFIRMED | Info |
| DB-02 | §2, §4.2.3 | `type` id=7 = `TAXES` | `db-export/БД ИО.md:319,1525,2791` (`(7, 'TAXES')`) | CONFIRMED | Info |
| DB-03 | §1.1, §4.2.3 | `operation_type` id=2 = `tax`, id=20 = `tax_input` | `db-export/БД ИО.md:326,344,2816` (`| 2 | tax |`, `(20, 'tax_input')`) | CONFIRMED | Info |
| DB-04 | §1.2, §4.2.3 | `bph` id=19 = `TAX_RETAIN` (type_id 7, active), id=20 = `TAX_REFUND_BROK_ACCOUNT` (type_id 7, active) | `db-export/БД ИО.md:425,428,2896-2897` (`(19,'TAX_RETAIN',7,true)`, `(20,'TAX_REFUND_BROK_ACCOUNT',7,true)`) | CONFIRMED | Info |
| DB-05 | §4.2.3 | `operation` id=2 = `tax` (bc_id 110 `TAX_WITHHOLDING`, bph_id 19), id=23 = `tax_input` (bc_id NULL, bph_id 20) | `db-export/БД ИО.md:1692,1713`; `bph_bc` id=110 = `TAX_WITHHOLDING` (`:1675,2911`) | CONFIRMED | Info |
| DB-06 | §4.2.3 | `info`: operation 2 → 4 строки `OUT_MONEY`/`OUT_SECURITIES`/`TAX_PERIOD_END`/`INCENTIVE_PAYMENT`; operation 23 → 1 строка `additional_type=NULL`, `comment='Возврат излишне удержанного налога'` | `LikeBCBphIntegrationTest.java:29` (default-value JSON: `TAX_RETAIN` → 4 `info[].additional_type`; `TAX_REFUND_BROK_ACCOUNT` → `info[{"comment":"Возвратизлишнеудержанногоналога"}]` без `additional_type`); `db-export/БД ИО.md:3985-3994` | CONFIRMED | Info |
| DB-07 | §2, §4.2.3 | `status` id=19 = `COMPLETE` → `general_status_id=1` (`executed`) | `db-export/БД ИО.md:375,1594,2845` (`(19, 1, 'COMPLETE')`); `general_status` id=1 = `executed` (`:347`) | CONFIRMED | Info |
| DB-08 | §4.2.3 | `status_to_operation`: operation 2 ↔ status 19; operation 23 ↔ status 19 | `db-export/БД ИО.md:1827-1828` (`| 28 | 2 … | 19 (COMPLETE) |`, `| 29 | 23 … | 19 (COMPLETE) |`) | CONFIRMED | Info |
| DB-09 | CN-10, §4.2.3 | Прецедент data-driven пролива — Liquibase changeset `20250606_SIHIST-3321_added_tax_data.sql` | В `repositories/` файл отсутствует (в `liquibase/changesets/` только до `SIHIST-3426`); запись changeset есть в `db-export/БД ИО.md:778,2046` (databasechangelog, EXECUTED). Спека корректно цитирует db-export, а не код | NOT FOUND | Minor |

### Поведение и алгоритмы

| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|---|---|---|---|---|---|
| B-01 | §4.2.2, §4.2.4 | `BphCommonClientConverter`: константа `TAXES`, методы `convert()`, `getId()`, `enrichComment()`, `enrichOperationDisplayName()`, `getAdditionalInfoFromCache()`, `isCorrectAdditionalType()`, `getOperationFromCache()` (фильтр `bphActive`) | `service/conversion/BphCommonClientConverter.java` (`private static final String TAXES = "TAXES"`; `getOperationFromCache(...).filter(Operation::bphActive)`) | CONFIRMED | Info |
| B-02 | BR-05, CN-09, §4.2.4 | `comment` подбирается из `info[]` по `additional_type == lead.additionalType` (NULL↔`""`); для `TAXES` при пустом `comment` — fallback `accComment` из `details[]` | `BphCommonClientConverter.java` — `isCorrectAdditionalType()` (`Optional.ofNullable(...).orElse("")` + `equals`); fallback `if (TAXES.equals(bphType) && commentFromTable.isBlank()) lead.setComment(accComment)`. `accComment` приходит из `details[]` → `BphOperationConverter.java` (`details.get("accComment")`) | CONFIRMED | Info |
| B-03 | §4.2.4 | `id` = `bph_{operation_type}_{externalSystemId}` (для `TAXES` ветка `CASH_FLOW`/`NON_TRADE_ORDERS` не применяется) | `BphCommonClientConverter.java` — `getId()`: `return "bph_%s_%s".formatted(operationType.getValue(), externalSystemId)` (ветка default) | CONFIRMED | Info |
| B-04 | §4.2.4 | `totalSum` = `abs(totalPrice)`; `instrumentCount` = `quantity.longValue()` | `BphCommonClientConverter.java` — `Optional.ofNullable(operation.totalPrice()).map(BigDecimal::abs)`; `Optional.ofNullable(quantity).map(BigDecimal::longValue)` | CONFIRMED | Info |
| B-05 | §4.2.4 | `operationDisplayName` = прямое присваивание `info.displayed_name`, без fallback на `operation.name` | `BphCommonClientConverter.java` — `enrichOperationDisplayName()` → `lead.setOperationDisplayName(displayedName)` (без fallback) | CONFIRMED | Info |
| B-06 | CN-08, BR-06 | `additionalTypes[]` в запросе формируется только из non-null `info.additional_type` (`filter(Objects::nonNull)`) | `service/filter/BphBcFilterService.java` — `buildBphRequestEntityByBphParams()`: `.map(AdditionalInfo::getAdditionalType).filter(Objects::nonNull).toList()`; `if (!additionalTypes.isEmpty()) setAdditionalTypes(...)` | CONFIRMED | Info |
| B-07 | CN-07, BR-07 | При `bc_id=NULL` ранний `return true` в `isActualBphOperation()` — watershed/additionalType не блокируют | `BphBcFilterService.java` — `isActualBphOperation()`: `hasBcContext = operationInternal.bcType() != null && operationInternal.bcSubtype() != null`; `if (!hasBphContext || !hasBcContext) return true;` | CONFIRMED | Info |
| B-08 | CN-03, BR-10 | Статус-членство — жёсткий фильтр `statusMap.containsKey(status)` | `BphBcFilterService.java` — `isCommonOperationByBphContext()`: `statusMap = cacheOperation.getStatusAndGeneralStatus(); ... statusMap.containsKey(status)` | CONFIRMED | Info |
| B-09 | §5.3.1, §5.3.2 | INFO-лог `"Unexpected additional type for common BPH operation id=%s type=%s subType=%s additionalType=%s"` + метрика `unexpected_additional_type_for_common_operation` (`countGeneralError`); при `bc_id=NULL` не срабатывают | `BphBcFilterService.java:243-247` (`log.info(logTemplate.formatted(...))`; `meterService.countGeneralError(meterTemplate, 1)`); срабатывает только после раннего `return true` | CONFIRMED | Info |
| B-10 | §4.2.2 | `BphOperationConverter`: `validateSimpleAttributes()` требует `type`, `subType`, `formationDate`, `eventDate`, `externalSystemId`, `status`, `agreement`; `getSubType()` читает `subtype` затем `subType` | `adapter/bph/BphOperationConverter.java` — `validateSimpleAttributes()` (`Preconditions.checkNotNull(...)`); `getSubType()` (`subtype` → else `subType`) | CONFIRMED | Info |
| B-11 | §4.1.1 | HO не ветвится по `status.code`: из 200-ответа извлекается `data`, элементы конвертируются по отдельности | `BphOperationConverter.convert()` читает `operationWithDetails.getLead()`/`getDetails()` без обращения к `status.code`; `BphClient.getOperations()` → `bodyToMono(...Post200Response)` | CONFIRMED | Info |

### Конфигурация

| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|---|---|---|---|---|---|
| C-01 | §5.4, CN-15 | `app-config.bph.deadline`, `app-config.bph.url`, `app-config.bph.page-size-for-linked-events`, `app-config.bph.page-size-for-trades` | `configuration/properties/BphProperties.java` (`@ConfigurationProperties(prefix = "app-config.bph")`: `deadline`, `url`, `pageSizeForLinkedEvents`, `pageSizeForTrades`) | CONFIRMED | Info |
| C-02 | CN-02, §5.4 | `app-config.operation-cache.update-delay-ms`, `.default-value`, `.including-name-types` | `configuration/properties/OperationCacheLoaderProperties.java` (`prefix = "app-config.operation-cache"`: `updateDelayMs`, `defaultValue`, `includingNameTypes`) | CONFIRMED | Info |
| C-03 | CN-15, §5.4 | `app-config-dynamic.bph-dynamic.max-records-from-bph`, `.linked-commission-start-date` (`@RefreshScope`) | `configuration/properties/BphDynamicProperties.java` (`prefix = "app-config-dynamic.bph-dynamic"`: `maxRecordsFromBph`, `linkedCommissionStartDate`); `BphGateway.java:117` (`request.setPageSize(bphDynamicProperties.getMaxRecordsFromBph())`) | CONFIRMED | Info |
| C-04 | §4.1.1 | Таймауты задаются `WebClientBphConfiguration` (WebClient HO) | `configuration/WebClientBphConfiguration.java` (существует; `@Qualifier("BPH")` WebClient в `BphClient`) | CONFIRMED | Info |
| C-05 | §5.4 | Кэш перезагружается по `update-delay-ms` (`OperationCacheLoader.loadDataTask`), данные из `OperationDAO.findAll()` | `cache/OperationCacheLoader.java:40` (`loadDataTask(properties.updateDelayMs())`); `dao/OperationDAO.java:37-39` (`findAll()` → `db/find_all_operations_v2.sql`) | CONFIRMED | Info |

### Feature toggles

| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|---|---|---|---|---|---|
| T-01 | §5.5, CN-17 | Отдельный runtime-тогл для нового подтипа не вводится; активация data-driven через `bph.is_active` (`bphActive`) + перезагрузка кэша | `BphCommonClientConverter.getOperationFromCache().filter(Operation::bphActive)`; `BphBcFilterService` (`operation.bphActive()`). Нового toggle-имени под фичу в `FeatureToggleName` нет | CONFIRMED | Info |
| T-02 | §5.5 | (не заявлено) Существующий тогл `ENABLE_BPH` гейтит всю интеграцию BPH | `adapter/auth/FeatureToggleName.java:10` (`ENABLE_BPH("enableServiceBPH")`); `BphGateway.java:56` (`executionProcess.getFeatureToggles().get(FeatureToggleName.ENABLE_BPH)`). Не противоречит спеку (спека говорит «новый тогл не вводится», что верно) — стоит упомянуть для полноты | CONFIRMED | Info |

### Метрики

| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|---|---|---|---|---|---|
| M-01 | §5.3.2 | `history_ops_integration_total` (Counter, labels `ex_system`/`event_type`/`comment`/`status`) | `service/meter/service/MeterService.java:52-66` (`meterRegistry.counter("history_ops_integration", ...)`); test fixtures `prometheus_metrics/*.txt` (`history_ops_integration_total{...}`) | CONFIRMED | Info |
| M-02 | §5.3.2 | `history_ops_integration_flow_duration_seconds` (Timer) | `MeterService.java:32-38` (`addIntegrationMetric` → `input.name("history_ops_integration").tap(Micrometer.metrics(...))`); fixtures (`history_ops_integration_flow_duration_seconds_count{...}`) | CONFIRMED | Info |
| M-03 | §5.3.2 | `history_ops_time` (Timer, перцентили 0.5/0.75/0.85/0.95/0.99) | `MeterService.java:20-30` (`Timer.builder("history_ops_time").publishPercentiles(METRIC_PERCENTILES)`), `METRIC_PERCENTILES={0.5,0.75,0.85,0.95,0.99}`; dashboards `history_ops_time_seconds_bucket` | CONFIRMED | Info |
| M-04 | §5.3.2 | `history_ops_general_total{comment="unexpected_additional_type_for_common_operation", status="error"}` | `MeterService.java:69-76` (`countGeneralError` → `meterRegistry.counter("history_ops_general", "status","error","comment",comment)`); вызов `BphBcFilterService.java:247` (`countGeneralError("unexpected_additional_type_for_common_operation", 1)`) | CONFIRMED | Info |
| M-05 | §5.3.2 | `history_ops_integration_total{comment="parse_error"}` и `{comment="dataCompleteFalse"}` | `adapter/ListRequestService.java:76,98` (`countIntegrationError(..., "parse_error", ...)`); `MeterService.java:48-50` (`countIntegrationDataCompleteFalse` → `"dataCompleteFalse"`); вызов `AbstractOperationGateway.java:100` | CONFIRMED | Info |

### TO BE (data-only, ожидаемо отсутствует до пролива)

| ID | Раздел документа | Утверждение | Доказательство | Статус | Критичность |
|---|---|---|---|---|---|
| TB-01 | §1.1, §4.2.3 | Новый BPH-подтип `PORTFOLIO_SIZE_TAX` (семейство `TAXES`) | 0 совпадений в `repositories/` и `db-export/` (grep по `PORTFOLIO_SIZE_TAX`, `MOEX_TAX`). Ожидаемо: подтип появится только после INSERT | NOT FOUND | Major (ожидаемо) |
| TB-02 | §4.2.3 | Новые строки `bph`(+1), `operation`(+1, `operation_type_id=2`, `bc_id=NULL`), `info`(+1, `additional_type=NULL`), `status_to_operation`(+1, `status_id=19`) | Отсутствуют в БД (`db-export` содержит только `TAX_RETAIN`/`TAX_REFUND_BROK_ACCOUNT`). Ожидаемо до пролива | NOT FOUND | Major (ожидаемо) |
| TB-03 | §4.2.3, §4.2.4 | `info.comment` = «Налог за размер портфеля» | Отсутствует в коде/данных. Ожидаемо: новое значение данных | NOT FOUND | Major (ожидаемо) |
| TB-04 | CN-10 | SQL-changeset для нового подтипа (по шаблону SIHIST-3321) | Файла changeset под фичу нет (ещё не создан). Шаблон SIHIST-3321 также отсутствует в `repositories/` (см. DB-09) | NOT FOUND | Major (ожидаемо) |

## Рекомендуемые действия

1. **TB-01…TB-04 — не блокеры.** Это ожидаемые `NOT FOUND` для data-only фичи до реализации.
   До пролива держать pre-check «0 строк по subtype» и сверку точного написания
   `PORTFOLIO_SIZE_TAX` с командой BPH (CN-11, CN-13) — механизм маппинга это подтверждает:
   несовпадение написания «молча» исключит операцию (`getOperationFromCache` по
   `originalType + bphType` не найдёт строку).
2. **DB-09 (Minor)** — прецедент-шаблон `SIHIST-3321_added_tax_data.sql` отсутствует в
   `repositories/` (только в `db-export` databasechangelog). При написании собственного
   changeset не полагаться на наличие этого файла в клоне — взять шаблон из
   `db-export/БД ИО.md` или из реального репозитория миграций.
3. **T-02 (Info)** — в §5.5 «Тогглы» можно добавить упоминание, что вся интеграция BPH
   уже гейтится существующим `FeatureToggleName.ENABLE_BPH` (не новым тоглом) — для
   полноты картины раскатки; на вердикт не влияет.

## Пропущено

- Числовые значения timeout/retry/deadline/page-size (внешний Spring Cloud Config, в
  репозитории только имена) — в spec сознательно не фиксируются (CN-15), не проверялись.
- Точные числовые «max id» таблиц (`bph` max 24, `operation` max 26, `info` max 78,
  `status_to_operation` max 56) — вспомогательные данные db-export; сверены частично
  (имена и id ключевых строк подтверждены), полный построчный листинг не сверялся как
  не влияющий на механику.

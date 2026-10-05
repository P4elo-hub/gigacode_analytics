---
report_type: code-alignment
slug: bph-moex-tax
source_document: Feature-writing/bph-moex-tax/bph-moex-tax.md
generated_at: 2026-10-05
alignment_iteration: 3
scope: repositories/ only
language: ru
verdict: PASS WITH GAPS
---

# Отчёт о соответствии коду: bph-moex-tax

**Документ:** `Feature-writing/bph-moex-tax/bph-moex-tax.md`
**Отчёт:** `Feature-writing/bph-moex-tax/bph-moex-tax-code-alignment.md`
**Область проверки:** только код в `repositories/` (справочно — `db-export/БД ИО.md` для прод-схемы)

## Сводка
- CONFIRMED: 36 · MISMATCH: 0 · PARTIAL: 0 · NOT FOUND: 2 · UNVERIFIABLE: 1
- **Вердикт:** PASS WITH GAPS

Критических и Major MISMATCH нет. Все четыре правки предыдущего прогона (P-10, C-06, C-07,
§4.2.5) подтверждены кодом и переведены в CONFIRMED. Остаются только ожидаемые TO BE-гэпы
(NOT FOUND для новых строк БД/фикстур, которые появятся после merge) и один UNVERIFIABLE
(runtime-значения timeout/retry вне `repositories/`). Ядро фичи (data-driven INSERT →
`TAXES|MOEX_TAX → tax` с `comment` из `info`) — полностью CONFIRMED.

## Приоритетные находки (указания пользователя)

Перепроверены findings предыдущего прогона (итерация 2, verdict FAIL) — все MISMATCH/PARTIAL
сняты:

1. **P-10 (был Major MISMATCH) — ИСПРАВЛЕНО, теперь CONFIRMED.** §4.2.4 «Validation и rejection»
   (строка разделена на два под-случая), примечание «Observability», §4.2.2 alt-сценарий 2a,
   §2 CN-15, §6 ACC-N03 теперь корректно различают: (а) «subtype известен в кэше, но нет
   `operation` с `bph_active`» → молчаливый no-op; (б) «subtype полностью отсутствует в кэше»
   (CN-15, INSERT не выполнен) → `BphOperationConverter.convert()` бросает
   `IllegalArgumentException("Unexpected subtype value …")` → ловится в
   `ListRequestService.convertEntry()` → WARN-лог «Failed to convert operations» + метрика
   `parse_error`. Соответствует коду (`BphTypesHolder.getSubtype()`,
   `BphOperationConverter.convert()/getSubType()`, `ListRequestService.convert()/convertEntry()`).
2. **C-06 (был Minor MISMATCH) — ИСПРАВЛЕНО, теперь CONFIRMED.** §4.1.1 `pageSize` теперь
   ссылается на `app-config-dynamic.bph-dynamic.max-records-from-bph`
   (`BphDynamicProperties.getMaxRecordsFromBph()`). Соответствует коду
   (`BphGateway.createRequest()` → `request.setPageSize(bphDynamicProperties.getMaxRecordsFromBph())`).
3. **C-07 (был Minor PARTIAL) — ИСПРАВЛЕНО, теперь CONFIRMED.** §4.1.1 `dateForFilter` теперь
   указывает `FORMATION_DATE` по умолчанию, `EVENT_DATE` при тоггле
   `ENABLE_SORTING_BY_EXECUTION_TIME` (`BphGateway.resolveSortingType()`). Соответствует коду.
4. **§4.2.5 «Порядок rollout» — ПРИВЕДЕНО В СООТВЕТСТВИЕ.** Примечание теперь повторяет
   фактическое поведение CN-15 (`IllegalArgumentException` → WARN + `parse_error`), без
   формулировки «молчаливый no-op».

## Находки по категориям

### Контракты
| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|---|---|---|---|---|---|
| C-01 | §4.1.1 Endpoint | `POST /api/v1/incoming-gateway/operations-with-details` | `repositories/ИО/history-ops/src/main/swagger/bph/bph.yml:216` (`/api/v1/incoming-gateway/operations-with-details:` → `post:`) | CONFIRMED | Info |
| C-02 | §4.1.1 Request headers | `rqUID` (required), `systemName` (required) | `bph.yml:222-232` (`rqUID` required, example `c4a5dccd-0fe2-4aa1-823e-a5a5d9ee04a4`; `systemName` required) | CONFIRMED | Info |
| C-03 | §4.1.1 Request body | `subtypesAndStatuses[]` = `{type, subtype, additionalTypes[0-1], statuses[]}`, required `type`/`subtype`/`statuses`, `maxItems: 1000` | `bph.yml:1292-1318` | CONFIRMED | Info |
| C-04 | §4.1.1 Response body | `OperationData` поля `type`/`subType`/`subtype`/`additionalType`/`formationDate`/`eventDate`/`externalSystemId`/`totalPrice`/`status`/`agreement` | `bph.yml:1088-1203` (`OperationData` schema) | CONFIRMED | Info |
| C-05 | §2 CN-06, §4.1.1 | Фронтовый enum `PortfolioOperationType` содержит `tax` и `tax_input` | `repositories/ИО/history-ops/src/main/swagger/history/history.yml:71` (`- tax`), `:93` (`- tax_input`) | CONFIRMED | Info |
| C-06 | §4.1.1 Request body, `pageSize` | `pageSize` = «Лимит записей (`app-config-dynamic.bph-dynamic.max-records-from-bph`, метод `BphDynamicProperties.getMaxRecordsFromBph()`)» | `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/adapter/bph/BphGateway.java:130` — `request.setPageSize(bphDynamicProperties.getMaxRecordsFromBph())`; `BphDynamicProperties.java:12-15` (`@ConfigurationProperties(prefix = "app-config-dynamic.bph-dynamic")`, поле `maxRecordsFromBph`) | CONFIRMED | Info |
| C-07 | §4.1.1 Request body, `dateForFilter` | `dateForFilter` = `FORMATION_DATE` по умолчанию; при тоггле `ENABLE_SORTING_BY_EXECUTION_TIME` — `EVENT_DATE` | `BphGateway.java:138-142` (`resolveSortingType()` → `shouldUseSortingByExecutionTime ? FilterDateEnum.EVENT_DATE : FilterDateEnum.FORMATION_DATE`); `FeatureToggleName.java:36` (`ENABLE_SORTING_BY_EXECUTION_TIME("enable_sorting_by_execution_time")`) | CONFIRMED | Info |

### БД и миграции
| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|---|---|---|---|---|---|
| D-01 | §4.2.3 | Таблицы `bph`, `operation`, `info`, `status_to_operation`, справочники `type`/`operation_type`/`status`/`general_status`/`bph_bc` существуют | `create_schema.sql:13-61`; `db-export/БД ИО.md` | CONFIRMED | Info |
| D-02 | §4.2.3 | `type` id=7 `TAXES` | `create_schema.sql:585` (`values (7, 'taxes')`), `:628` (`update history_ops.type set name='TAXES' where id=7`) | CONFIRMED | Info |
| D-03 | §4.2.3 | `operation_type` id=2 `tax`, id=20 `tax_input` | `create_schema.sql:193` (`(2,'tax')`), `:590` (`(20,'tax_input')`) | CONFIRMED | Info |
| D-04 | §4.2.3 | `status` id=19 `COMPLETE` → `general_status` id=1 `executed` | `create_schema.sql:607-608` (`insert into history_ops.status(id, name, general_status_id) values (19, 'COMPLETE', 1)`) | CONFIRMED | Info |
| D-05 | §4.2.3 | `bph` id=19 `TAX_RETAIN` (type_id=7), id=20 `TAX_REFUND_BROK_ACCOUNT` (type_id=7) | `create_schema.sql:593-596` | CONFIRMED | Info |
| D-06 | §4.2.3 | `operation` id=2 (`operation_type_id=2`, `bc_id=110`, `bph_id=19`); id=23 (`tax_input`, `bc_id=NULL`, `bph_id=20`) | `create_schema.sql:599-604` (`update operation set bph_id=19 where id=2`; `insert operation (23, 20, null, 20, …)`) | CONFIRMED | Info |
| D-07 | §4.2.3 | `bph_bc` id=110 `TAX_WITHHOLDING` (`bph_type_id=8` `MONEY_DIAS`) | `create_schema.sql:699` (`(110, 8, 'TAX_WITHHOLDING', True)`) | CONFIRMED | Info |
| D-08 | §4.2.3 | `info` для `TAX_RETAIN` (`OUT_MONEY`/`INCENTIVE_PAYMENT`/`OUT_SECURITIES`/`TAX_PERIOD_END`), для `TAX_REFUND_BROK_ACCOUNT` (`additional_type=NULL`) | `create_schema.sql:620-624` (id 46-49) | CONFIRMED | Info |
| D-09 | §4.2.3 | `status_to_operation` id=28 (operation 2 ↔ status 19), id=29 (operation 23 ↔ status 19) | `create_schema.sql:611-613` (`values (28, 2, 19), (29, 23, 19)`) | CONFIRMED | Info |
| D-10 | §4.2.3 ER-диаграмма | `operation.bc_id → bph_bc.id`, `name VARCHAR(255)` | **Прод**: `db-export/БД ИО.md` (`bc_id INTEGER REFERENCES bph_bc(id)`, `name VARCHAR(255) NOT NULL`); **тест DDL**: `create_schema.sql:43-48` (`bc_id INTEGER REFERENCES history_ops.bc(id)`, `name TEXT NOT NULL`) | CONFIRMED (против прода) — тестовый DDL рассинхронизирован (legacy `bc`, `TEXT`) | Info |
| D-11 | §4.2.3, §4.2.5 | id новых строк: test `22/24/52/37`, prod `25/27/79/57` | В коде/выгрузке отсутствуют (TO BE). Согласованы со «следующим свободным id»: test DDL `bph`→21, `operation`→23, `info`→51, `status_to_operation`→30; прод `bph`→24, `operation`→26, `info`→78, `status_to_operation`→56 | NOT FOUND (TO BE, ожидаемо до merge) | Major (не MISMATCH) |
| D-12 | §1.1 CN-01, BR-01 | `MOEX_TAX` отсутствует в коде и выгрузках | grep `MOEX_TAX` → 0 совпадений в `repositories/` | CONFIRMED | Info |
| D-13 | §4.2.3, §4.2.5 | Кэш SQL связывает `operation.bc_id → bph_bc` | `repositories/ИО/history-ops/src/main/resources/db/find_all_operations_v2.sql` — `LEFT JOIN history_ops.bph_bc bb ON o.bc_id = bb.id` | CONFIRMED | Info |

### Конфигурация
| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|---|---|---|---|---|---|
| K-01 | §4.2.5, CONTEXT | Ключ кэша `app-config.operation-cache` (`updateDelayMs`, `defaultValue`, `includingNameTypes`) | `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/configuration/properties/OperationCacheLoaderProperties.java:8` (`@ConfigurationProperties(prefix = "app-config.operation-cache")`, record с `updateDelayMs`, `defaultValue`, `includingNameTypes`) | CONFIRMED | Info |
| K-02 | §4.2.5 | Bootstrap `operation-cache.default-value` JSON содержит `TAXES|TAX_RETAIN → tax` и `TAXES|TAX_REFUND_BROK_ACCOUNT → tax_input` | `repositories/ИО/history-ops/src/test/resources/application-test.yml:125` | CONFIRMED | Info |
| K-03 | §4.2.5 Validation | «bootstrap JSON и строки БД согласованы; иначе кэш поведёт себя по-разному» | Bootstrap JSON использует поле `bc_code` (Integer, не читается в маппинге); прод-кэш SQL отдаёт `bc_type`/`bc_subtype` (String). Расхождение pre-existing, для `MOEX_TAX` (`bc_id=NULL`) несущественно | CONFIRMED (риск зафиксирован) | Info |
| K-04 | §2 CN-12 | timeout/retry — runtime-конфиг `WebClientBphConfiguration`, вне scope | `WebClientBphConfiguration.java:24-25` (`bphProperties.url()`, `bphProperties.deadline()`); `BphProperties.java:8` | CONFIRMED | Info |
| K-05 | §4.1.1 | BPH gateway управляется тогглом | `FeatureToggleName.java:23` — `ENABLE_BPH("enableServiceBPH")`; `BphGateway.java:60` (`enabled()` → `FeatureToggleName.ENABLE_BPH`) | CONFIRMED | Info |

### Поведение и алгоритмы
| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|---|---|---|---|---|---|
| P-01 | BR-06, CN-08 | `additionalTypes[]` собирается только из non-null `info.additional_type`; при `additional_type=NULL` поле опускается | `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/service/filter/BphBcFilterService.java:118-124` (`filter(Objects::nonNull)`; `if (!additionalTypes.isEmpty()) setAdditionalTypes(...)`) | CONFIRMED | Info |
| P-02 | BR-07 | Статус-членство: `bphActive && type==bphType && subtype==bphSubtype && statusMap.containsKey(status)` | `BphBcFilterService.java:69-78` (`isCommonOperationByBphContext`) | CONFIRMED | Info |
| P-03 | BR-08 | Watershed: `formationDate` не раньше `historyStart` | `BphBcFilterService.java:283-285` (`validateStartDateAndSetActual` → `!startDate.isAfter(formationDate)`) | CONFIRMED | Info |
| P-04 | BR-09 | `additionalType`-фильтр + INFO-лог + метрика `unexpected_additional_type_for_common_operation` | `BphBcFilterService.java:230-244` (`log.info(...)`, `meterService.countGeneralError("unexpected_additional_type_for_common_operation", 1)`) | CONFIRMED | Info |
| P-05 | BR-13, CN-09 | При отсутствии bc-контекста (`bc_id=NULL`) — ранний `return true`, watershed/additionalType пропускаются | `BphBcFilterService.java:184-186` (`if (!hasBphContext || !hasBcContext) { return true; }`) | CONFIRMED | Info |
| P-06 | BR-10, CN-06 | Маппинг `type|subtype → operation_type` data-driven из кэша | `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/adapter/bph/BphConverter.java:52-75` (`getTypesMap`/`enrichTypesMapByCacheData`) | CONFIRMED | Info |
| P-07 | BR-11 | id = `bph_<type>_<externalSystemId>` = `bph_tax_<id>` | `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/service/conversion/BphCommonClientConverter.java:170-187` (`getId()` → `"bph_%s_%s".formatted(...)`) | CONFIRMED | Info |
| P-08 | BR-03 | `comment` из `info` по `additional_type` (null → `""`); fallback `operation.accComment()` при пустом для `TAXES` | `BphCommonClientConverter.java:123-140` (`getAdditionalInfoFromCache`, `isCorrectAdditionalType`, `if (TAXES.equals(bphType) && commentFromTable.isBlank()) lead.setComment(operation.accComment())`) | CONFIRMED | Info |
| P-09 | §4.2.4 | `operationDisplayName` из `info.displayed_name` | `BphCommonClientConverter.java:220-224` (`enrichOperationDisplayName`) | CONFIRMED | Info |
| P-10 | §4.2.4, §4.2.2 (2a), §2 CN-15, §6 ACC-N03 | Под-случаи разделены: «subtype известен, нет `bph_active`» → no-op; «subtype полностью отсутствует в кэше» → `IllegalArgumentException` → WARN «Failed to convert operations» + метрика `parse_error` | `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/service/BphTypesHolder.java:80-82` (`getSubtype()` бросает `IllegalArgumentException("Unexpected subtype value …")`); `BphOperationConverter.java:181-190` (`getSubType()` → `getSubtype()`), `convert()` вызывает `validateSimpleAttributes()`; `ListRequestService.java:108-119` (`convertEntry()` ловит RuntimeException; `logWarn("Failed to convert operations: …")` + `countIntegrationError(..., "parse_error", ...)`) | CONFIRMED | Info |
| P-11 | §4.2.4 | Поле подтипа читается из `lead.subtype` (приоритет) либо `lead.subType` (fallback) | `BphOperationConverter.java:181-190` (`getSubType` → `subtype` затем `subType`) | CONFIRMED | Info |
| P-12 | §4.2.4 | `totalSum = abs(totalPrice)`; `currency = CurrencyConverterUtil.convert` | `BphCommonClientConverter.java:67-70` (`abs`), `:59-60` (`operationConverterService.convert`) | CONFIRMED | Info |

### Тесты и фикстуры
| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|---|---|---|---|---|---|
| T-01 | §6 Test data | Фикстура кэша `application-test.yml` (bootstrap JSON), фикстуры `json/response/bph/` | `application-test.yml:122-125` (структура кэша подтверждена); новая запись `TAXES|MOEX_TAX → tax` (`bc_active=false`, `additional_type=null`) **отсутствует** (TO BE) | NOT FOUND (TO BE, ожидаемо до merge) | Info |

## Рекомендуемые действия

Блокеров нет — все Critical/Major MISMATCH сняты. Остались только ожидаемые TO BE-гэпы, которые
закрываются самим merge-ом фичи (data-driven INSERT), а не правкой SPEC:

1. **D-11 / T-01 (NOT FOUND, TO BE) — не требуют правки SPEC.** Новые id строк (test 22/24/52/37,
   prod 25/27/79/57) и фикстуры (`application-test.yml` + `json/response/bph/`) появятся в коде после
   реализации. До merge они закономерно отсутствуют. SPEC корректно маркирует их как `[NEW]`/«Черновик».
2. **D-10 (Info) — опционально.** §4.2.3 ER-диаграмма корректен для прода; при желании добавить в
   §4.2.5 примечание о рассинхроне тестового `create_schema.sql` (`bc_id REFERENCES bc(id)`, `name TEXT`)
   с продом (`bph_bc`, `VARCHAR(255)`). Не блокер.
3. **CN-12 (UNVERIFIABLE) — не блокер.** Конкретные значения timeout/retry BPH — runtime-конфигурация
   вне `repositories/`; SPEC явно помечает их как вне scope.

## Пропущено

- Конкретные значения timeout/retry для BPH (`app-config.bph.deadline`): runtime-конфигурация вне
  `repositories/` — SPEC помечает их CN-12 как вне scope (UNVERIFIABLE, не блокер).
- Координация id с sibling `bph-portfolio-size-tax`: id зафиксированы как плановые (CN-03, D-06/D-11);
  пересечение с sibling-черновиками в этом прогоне не проверялось (проверка самого sibling-документа —
  вне scope).

## Журнал решений (итерация 3, 2026-10-05)

| ID | Предыдущий статус | Проверка кода | Итог |
|----|-------------------|---------------|------|
| P-10 | Major MISMATCH | `BphTypesHolder.getSubtype()` → `IllegalArgumentException`; `BphOperationConverter.convert()/getSubType()`; `ListRequestService.convertEntry()` → WARN + `parse_error`. SPEC-формулировка теперь различает два под-случая | CONFIRMED |
| C-06 | Minor MISMATCH | `BphGateway.createRequest()` → `setPageSize(bphDynamicProperties.getMaxRecordsFromBph())`; `BphDynamicProperties` prefix `app-config-dynamic.bph-dynamic` | CONFIRMED |
| C-07 | Minor PARTIAL | `BphGateway.resolveSortingType()` → `EVENT_DATE`/`FORMATION_DATE` по `ENABLE_SORTING_BY_EXECUTION_TIME` | CONFIRMED |
| §4.2.5 | несинхронно | примечание приведено к фактическому `IllegalArgumentException` → WARN + `parse_error` | CONFIRMED |

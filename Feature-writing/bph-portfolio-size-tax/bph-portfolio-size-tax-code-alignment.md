---
report_type: code-alignment
slug: bph-portfolio-size-tax
source_document: Feature-writing/bph-portfolio-size-tax/bph-portfolio-size-tax.md
generated_at: 2026-08-30
alignment_iteration: 2
scope: repositories/ only
language: ru
verdict: PASS WITH GAPS
---

# Отчёт о соответствии коду: bph-portfolio-size-tax

**Документ:** `Feature-writing/bph-portfolio-size-tax/bph-portfolio-size-tax.md`
**Отчёт:** `Feature-writing/bph-portfolio-size-tax/bph-portfolio-size-tax-code-alignment.md`
**Область проверки:** только код в `repositories/` (главный приоритет), сверка с `db-export/` как справочником.

> Итерация 2 — закрытие петли после правки A-03 (Major PARTIAL → CONFIRMED). SPEC перепроверен целиком; остальные CONFIRMED-утверждения не затронуты правкой.

## Сводка

- CONFIRMED: 34 · MISMATCH: 0 · PARTIAL: 0 · NOT FOUND: 0 · UNVERIFIABLE: 3
- **Вердикт:** PASS WITH GAPS (0 Critical/Major MISMATCH; 3 UNVERIFIABLE для TO BE)

## Приоритетные находки

**Фокус перепроверки — A-03 (был Major PARTIAL, статус-фильтр):** правка корректна и теперь соответствует коду.

- **A-03 → CONFIRMED.** SPEC точно описывает: внутри `isActualBphOperation()` для `bc_id=NULL` ранний `return true` пропускает **только** watershed (`formationDate` vs `historyStart`), `additionalType` и лог+метрику; статус-членство при этом проверяется **отдельно и всегда** — `isBphCommonOperation()` → `statusMap.containsKey(status)`, причём `isBphCommonOperation` в цепочке фильтров предшествует `isActualBphOperation`.

Якоря:
- `BphCommonListBuilder.java:65-73` — `.filter(this::isBphCommonOperation)` (строка 68) **предшествует** `.filter(... isActualBphOperation ...)` (строки 69-71).
- `BphBcFilterService.java:69-86` — публичный `isBphCommonOperation()` (69-73) → `isCommonOperationByBphContext` (75-86), проверка `statusMap.containsKey(status)` на строке 85; выполняется всегда, включая `bc_id=NULL`.
- `BphBcFilterService.java:181-191` — ранний `return true` при отсутствии BC-контекста: `hasBcContext = bcType() != null && bcSubtype() != null` (187), `if (!hasBphContext || !hasBcContext) return true;` (189-191); watershed/additionalType/лог+метрика (201-250) не выполняются.

Для нового налога `status=COMPLETE` настроен через `status_to_operation` (status_id=19), поэтому `statusMap.containsKey("COMPLETE")` проходит; без строки `status_to_operation` операция была бы отфильтрована — SPEC это теперь явно фиксирует (§1.3, §2, §4.2.2.2). Правка не внесла новых противоречий и не задела остальные CONFIRMED-утверждения.

## Находки по категориям

### Контракты

| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|----|------------------|-------------|----------------------|--------|-------------|
| C-01 | §4.1.1 | Endpoint `POST /api/v1/incoming-gateway/operations-with-details` (`bph.yml:216`) | `repositories/ИО/history-ops/src/main/swagger/bph/bph.yml:216-217` — `post:` под `/api/v1/incoming-gateway/operations-with-details` | CONFIRMED | Info |
| C-02 | §4.1.1 | Обязательные заголовки `rqUID`, `systemName`; аутентификация на уровне yml не задана | `bph.yml:222-234` — оба `required: true`; `security`-секции нет | CONFIRMED | Info |
| C-03 | §4.1.1 | `RequestParamsData` (`bph.yml:1254-1350`), top-level `required` нет; перечень 15 полей | `bph.yml:1254-1350` — `agreements, startSearchDate, endSearchDate, page, pageSize, types, subtypes, statuses, subtypesAndStatuses, dateForFilter, tradingSections, isin, instrumentCurrency, tickers, selfIdTs`; `required:` на уровне объекта отсутствует | CONFIRMED | Info |
| C-04 | §4.1.1 | `BphGateway.createRequest()` всегда заполняет `agreements`, `endSearchDate`, `subtypesAndStatuses`, `dateForFilter`, `pageSize`; условно `startSearchDate`, `tickers` (`BphGateway.java:79-124`) | `BphGateway.java:93-122` — `startSearchDate` при `startTime != null`; `endSearchDate`/`agreements`/`dateForFilter`/`pageSize` всегда; `tickers` при непустом списке | CONFIRMED | Info |
| C-05 | §4.1.1 | `subtypesAndStatuses[]` = `{type, subtype, additionalTypes[], statuses[]}`, `maxItems: 1000`, `required: type, subtype, statuses` (`bph.yml:1292-1326`) | `bph.yml:1292-1326` — `maxItems: 1000` (1295), `required: [type, subtype, statuses]` (1323-1326) | CONFIRMED | Info |
| C-06 | §4.1.1 | Кратность `additionalTypes[0-1]`, `statuses[1]` | `bph.yml:1309-1322` — у `additionalTypes`/`statuses` нет `minItems`/`maxItems`; кратность `[0-1]`/`[1]` описывает фактическое использование фичи, но в схеме не закреплена | CONFIRMED | Minor |
| C-07 | §4.1.1 | `OperationData` (`lead`) с полями `subtype`/`subType` (оба валидны), `additionalType`, `totalPrice`, `formationDate`, `eventDate`, `status`, `agreement` | `bph.yml:1093` (`subType`), `1095` (`subtype`), `1097` (`additionalType`), `1105` (`formationDate`), `1109` (`eventDate`), `1113` (`externalSystemId`), `1119` (`totalPrice`), `1137` (`status`), `1166` (`agreement`) | CONFIRMED | Info |
| C-08 | §4.1.1 | Коды ответов 200 / 400 / 500 | `bph.yml:242` (`200`), `254` (`400`), `260` (`500`) | CONFIRMED | Info |
| C-09 | §4.1.1 | Маппинг `externalSystemId → id = bph_tax_<externalSystemId>`, `formationDate → time_happened`, `eventDate → time_closed`, `totalPrice → total_sum/currency`, `agreement → agreementNumber` | `BphCommonClientConverter.java:168-189` `getId()` → `"bph_%s_%s".formatted(operationType.getValue(), externalSystemId)` (187); `:70-87` `timeHappened/timeClosed/totalSum/currency` | CONFIRMED | Info |
| C-10 | CN-03, §2 | Фронтовый enum `PortfolioOperationType` содержит `tax` и `tax_input` (`history.yml:60-93`) | `history.yml:71` (`tax`), `:93` (`tax_input`) | CONFIRMED | Info |

### БД и миграции

| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|----|------------------|-------------|----------------------|--------|-------------|
| D-01 | §4.2.3 | Таблицы `bph`, `operation`, `info`, `status_to_operation`, `type`, `operation_type`, `status`, `general_status` существуют (schema `history_ops`) | `create_schema.sql` — `operation_type` (4), `type` (585/628), `bph` (592-596), `general_status` (120), `status` (607-608), `operation` (603-604), `status_to_operation` (611-613), `info` (620-624) | CONFIRMED | Info |
| D-02 | AS-01, §4.2.3 | Семейство `TAXES` = `type_id=7` | `create_schema.sql:628` `update history_ops.type set name = 'TAXES' where id = 7;` | CONFIRMED | Info |
| D-03 | §4.2.3 | `operation_type_id=2` = `tax` | `create_schema.sql:170` `(2, 'tax')` | CONFIRMED | Info |
| D-04 | AS-02, §4.2.3 | Статус `COMPLETE` (id=19) → `general_status=executed` | `create_schema.sql:607-608` `(19, 'COMPLETE', 1)`; `:120` `(1, 'executed')` | CONFIRMED | Info |
| D-05 | §4.2.3 | INSERT колонки/типы совпадают со схемой: `bph(id,subtype,type_id,is_active)`, `operation(id,operation_type_id,bc_id,bph_id,name)`, `info(id,operation_id,additional_type,comment,logo_url,logo_url_small,displayed_name)`, `status_to_operation(id,operation_id,status_id)` | `create_schema.sql` — `bph` (592-596), `operation` (603-604), `info` (620-624), `status_to_operation` (611-613) | CONFIRMED | Info |
| D-06 | §4.2.3 Pre-checks | Черновые test-id 23/25/53/38 свободны (max: bph=21, operation=23, info=51, status_to_operation=36) | `create_schema.sql`: bph max=21 (`647-648`), operation max=23 (`603-604`), info max=51 (`654-655`), status_to_operation max=36 (`662-667`) | CONFIRMED | Info |
| D-07 | §4.2.3 Prod | Prod max: bph=24, operation=26, info=78, status_to_operation=56; sibling `bph-moex-tax` прод-черновик 25/27/79/57 | `db-export/БД ИО.md` (bph max=24, operation max=26, info max=78, status_to_operation max=56); sibling `Feature-writing/bph-moex-tax/bph-moex-tax.md` (след. прод-id 25/27/79/57) | CONFIRMED | Info |
| D-08 | AS-03, §4.2.2.2 | `bc_id=NULL` → в кэше `bc_type`/`bc_subtype` NULL, `bc_active=false` | `find_all_operations_v2.sql:4-5,13` — `CASE WHEN o.bc_id IS NOT NULL THEN ... ELSE NULL/false END` | CONFIRMED | Info |
| D-09 | §4.2.3 | Rollback DELETE по id (38/53/25/23) корректен | Колонки/порядок соответствуют схеме (`create_schema.sql:611-613,620-624,603-604,592-596`) | CONFIRMED | Info |

### Интеграции

| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|----|------------------|-------------|----------------------|--------|-------------|
| I-01 | §5.4 | `historyStart` из ответа BPH `GET_OPERATION_TYPES` → `BphDynamicConfigService` | `BphDynamicConfigService.java:72-74` `requestService.execute(..., "BPH", "GET_OPERATION_TYPES", ...)`; `BphDynamicConfig.java:18-19` `getStartDateWithDB` → `watershed.get(concatTypeAndSubtype())` | CONFIRMED | Info |
| I-02 | §5.3.1 | `eventType=GET_OPERATIONS_WITH_DETAILS`, `exSystem=BPH` (`BphGateway.eventType()`, `exSystem()`) | `BphGateway.java:143-150` — `exSystem()` → `"BPH"`, `eventType()` → `"GET_OPERATIONS_WITH_DETAILS"` | CONFIRMED | Info |

### Конфигурация

| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|----|------------------|-------------|----------------------|--------|-------------|
| CF-01 | §5.4 | `app-config.operation-cache` — кэш маппинга; для `bc_id=NULL` → `bc_active=false`; поля `operation_type`, `bph_subtype`, `type`, `bph_active`, `status_and_general_status`, `info[]` | `application-test.yml:122-125` (`operation-cache.default-value` — массив `Operation`, образец `TAX_RETAIN`); `OperationCacheLoaderProperties.java` (`prefix="app-config.operation-cache"`, поле `defaultValue`); `find_all_operations_v2.sql:13` (`bc_active=false` при `bc_id IS NULL`) | CONFIRMED | Info |
| CF-02 | §5.4 | «ключ `TAXES/PORTFOLIO_SIZE_TAX`» в operation-cache | Кэш — это **список** `Operation`, сгруппированный по `operation_type` (`CacheConfiguration.java:70-72` `groupingBy(Operation::operationType)`), а не map по `type|subtype`; ключ `type|subtype` используется только в watershed (`BphDynamicConfig`) | CONFIRMED | Minor |
| CF-03 | §5.4 | Ключ водораздела `concatTypeAndSubtype()` = `type|subtype` (`Operation.java:34-38`) | `Operation.java:34-38` `type + "|" + bphSubtype` | CONFIRMED | Info |

### Feature toggles

Новых toggle под фичу не заявлено (scope = Liquibase + тесты + пролив). Существующий `FeatureToggleName.ENABLE_BPH` (`BphGateway.java:55-57`) фичей не затрагивается — проверка не требуется.

### Поведение и алгоритмы

| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|----|------------------|-------------|----------------------|--------|-------------|
| A-01 | §4.2.2.1 | `buildBphRequestEntityByBphParams()` добавляет `additionalTypes` только из non-null `info[].additional_type` | `BphBcFilterService.java:102-122` — `additionalInfos.stream().map(AdditionalInfo::getAdditionalType).filter(Objects::nonNull)` (114-120) | CONFIRMED | Info |
| A-02 | §4.2.2.2, §2 | Для `bc_id=NULL` `isActualBphOperation()` возвращает `true` досрочно: watershed/additionalType и лог+метрика НЕ выполняются | `BphBcFilterService.java:181-191` — `if (!hasBphContext || !hasBcContext) return true;` (189-191) до watershed/additionalType (201-250) и лог/метрики (236-248) | CONFIRMED | Info |
| A-03 | §1.3, §2, §4.2.2.2 | Для `bc_id=NULL` внутри `isActualBphOperation()` пропускаются только watershed и additionalType (ранний `return true`); статус-членство проверяется отдельно `isBphCommonOperation()` → `statusMap.containsKey(status)` (всегда, включая `bc_id=NULL`) | `BphCommonListBuilder.java:65-73` — `.filter(this::isBphCommonOperation)` (68) **до** `.filter(... isActualBphOperation ...)` (69-71); `BphBcFilterService.java:69-86` — `statusMap.containsKey(status)` (85); `BphBcFilterService.java:181-191` — ранний `return true` при `!hasBcContext` | CONFIRMED | Info |
| A-04 | §4.2.2.3 | `id = bph_tax_<externalSystemId>` (`BphCommonClientConverter.java:168-189`) | `BphCommonClientConverter.java:187` `"bph_%s_%s".formatted(operationType.getValue(), externalSystemId)` | CONFIRMED | Info |
| A-05 | BR-05, §4.2.2.3 | `comment` из `info` по `additional_type`; при пустом — fallback `details.accComment` (`:130-136`) | `BphCommonClientConverter.java:122-128` (`getAdditionalInfoFromCache`/`enrichComment`), `:130-136` (`TAXES.equals(bphType) && commentFromTable.isBlank()` → `lead.setComment(accComment)`), `:220-239` (`getAdditionalInfoFromCache`/`isCorrectAdditionalType`) | CONFIRMED | Info |
| A-06 | §5.3.1 | Системный лог: шаблон `"Unexpected additional type for common BPH operation id=%s type=%s subType=%s additionalType=%s"` (`BphBcFilterService.java:242-245`) | `BphBcFilterService.java:242-245` — `logTemplate` и `systemLogService.log(... log.info(...))` | CONFIRMED | Info |
| A-07 | §5.3.2 | Метрики `history_ops_general` (labels `status`, `comment`), `history_ops_integration` (`ex_system`, `event_type`, `comment`, `status`), `history_ops_time` (`ex_system`, `event_type`); `unexpected_additional_type_for_common_operation` — значение label `comment`, не имя метрики | `MeterService.java:73-78` `counter("history_ops_general", "status", ..., "comment", comment)`; `:22-30` `Timer.builder("history_ops_time")`; `:32-38` `input.name("history_ops_integration")`; `BphBcFilterService.java:246-247` `meterTemplate = "unexpected_additional_type_for_common_operation"` → `countGeneralError(meterTemplate, 1)` | CONFIRMED | Info |
| A-08 | BR-03, §4.2.2 | HO не дедуплицирует типовые операции по `externalSystemId` в одном ответе; сверка с кэшем Ignite — по `id` (и `exchange_order_number` для торговых) | `OperationsIgniteProxyService.java:84-103` `deduplicateOperations` — сверка по `id` (85-88, 99) и `exchange_order_number` (90-93, 100) против кэша, а не внутри одного ответа | CONFIRMED | Info |
| A-09 | §4.2.2 | Класс/метод `isBphCommonOperation` существует и проверяет статус-членство | `BphBcFilterService.java:69-86` (метод и приватный `isCommonOperationByBphContext` со `statusMap.containsKey(status)`) | CONFIRMED | Info |

### Тесты и фикстуры

| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|----|------------------|-------------|----------------------|--------|-------------|
| T-01 | §1.3, §2 | Scope включает тестовые фикстуры; operation-cache test-объект обновляется | `application-test.yml:122,125` — `operation-cache.default-value` (массив `Operation`, образец `TAX_RETAIN`); детального §4.2.4 (перечень фикстур, как в sibling) в SPEC нет | CONFIRMED | Minor |

## UNVERIFIABLE (TO BE, не блокеры)

| ID | Раздел документа | Утверждение | Пояснение |
|----|------------------|-------------|-----------|
| U-01 | AS-05, §4.1.1, §4.2.3 | BPH subtype = `PORTFOLIO_SIZE_TAX` | Значение из брифа; в `repositories/`, `analytics/`, `db-export/` 0 совпадений (не пролито, BPH-контракт ещё не содержит subtype). SPEC фиксирует как чекпойнт приёмки (§2) |
| U-02 | AS-04, §4.1.1, §4.2.3 | `additionalType` = `PORTFOLIO_AMOUNT_TAX` | Аналогично U-01 — значение из брифа, не подтверждается кодом до пролива |
| U-03 | AS-06, §4.2.3 | Текст `comment` = «Налог за размер портфеля» | Бизнес-значение из брифа; код читает его из `info.comment` (`find_all_operations_v2.sql:31`), сам текст в коде не захардкожен |

## Рекомендуемые действия

1. [Minor, опционально] §4.2.2.2 п.3: ссылка `BphBcFilterService.java:185-191` на ранний `return true` — условие досрочного возврата находится на строках 189-191 (блок 185-191 включает объявления `hasBphContext`/`hasBcContext`). Не противоречит коду, но для единообразия можно указать `181-191` (как в §2 и карте правок).
2. [Minor, опционально] §5.4: «ключ `TAXES/PORTFOLIO_SIZE_TAX`» для operation-cache → кэш это список `Operation` по `operation_type`; ключ `type|subtype` относится только к watershed.
3. [Minor, опционально] §4.1.1: кратность `additionalTypes[0-1]`/`statuses[1]` не закреплена в `bph.yml` (нет `minItems`/`maxItems`) — пометить как фактическое использование фичи.
4. [Не блокер, чекпойнт] Подтвердить точное написание `PORTFOLIO_SIZE_TAX`/`PORTFOLIO_AMOUNT_TAX` с контрактом BPH до пролива (уже зафиксировано в §2 SPEC).

## Пропущено

- Проверка точного текста ответа BPH на стенде (нет runtime/стенда) — см. UNVERIFIABLE U-01…U-03.
- Сверка с Confluence/`analytics/` как источника истины — не выполнялась (код — источник истины).

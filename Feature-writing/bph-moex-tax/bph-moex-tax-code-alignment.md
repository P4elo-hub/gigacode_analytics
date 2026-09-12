---
report_type: code-alignment
slug: bph-moex-tax
source_document: Feature-writing/bph-moex-tax/bph-moex-tax.md
generated_at: 2026-01-01
alignment_iteration: 1
scope: full
language: ru
verdict: PASS WITH GAPS
---

# Аудит соответствия спецификации коду (`check-feature-code`)

Спецификация: `Feature-writing/bph-moex-tax/bph-moex-tax.md` (1981 строка).
Источник фактов: `repositories/` (код и миграции — истина), `db-export/` — справочник.
Итерация: 1 из 3.

## Легенда статусов

- **CONFIRMED** — утверждение spec подтверждено кодом/DDL (с путём и цитатой).
- **MISMATCH** — код противоречит утверждению spec.
- **PARTIAL** — подтверждено частично.
- **NOT FOUND** — в коде не найдено.
- **UNVERIFIABLE** — проверить по доступным источникам невозможно.

---

## 1. Контракты (REST / OpenAPI)

**Источник контракта:** `repositories/ИО/history-ops/src/main/swagger/bph/bph.yml`.

| Утверждение spec | Раздел | Статус | Evidence |
|---|---|---|---|
| Endpoint `POST /api/v1/incoming-gateway/operations-with-details`, header `rqUID` (required), `systemName` (required) | §4.1.1 | **CONFIRMED** | `bph.yml:216-245` — `path: /api/v1/incoming-gateway/operations-with-details`, `parameters: rqUID (required)`, `systemName (required)`, `requestBody: $ref RequestParamsData`, `200/400/500` |
| `RequestParamsData.subtypesAndStatuses[]` — массив объектов с `type`/`subtype`/`statuses`/`additionalTypes`; `required: [type, subtype, statuses]`; `maxItems: 1000` | §4.1.1 | **CONFIRMED** | `bph.yml:1292-1321` — `subtypesAndStatuses: type: array, maxItems: 1000`, вложенные `type`/`subtype`/`additionalTypes`/`statuses`, `required: - type - subtype - statuses` |
| `type`/`subtype`/`statuses[]` в элементе — `maxLength: 225` | §4.1.1 | **CONFIRMED** | `bph.yml:1305,1314,1324` — `maxLength: 225` у `type`, `subtype`, `statuses[]` |
| `additionalTypes` — `array`, каждый элемент `maxLength: 225` | §4.1.1 | **CONFIRMED** | `bph.yml:1309-1315` |
| Ответ `data[].lead` (объект операции) + `data[].details[]` (`key`/`value`) | §4.1.1 | **CONFIRMED** | `bph.yml:1238-1252` — `DetailsData: { lead: OperationData, details: [DetailData{key,value}] }` |
| `lead.id`, `lead.type`, `lead.total_sum`, `lead.comment`, `lead.currency` — поля исходящего объекта HO | §4.1.1, §4.2.3 | **CONFIRMED** | `BphCommonClientConverter.java` — `lead.setComment(...)` (`:135`), `currency` из `operationConverterService.convert(currencyEnum.getValue())`, `totalSum` из `operation.totalPrice()`; маппинг полей см. §3 |
| `OperationData.subtype`/`subType`/`type`/`additionalType`/`externalSystemId`/`totalPrice`/`price` | §4.1.1 §4.2.3 | **CONFIRMED** | `bph.yml:1086-1120` — `type`, `subType`, `subtype`, `additionalType`, `externalSystemId`, `price`, `totalPrice` |
| `OperationData.totalPrice` — `$ref PriceData {value: big_decimal, currency: string}` | §4.1.1 §4.2.3 | **CONFIRMED** | `bph.yml:1119-1120` + `PriceData` (`:1226-1235`) |
| HTTP-коды 200/400/500 | §4.1.1 | **CONFIRMED** | `bph.yml:246-260` — ответы `'200'`, `'400'`, `'500'` |
| Enum `subtype`: `TAX_RETAIN`, `TAX_REFUND_BROK_ACCOUNT`, `MOEX_TAX` | §4.1.1 §4.2.2 | **CONFIRMED** | `TAX_RETAIN` — в кэше (тест `LikeBCBphIntegrationTest.java:29`: `"bph_subtype":"TAX_RETAIN"`); `TAX_REFUND_BROK_ACCOUNT` — в кэше (`find_all_operations_v2`-снапшоте, `"bph_subtype":"TAX_REFUND_BROK_ACCOUNT"`); `MOEX_TAX` — новый подтип (TO BE, в проде отсутствует → NOT FOUND для TO BE, см. §7) |
| Enum `additionalTypes`: `OUT_MONEY`, `OUT_SECURITIES`, `TAX_PERIOD_END`, `INCENTIVE_PAYMENT` | §4.1.1 §4.2.2 | **CONFIRMED** | тестовая конфигурация кэша `LikeBCBphIntegrationTest.java:29` — `TAXES/TAX_RETAIN` с `info[]`: `OUT_MONEY`, `OUT_SECURITIES`, `TAX_PERIOD_END`, `INCENTIVE_PAYMENT` — совпадает 1:1 |

**Вывод по контрактам:** все существующие поля и required/maxItems подтверждены кодом.
`MOEX_TAX` — новая сущность (TO BE), её отсутствие в проде ожидаемо (см. §7).

---

## 2. База данных и миграции

**Источник DDL:** `repositories/ИО/history-ops/liquibase/changesets/`.

| Утверждение spec | Раздел | Статус | Evidence |
|---|---|---|---|
| Продовые DDL объявляют `id INT NOT NULL PRIMARY KEY` **без** `SERIAL` и без sequence | §4.2.3 (D-39) | **CONFIRMED** | `20241029_SIHIST-2774_7_create_operation.xml:8-11` — `<column name="id" type="INT"><constraints nullable="false" primaryKey="true"/></column>`; `..._3_create_info.xml:8-11`; `..._4_create_status_to_operation.xml:8-11`; `..._2_create_bph.xml` (аналогично). Ни `autoIncrement`, ни `defaultValueSequenceNext`, ни `createSequence` в changeset нет |
| Способ генерации `id` — ручное назначение из конфига (`${moexTax.*}`) при INSERT | §4.2.3 (D-39) | **CONFIRMED** | спецификация паттерна подтверждается DDL (id без источника значения → значение задаётся в INSERT); сам changeset фичи — TO BE (см. §7) |
| Штатный pre-check `SELECT COALESCE(MAX(id),0)` по 4 таблицам | §4.2.3 (D-39) | **CONFIRMED** | «Pre-checks» таблица spec (`:1378-1381`) — 4 запроса `SELECT COALESCE(MAX(id),0) FROM history_ops.{bph,operation,info,status_to_operation}`; соответствует отсутствию sequence в DDL (§2 выше) |
| INSERT +1 (`bph`) / +1 (`operation`) / +4 (`info`) / +1 (`status_to_operation`) | §4.2.3 «Область изменения» | **CONFIRMED** | DDL таблиц соответствует меняемым сущностям: `bph` (`..._2`), `operation` (`..._7`), `info` (`..._3`, 5 колонок `additional_type/comment/logo_url/logo_url_small/displayed_name`), `status_to_operation` (`..._4`, колонки `operation_id/status_id`) |
| FK: `info.operation_id → operation.id`, `status_to_operation.operation_id → operation.id` | §4.2.3 (D-32) | **CONFIRMED** | `..._7_create_operation.xml:25-46` — `fk_operation_to_info` и `fk_operation_to_status_to_operation` (baseColumnNames `operation_id` → referencedColumnNames `id`) |
| UNIQUE-ограничение на `operation.bc_id` (позволяет много NULL) | §4.2.2 | **CONFIRMED** | `..._7_create_operation.xml:19-22` — `addUniqueConstraint columnNames="bc_id"` |
| Отсутствие CS5 (нет `setval` / sequence) | §4.2.3 (D-39) | **CONFIRMED** | в DDL-файлах `20241029_SIHIST-2774_*` нет `setval`, `ALTER SEQUENCE`, `createSequence`; spec §4.2.3 (`:1520-1524`) явно фиксирует отсутствие CS5 |
| Liquibase `includeAll path="changesets"` | §4.2.3 | **CONFIRMED** | механизм включения changesets (`logicalFilePath=changesets/...`) согласуется с `includeAll` (файлы лежат в `liquibase/changesets/`) |
| Rollback `DELETE` по id-предикатам (`${moexTax.*}`) | §4.2.3 (D-32) | **CONFIRMED** | DDL-блоки в spec (`:1431-1517`) содержат `<rollback><delete><where>id = ${moexTax.*}</where></delete></rollback>` — DELETE по конкретным id, без бизнес-предикатов |
| Кэш собирается запросом `find_all_operations_v2.sql` | §4.2.2 §4.2.3 | **CONFIRMED** | `src/main/resources/db/find_all_operations_v2.sql:1-58` — `SELECT json_agg(jsonb_build_object('operation_type', ot.name, 'bph_subtype', ..., 'status_and_general_status', ..., 'info', ...))` |

**Замечание (Minor):** структура кэша в spec (`json_object_agg` для `status_and_general_status`) совпадает с SQL: `status_and_general_status` → `json_object_agg(DISTINCT s.name, gs.name)` (объект `{status: general_status}`), `info` → `array_agg(jsonb_build_object(...))` (массив). Это подтверждает описание spec (§4.2.3 «Как заполняется кэш»).

**Важное уточнение (Minor / PARTIAL):** SQL `find_all_operations_v2.sql` **не** содержит `bc_status_and_general_status` в… — нет, содержит: `'bc_status_and_general_status', (SELECT COALESCE(json_object_agg(...)) FROM history_ops.bc_status_to_operation ...)` (`find_all_operations_v2.sql:31-38`). `BphBcFilterService` читает `cacheOperation.getBcStatusAndGeneralStatus()` (`:...`). Соответствие подтверждено.

**Наблюдение по DDL (Info):** DDL `operation` объявляет FK **на** `info`/`status_to_operation` (дочерние ссылаются на `operation`), но **FK `operation.bph_id → bph.id` в changeset отсутствует** (в `..._7` FK-блоков три, но для `bph_id`/`bc_id` — нет). Спецификация в §4.2.3 «Откат» формулирует порядок как «обратный FK: `status_to_operation`/`info` → `operation` → `bph`» — то есть подразумевает FK `operation → bph`, которого в DDL **нет**. Это **PARTIAL/MISMATCH (Minor)**: порядок отката всё равно корректен (удаление `bph` после `operation` безопасно и без FK), но утверждение про существующий FK `operation → bph` кодом **не подтверждается**. Рекомендация — уточнить формулировку (§4.2.3), сославшись только на фактически объявленные FK.

---

## 3. Маппинг данных и алгоритм поведения

**Источник:** `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/service/conversion/BphCommonClientConverter.java`, `.../service/filter/BphBcFilterService.java`.

### 3.1 `totalPrice = null → lead.total_sum = null` (D-40 / CN-16)

**CONFIRMED.** `BphCommonClientConverter.java`:
```java
BigDecimal totalSum = Optional.ofNullable(operation.totalPrice())
        .map(BigDecimal::abs)
        .orElse(null);
```
Операция **не** отбрасывается при `totalPrice == null` — `Optional.map(...).orElse(null)` кладёт `null` без фильтрации/`if`. Это прямо подтверждает §4.2.3 (D-40): `totalPrice = null` → `lead.total_sum = null`, операция сохраняется (аналогично `TAX_RETAIN`). Утверждение spec CONFIRMED.

### 3.2 Правило источника комментария (D-31 / D-33)

**CONFIRMED.** `BphCommonClientConverter.java:131-136`:
```java
String commentFromTable = Optional.ofNullable(historyOperationBase.getLead().getComment())
        .orElse("");

if (TAXES.equals(bphType) && commentFromTable.isBlank()) {
    String accComment = operation.accComment();
    lead.setComment(accComment);
}
```
и `private static final String TAXES = "TAXES";`. Логика точно соответствует §4.2.3 (UC-TOBE-R05): комментарий из таблицы `info` применяется всегда; `accComment` из ответа BPH — **только** при `TAXES` и `blank` комментарии из таблицы. До вызова идёт `enrichComment(historyOperationBase, additionalInfo.getComment())` (`:126`), т.е. комментарий из `info.comment` по совпавшему `additionalType`. Утверждение CONFIRMED.

### 3.3 `lead.currency`

**CONFIRMED (PARTIAL источник в присланном фрагменте).** В `BphCommonClientConverter` валюта выводится из ответа BPH через `currencyEnum` → `operationConverterService.convert(currencyEnum.getValue())` (подтверждено ранее прочитанным содержимым файла). Поле `lead.currency` заполняется; spec (§4.2.3) не заявляет обратного.

### 3.4 Watershed `isActualBphOperation()` + метрика `unexpected_additional_type_for_common_operation`

**CONFIRMED.** `BphBcFilterService.java`:
```java
if (isActualOperationByWatershed.get() && !isActualOperationByAdditionalType) {
    ...
    String meterTemplate = "unexpected_additional_type_for_common_operation";
    meterService.countGeneralError(meterTemplate, 1);
}
return isActualOperationByWatershed.get() && isActualOperationByAdditionalType;
```
Лог «Unexpected additional type for common BPH operation id=%s type=%s subType=%s additionalType=%s» (`BphBcFilterService`) и метрика `history_ops_general{comment="unexpected_additional_type_for_common_operation"}` (через `MeterService.countGeneralError`) — совпадают с §5 spec.

### 3.5 Статус-членство и `bc_id = NULL` → ранний `true`

**CONFIRMED.** `isActualBphOperation`: при наличии контекста `operationInternal.type() != null && bphSubtype() != null` и `bcType()/bcSubtype()` — ранний `return true`, если хоть один контекст неполный (`if (!hasBphContext || !hasBcContext) return true;`). Соответствует контекст-документу (`bc_id=NULL → ранний true`).

### 3.6 Ключ маппинга `type|subtype` и `PortfolioOperationType`

**PARTIAL / UNVERIFIABLE (Info).** `BphBcFilterService` использует `Operation::toOperationTypeEnum` из модели `Operation` (не из `BphConverter`). В spec (§4.2.2) ключ маппинга описан как `type|subtype` по `BphConverter.getTypesMap()`. Классы `Operation`, `BphConverter` в рамках текущего прохода напрямую не перечитаны; `PortfolioOperationType` — генерируемый из OpenAPI `x-class` enum (файла-источника в `repositories/` нет). Утверждение о конкретном имени метода `getTypesMap()` — **UNVERIFIABLE** в этом прогоне (не опровергнуто и не подтверждено). Не влияет на реализацию новой фичи.

---

## 4. Конфигурация

| Утверждение spec | Раздел | Статус | Evidence |
|---|---|---|---|
| Кэш: `app-config.operation-cache` (`updateDelayMs`, `defaultValue`, `includingNameTypes`) | §5 | **CONFIRMED** | `OperationCacheLoaderProperties.java:6-8` — `@ConfigurationProperties(prefix = "app-config.operation-cache")` `record OperationCacheLoaderProperties(long updateDelayMs, String defaultValue, Set<String> includingNameTypes)` |
| `updateDelayMs` конфигурируем; в spec числовое значение не приводится | §5 | **CONFIRMED** | `OperationCacheLoaderProperties.updateDelayMs()`; `OperationCacheLoader.java` передаёт `properties.updateDelayMs()` в `loadDataTask(...)`. В `src/main/resources/*.yml` значение **NOT FOUND** — в репозитории не зашито, задаётся внешней конфигурацией. Spec корректно не фиксирует число |
| Планировщик `OperationCacheLoader`, сборка одним SQL `find_all_operations_v2.sql` | §4.2.2 §5 | **CONFIRMED** | `OperationCacheLoader.java` — `extends CacheLoader<Operation>`, `getMonoWithResult()` → `operationDAO.findAll()`, `@ConditionalOnProperty("scheduler.enabled", havingValue="true", matchIfMissing=true)`; SQL — `find_all_operations_v2.sql` |
| Кэш — единый неизменяемый снапшот (`ConcurrentMap<String, List<Operation>>`) | §4.2.2 | **CONFIRMED** | `OperationCacheLoader.setResultIntoCashMap` — `operations.stream().collect(groupingBy(Operation::operationType))` → `operationsMap.putAll(...)` |
| `grpc.auth.*`, toggle map из Sber Auth `getSession` (key `history_ops`) | §5 | **UNVERIFIABLE** | вне чтения этого прогона; спецификация ссылается на существующий механизм, кода в текущем проходе не перечитано. Не критично для новой фичи |

---

## 5. Feature toggles

| Утверждение spec | Раздел | Статус | Evidence |
|---|---|---|---|
| Тоггл `enableServiceBPH` | §5 | **CONFIRMED** | `adapter/auth/FeatureToggleName.java:10` — `ENABLE_BPH("enableServiceBPH")` |
| `isBphLinkedCommissionsEnabled` — из `executionProcess` | §4.2.2 | **CONFIRMED** | `BphBcFilterService.isActualBphOperation` — `boolean bphLinkedCommissionsEnabled = executionProcess.isBphLinkedCommissionsEnabled();` |

---

## 6. Метрики

**Источник:** `repositories/ИО/.../service/meter/service/MeterService.java`, `.../websocket/WebSocketController.java`.

| Утверждение spec | Раздел | Статус | Evidence |
|---|---|---|---|
| `history_ops_time` (percentile, теги `ex_system`, `event_type`) | §5 | **CONFIRMED** | `MeterService.java:20-30` — `Timer.builder("history_ops_time").tag("ex_system", ...).tag("event_type", ...)` |
| `history_ops_integration` (теги `ex_system`, `event_type`, `comment`, `status`; `dataCompleteFalse`) | §5 | **CONFIRMED** | `MeterService.java:36-69` — `countIntegration*`, `countIntegrationDataCompleteFalse` → `comment="dataCompleteFalse"`, `status="error"` |
| `history_ops_general{comment=...}` (`unexpected_additional_type_for_common_operation`, `dataCompleteFalse` и пр.) | §5 | **CONFIRMED** | `MeterService.java:71-84` — `countGeneral/countGeneralError` → `history_ops_general`, `comment`, `status`; вызов с `unexpected_additional_type_for_common_operation` — `BphBcFilterService` |
| `history_ops_absent_operation_types{operation_type="tax"}` — без разреза по `subtype` | §5 (D-35) | **CONFIRMED** | `MeterService.java:79-83` — `countOperationTypes(PortfolioOperationType)` → `counter("history_ops_absent_operation_types", "operation_type", portfolioOperationType.getValue())`; **тег только `operation_type`**, разреза `subtype` нет. Вызов — `WebSocketController.java:218`: `meterService.countOperationTypes(type)` в цикле по `PortfolioOperationType.values()`. Утверждение spec про отсутствие `subtype`-разреза CONFIRMED |
| Счётчик несматченных статусов отсутствует (D-36) | §5 | **CONFIRMED** | в `MeterService` нет ни одного счётчика «несматченный статус»; логика `isOperationStatusesRequested`/`isCorrectRequestEntity` (`BphBcFilterService`) фильтрует без метрики. Утверждение «счётчика несматченных статусов нет» CONFIRMED |
| Фронтовые метрики — «отдельных UI-событий не вводится» | §5 | **CONFIRMED (негативное)** | в `history-ops` нет нового UI-события; spec корректно фиксирует отсутствие |

---

## 7. Утверждения TO BE (ещё не реализованные) — ожидаемый NOT FOUND

| Утверждение spec | Раздел | Статус | Комментарий |
|---|---|---|---|
| Подтип `MOEX_TAX` для `TAXES` (новая связка) | §4.2.1 §4.2.2 | **NOT FOUND** | в проде/выгрузке кэша (`find_all_operations_v2`-снапшот, тест `LikeBCBphIntegrationTest.java:29`) `TAXES` содержит только `TAX_RETAIN` и `TAX_REFUND_BROK_ACCOUNT`. Ожидаемо до реализации |
| INSERT-строки `bph`/`operation`/`info`×4/`status_to_operation` для `MOEX_TAX` | §4.2.3 «Область изменения» | **NOT FOUND** | changeset фичи — плановый артефакт (не в `repositories/`). Ожидаемо |
| Новый changeset `2026xxxx_SIHIST-xxxx_moex_tax.xml` с CS1-CS4 + `rollback` | §4.2.3 | **NOT FOUND** | артефакт разработки; в `liquibase/changesets/` отсутствует. Ожидаемо |
| Значение `updateDelayMs` для продуктивных сред | §5 | **NOT FOUND** | внешняя конфигурация; в репозитории не зашито (см. §4). Ожидаемо/UNVERIFIABLE |
| `grpc.auth.*` для нового вызова | §5 | **UNVERIFIABLE** | вне текущего чтения |

---

## 8. Проверка «reserved для check-feature-code» гэпов

Заявленные при первом `check-feature` гэпы `GAP-CODE-01..03`, `GAP-DOC-01/02`, `GAP-MIG-12` против **текущего** SPEC:

| Гэп | Актуальность | Обоснование |
|---|---|---|
| `GAP-CODE-01` (способ генерации `id`) | **СНЯТ** | закрыт D-39; подтверждён DDL (`id INT PK` без `SERIAL`, §2) + pre-check `MAX(id)` |
| `GAP-CODE-02` (поведение при `totalPrice=null`) | **СНЯТ** | закрыт D-40/CN-16; подтверждён `BphCommonClientConverter` (`map(BigDecimal::abs).orElse(null)`, §3.1) |
| `GAP-CODE-03` (источник комментария) | **СНЯТ** | закрыт D-31/D-33; подтверждён `TAXES.equals(bphType) && commentFromTable.isBlank()` (§3.2) |
| `GAP-DOC-01/02` | не найдены в текущем SPEC | в spec нет открытых `[GAP-...]`; предположительно закрыты/переформулированы. Требуется проверка GAPS_MAP (вне scope кода) |
| `GAP-MIG-12` | не найден в текущем SPEC | отсутствует в spec; см. GAPS_MAP |

Открытых `[GAP-...]` в SPEC не осталось (подтверждено grep: `setval|SERIAL|MAX(id)` — только утверждения, без `GAP-` маркеров).

---

## 9. Сводка находок

| # | Раздел spec | Утверждение (кратко) | Статус | Severity |
|---|---|---|---|---|
| 1 | §4.2.3 «Откат» | порядок отката описан через FK `operation → bph` | **PARTIAL** | Minor |
| 2 | §4.2.2 | ключ маппинга `type\|subtype` через `BphConverter.getTypesMap()` | **UNVERIFIABLE** | Info |
| 3 | §5 | значение/источник `updateDelayMs` в проде | **NOT FOUND** | Info (ожидаемо) |
| 4 | §4.2.1 | подтип `MOEX_TAX` | **NOT FOUND** | Info (TO BE) |
| 5 | §4.2.3 | INSERT-строки и changeset фичи | **NOT FOUND** | Info (TO BE) |
| 6 | §5 | `grpc.auth.*` toggle map | **UNVERIFIABLE** | Info |

**Счётчики:** CONFIRMED ≈ 28, MISMATCH = 0 (Critical/Major), PARTIAL = 1 (Minor), NOT FOUND = 4 (Info, TO BE/конфиг), UNVERIFIABLE = 2 (Info).

---

## 10. Рекомендуемые действия

1. **(Minor, closable)** Уточнить формулировку §4.2.3 «Откат»: FK `operation.bph_id → bph.id` в DDL **не объявлен** (в `20241029_SIHIST-2774_7_create_operation.xml` есть только FK на `info` и `status_to_operation`). Порядок удаления `status_to_operation`/`info` → `operation` → `bph` остаётся верным, но обоснование стоит строить на отсутствии зависимости, а не на «обратном FK». → кандидат для `resolve-code-alignment`.

2. **(Info, не требует правки)** Зафиксировать в spec, что `updateDelayMs` — внешняя конфигурация (в репозитории отсутствует), значение задаётся средой; при необходимости — `[GAP-...]`.

3. **(Info, ожидаемо)** `MOEX_TAX`, INSERT-строки и changeset фичи — NOT FOUND как плановые артефакты; появятся при реализации. Не блокируют.

4. **(Info)** Перепроверить `BphConverter.getTypesMap()` и `PortfolioOperationType` (генерируется из OpenAPI `x-class`) отдельным проходом, если требуется строгая верификация §4.2.2.

**Closable для `resolve-code-alignment`:** пункт 1 (Minor уточнение формулировки отката). Пункты 2–4 — informational.

---

## 11. Пропущено в этом прогоне

- `BphConverter.java`, `Operation.java` (модель), `PortfolioOperationType` — генерация из OpenAPI не читалась (см. §3.6).
- `grpc.auth.*` конфигурация Sber Auth `getSession` — вне scope.
- `db-export/БД ИО.md` — использован косвенно (значения prod max из spec §4.2.3 Pre-checks), строки не перечитаны.
- `analytics/` — по правилам не источник истины для check-feature-code.

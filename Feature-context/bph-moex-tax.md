# Контекст для фичи: налог MOEX_TAX из BPH

## Задача (бриф)

> В интеграции `history-ops` ↔ BPH по `GET_OPERATIONS_WITH_DETAILS` нужно
> добавить обработку нового налога: BPH присылает `type = TAXES`,
> `subtype = MOEX_TAX` (новый подтип). В Java операция маппится в **тот же
> исходящий объект**, что и обычный налог (`operation_type = tax`), отличие —
> **другой `comment`**, который берётся из таблицы `info` по `additionalType`.
> Логика обработки идентична существующим налогам `TAX_RETAIN`; изменения
> **data-driven через БД**, без правок Java-кода.

Трактовка: новый BPH subtype семейства `TAXES` маппится в существующий
`operation_type = tax`, а специфика (текст для UI) задаётся строкой в таблице
`info` по `additional_type`. Механика — как у `TAX_RETAIN`
(`db-export/БД ИО.md:425,1692`), добавление — INSERT в таблицы маппинга БД HO.

Subtype `MOEX_TAX` в текущих выгрузках и репозитории **не найден** (см. Q-01):
есть только `TAX_RETAIN`, `TAX_REFUND_BROK_ACCOUNT` (`db-export/БД ИО.md:425,428`).

## Затронутые области

| Область | Что затрагивается | Документы / код |
|---|---|---|
| БД маппинга HO | Новый `bph.subtype` (family `TAXES`), запись `operation`, строка `info`, связка `status_to_operation` | `db-export/БД ИО.md`; DDL `history-ops/liquibase/changesets/20241029_SIHIST-2774_3_create_info.xml` |
| Запрос к BPH | Новый subtype автоматически попадёт в `subtypesAndStatuses` при `operationTypes` содержит `tax` | `BphBcFilterService.buildBphRequestEntityByBphParams()` |
| Обработка ответа BPH | Матч `type+bphSubtype` → `operation` (только `bphActive`), затем `additionalType` → `info.comment`; `TAXES`+пустой comment → fallback `accComment` | `BphCommonClientConverter.getAdditionalInfoFromCache()/isCorrectAdditionalType()/getOperationFromCache()` |
| Исходящий ответ | `type` из кэша (`tax`), `comment` из `info`, `id = bph_tax_<externalSystemId>` | `BphCommonClientConverter.convert()/getId()` |
| Композит / МП | Без изменений — деталка `HISTORY_OPS_TAX_DETAILS_SCREEN`, заголовок «Удержание налога» | `HistoryOperationTaxDetailsScreen.java`, `HistoryOperationTaxDetailsHeaderSection.java` |
| Java history-ops | **Не меняется** (по брифу; проверить Q-05 — влияние на `additionalType=NULL`) | — |
| Тесты | `operation-cache` fixture, JSON ответа BPH | `src/test/resources/application-test.yml:125` |

## Релевантная аналитика

| Документ | Что описывает | Почему релевантно |
|---|---|---|
| `analytics/02-Modules/MOD-001-history-ops/behavior/operation-type-catalog.md:141-149` | § «Удержание налогов из BPH (3321)»: `TAXES/TAX_RETAIN` → `tax`, additionalTypes `OUT_MONEY/OUT_SECURITIES/TAX_PERIOD_END/INCENTIVE_PAYMENT`; правило `comment = info.comment` по additionalType | Прямой аналог маппинга |
| `analytics/02-Modules/MOD-001-history-ops/behavior/bph-response-processing.md` | Фазы обработки ответа: запрос из кэша, `BphBcFilterService`-фильтрация, watershed, матч `additionalType`, маппинг в `operation_type`, comment/logo из `info` | Алгоритм, в который встраивается новый subtype |
| `analytics/02-Modules/MOD-001-history-ops/data/bc-bph-mapping-db.md` | ER-схема и атрибуты `info(operation_id, additional_type, comment, …)`, `bph(subtype, type_id, is_active)`, `operation(operation_type_id, bc_id, bph_id)`; gap G-032-03 «новый subtype = DBA insert + cron, не Java deploy» | Обоснование data-driven изменения |
| `analytics/02-Modules/MOD-001-history-ops/integrations/bph.md` | Контракт `GET_OPERATIONS_WITH_DETAILS`: запрос (`subtypesAndStatuses[].{type,subtype,statuses}`), ответ (`lead.{type,subtype,additionalType,status,totalPrice,…}`) | Контракт обмена |
| `analytics/02-Modules/MOD-001-history-ops/integrations/feature-toggle.md` | Feature toggles интеграции BPH | Влияние на обработку налога |
| Контекст-док `Feature-context/bph-portfolio-size-tax.md` | Соседняя фича (`TAXES/PORTFOLIO_SIZE_TAX`); документирует весь паттерн «TAXES/subtype → tax», закрытые Q-01…Q-10, ссылается на `MOEX_TAX` как образец | Ближайший прецедент, тот же паттерн |

## Релевантный код

| Файл : якорь | Компонент | Текущее поведение | Почему важно |
|---|---|---|---|
| `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/service/conversion/BphCommonClientConverter.java:40` | константа `private static final String TAXES = "TAXES";` | **Хардкод** строки `TAXES` в Java | Ключевой факт для проверки тезиса «без правок Java» (Q-05) |
| `.../BphCommonClientConverter.java:121-137` | `convert()`: comment-enrichment | `getAdditionalInfoFromCache()` → `enrichComment(...info.comment)`; fallback: если `TAXES.equals(bphType)` и comment пуст → `lead.setComment(operation.accComment())` | Место, где формируется `comment` налога |
| `.../BphCommonClientConverter.java:220-262` | `getAdditionalInfoFromCache()`, `isCorrectAdditionalType()`, `getOperationFromCache()` | `info`-строка выбирается по `info.additional_type == operation.additionalType` (null → `""`); `operation` ищется по `bphType+bphSubtype` и `bphActive` | **Механизм «comment из info по additionalType»**: новый `additionalType` подхватывается без кода |
| `.../BphCommonClientConverter.java:168-189` | `getId()` | `"bph_%s_%s".formatted(operationType.getValue(), externalSystemId)` → `bph_tax_<id>` | Формат id во фронте |
| `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/adapter/bph/BphConverter.java:52-77,141-152` | `getTypesMap()/deserializeType()` | `operation_type` берётся **из кэша БД** (`operationsMap` → `PortfolioOperationType.fromValue(operationsKey)`), ключ = `type|subtype` | Маппинг BPH→`tax` **data-driven**, не хардкодится |
| `.../service/filter/BphBcFilterService.java:102-121` | `buildBphRequestEntityByBphParams()` | Собирает `type`,`subtype`,`statuses`,`additionalTypes` (только non-null из `info`) в запрос BPH | Новый subtype попадёт в запрос автоматически после INSERT |
| `.../service/filter/BphBcFilterService.java:161-250` | `isActualBphOperation()` | Ранний `return true`, если у `operation` только BPH- либо только BC-контекст (нет обеих сторон); при `bc_id=NULL` watershed/additionalType/лог+метрика **не выполняются** | Для `bc_id=NULL` (как у соседа) ветка «только BPH» пропускает доп. проверки; статус проверяется отдельно в `isBphCommonOperation` (см. ниже) |
| `.../service/filter/BphBcFilterService.java:69-86` | `isBphCommonOperation()/isCommonOperationByBphContext()` | `cacheOperation.bphActive() && bphType==bphType && bphSubType==bphSubtype && statusMap.containsKey(status)` | Статус-членство проверяется **всегда**; нужна строка `status_to_operation` для статуса, приходящего от BPH |
| `.../model/Operation.java` (record) | `hasBphContext()`, `concatTypeAndSubtype()`, `toOperationTypeEnum()` | `hasBphContext = bphActive && type != null && statusAndGeneralStatus != null`; ключ = `type|bphSubtype` | Условие включения в запрос и ключ водораздела |
| `.../model/AdditionalInfo.java` | поля `additionalType`, `comment`, `displayedName`, `logoUrl` (`@JsonProperty`) | JSON-ключи `additional_type`, `comment`, `logo_url`, `displayed_name` | Структура строки `info` в кэше |
| `.../resources/db/find_all_operations_v2.sql` | сборка `info` json-массива и `operation_type` из БД | `'additional_type', i.additional_type`, `'comment', i.comment`; `bc_active=false` при `bc_id IS NULL` | SQL-источник кэша — подтверждает data-driven маппинг |
| `repositories/ИО/history-ops/src/main/swagger/bph/bph.yml:216` | `POST /api/v1/incoming-gateway/operations-with-details` | Endpoint `GET_OPERATIONS_WITH_DETAILS` | Точка интеграции |
| `.../bph.yml:1093-1100` | `OperationData` | `type`, `subType`, `subtype`, `additionalType` (example `SPEC_SWAP`), `formationDate`, `eventDate`, `externalSystemId`, `totalPrice`, `status`, `agreement` | Поля ответа BPH для налога |
| `.../bph.yml:1292-1326` | `subtypesAndStatuses[]` | `{type, subtype, additionalTypes[], statuses[]}`; `required: [type, subtype, statuses]` | Формат запроса к BPH |
| `repositories/ИО/history-ops-screen-api/.../models/OperationTypeNameResolver.java:26` | `case TAX -> "Налог";` | Отображение типа `tax` в UI | UI-имя типа |
| `.../composite/screens/details/HistoryOperationTaxDetailsScreen.java:10` | `@Screen(bindWithScreenCode = "HISTORY_OPS_TAX_DETAILS_SCREEN")` | Деталка налога, `enrichScreenData` — no-op | UI не меняется |
| `.../composite/sections/details/tax/HistoryOperationTaxDetailsHeaderSection.java` | `defaultTitleName("Удержание налога")`, `ScreenDetailsHeaderSection.TAX` | Заголовок деталки без различия по subtype | Новый налог получит тот же заголовок (см. Q-06) |
| `.../composite/sections/details/tax/HistoryOperationTaxDetailsOperationParametersSection.java` | `Section(bindWithSectionCode = "HISTORY_OPS_TAX_DETAILS_OPERATION_PARAMETERS_SECTION")` | Секция параметров налога | UI не меняется |
| `repositories/ИО/history-ops/src/test/resources/application-test.yml:125` | `operation-cache.default-value` | JSON-массив `Operation`; строка `tax`/`TAX_RETAIN`/`TAXES`/`bph_active=true`/`COMPLETE→executed`/`info` c additionalTypes | Образец test-fixture для нового subtype |

> `PortfolioOperationType` (enum с `tax`/`tax_input`) — импортируется из
> `com.sberbank.si20.history.ops.api.ws`, но **файла в репозитории нет**
> (генерённый модуль, см. Q-07). Значения `tax` подтверждены через
> `create_schema.sql:170` и `OperationTypeNameResolver.java:26`.

## Данные (БД, выгрузки)

| Таблица / поле : якорь | Текущее устройство | На что влияет фича |
|---|---|---|
| `history_ops.type` id=7 `TAXES` — `db-export/БД ИО.md:319,1525` | Семейство налогов | Новый subtype ссылается на `type_id=7` |
| `history_ops.operation_type` id=2 `tax`, id=20 `tax_input` — `db-export/БД ИО.md:326,344` | Фронтовый тип операции | Новый налог → `operation_type_id=2 (tax)` |
| `history_ops.bph` id=19 `TAX_RETAIN` (type_id=7, active), id=20 `TAX_REFUND_BROK_ACCOUNT` (type_id=7, active) — `db-export/БД ИО.md:425,428,1655-1656`; DDL `.../20241029_SIHIST-2774_2_create_bph.xml` | Существующие subtypes `TAXES` | **INSERT** новой строки `subtype='MOEX_TAX', type_id=7, is_active=true` |
| `history_ops.operation` id=2 → `operation_type_id=2 (tax)`, `bc_id=110 (TAX_WITHHOLDING)`, `bph_id=19`, name «Удержание суммы налога»; id=23 → `operation_type_id=20 (tax_input)`, `bc_id=NULL`, `bph_id=20` — `db-export/БД ИО.md:476-477,1692,1713` | Записи операций налога | **INSERT** нового `operation` (новый `bph_id`), при желании `bc_id=110` или `NULL` (Q-04) |
| `history_ops.info` operation_id=2: `OUT_MONEY/OUT_SECURITIES/TAX_PERIOD_END/INCENTIVE_PAYMENT` с русскими комментариями; id=49 operation_id=23 `additional_type=NULL`, comment «Возврат излишне удержанного налога» — `db-export/БД ИО.md:527-531`; DDL `.../20241029_SIHIST-2774_3_create_info.xml` | Комментарии для UI по `additional_type` | **INSERT** строки `info` с `additional_type=<значение MOEX>` и `comment=<текст>` |
| `history_ops.status` id=19 `COMPLETE` → `general_status_id=1 (executed)` — `create_schema.sql:120,607-608` | Статус налога | Переиспользовать `COMPLETE` (Q-03) |
| `history_ops.status_to_operation`: operation_id=2 ↔ status_id=19 — `db-export/БД ИО.md:586` | Связка «операция ↔ статус» | **INSERT** связки для новой `operation` (иначе `statusMap.containsKey(status)` не пройдёт) |
| Кэш `app-config.operation-cache` — `application-test.yml:125` | JSON-массив `Operation`, строка `tax`/`TAX_RETAIN` с `info[]` | Обновить fixture под `MOEX_TAX` |
| `databasechangelog`: `20250606_SIHIST-3321_added_tax_data.sql`, `20250611_SIHIST-3321_modify_type.sql`, `20251030_include-tax.sql` — `db-export/БД ИО.md` | Прецедент Liquibase-миграции налогов | Образец оформления changeset для нового subtype |
| Changelog репозитория (`user_data-history_ops-changelog.xml`) | `<includeAll path="changesets">` | Changesets живут в `history-ops/liquibase/changesets/`; SIHIST-3321 там **не найден** — вероятно проливался вне репо (Q-08) |

**Подтверждено:** `MOEX_TAX` отсутствует в `repositories/`, `db-export/`,
`analytics/` (единственные совпадения `MOEX_TAX` — в правилах
`.qwen/rules/traceability.md:40` и в контекст-доке соседа `bph-portfolio-size-tax.md`).

## Интеграции и контракты

- Обмен: BPH `GET_OPERATIONS_WITH_DETAILS` — `POST /api/v1/incoming-gateway/operations-with-details` (`bph.yml:216`), заголовки `rqUID`, `systemName=si2-ops`.
- Вход от BPH (`OperationData`, `bph.yml:1093-1100`): `type=TAXES`, `subtype=MOEX_TAX`, `additionalType=<значение>`, `status`, `totalPrice`, `formationDate`, `eventDate`, `externalSystemId`, `agreement`.
- Запрос к BPH (`subtypesAndStatuses[]`, `bph.yml:1292-1326`): `{type, subtype, additionalTypes[], statuses[]}`, `required: [type, subtype, statuses]`; `additionalTypes` заполняется из `info.additional_type` (`BphBcFilterService.buildBphRequestEntityByBphParams`).
- Исходящий объект: `type = tax` (из кэша БД), `comment` из `info` по `additionalType`, `id = bph_tax_<externalSystemId>` (`BphCommonClientConverter.getId`).
- Фронтовый enum `PortfolioOperationType` уже содержит `tax` — новый тип вводить не нужно.

## Ограничения и риски текущего состояния

- **Без строки `info` с корректным `additional_type`** comment не подберётся:
  `isCorrectAdditionalType` сравнивает `info.additional_type` с
  `operation.additionalType` (null → `""`), и при несовпадении `info`-строка не
  найдена → comment остаётся пустым (для `TAXES` сработает fallback `accComment`).
- **Константа `TAXES` хардкодится в Java** (`BphCommonClientConverter.java:40`).
  Для налога с `type=TAXES` это лишь включает fallback `accComment` — сам
  маппинг `type+subtype → operation_type` и выбор `comment` по `additionalType`
  **data-driven** (`BphConverter.getTypesMap`, `isCorrectAdditionalType`). Тезис
  «без правок Java» держится при условии, что `type=TAXES` (Q-05).
- **Один `operation` в кэше = одна пара `bph.type+bph.subtype`**: для нового
  subtype нужна **отдельная** строка `operation`, даже при том же
  `operation_type=tax`.
- **Статус-членство проверяется всегда** (`isBphCommonOperation` →
  `statusMap.containsKey(status)`), независимо от `bc_id`. Нужна строка
  `status_to_operation` для фактического статуса BPH (вероятно `COMPLETE`).
- **`bc_id=NULL`**: при отсутствии BC-аналога `isActualBphOperation()` возвращает
  `true` досрочно (только BPH-контекст) — watershed по `additionalType` и
  лог+метрика `unexpected_additional_type_for_common_operation` не выполняются.
  Поведение подтверждено соседним `bph-portfolio-size-tax-code-alignment.md:29-36`
  (A-03 CONFIRMED). Если же у `MOEX_TAX` будет `bc_id=110` (обе стороны) — ветка
  иная, и `additionalType` обязан совпасть с `info`.
- **Watershed** (`BphDynamicConfig.getStartDateWithDB()`, ключ `type|subtype`):
  при наличии BPH- и BC-контекста одновременно требует согласованного
  `historyStart`; при `bc_id=NULL` не применяется.
- **UI-заголовок** налога не различается по subtype («Удержание налога»,
  `HistoryOperationTaxDetailsHeaderSection`) — если для `MOEX_TAX` нужен иной
  заголовок, потребуются правки Java (Q-06).

## Что учесть при написании фичи

- Следовать паттерну SIHIST-3321 / `TAX_RETAIN`: «BPH type / subtype / additionalType / operation_type / comment».
- Зафиксировать scope = Liquibase INSERT + пролив на стенды + тесты; **Java-код не меняется** (проверить Q-05/Q-06).
- Описать INSERT в `bph` (новый subtype, `type_id=7`, `is_active=true`), `operation` (`operation_type_id=2`, новый `bph_id`, `bc_id` по Q-04), `info` (`additional_type` + `comment`), `status_to_operation`.
- Указать, сколько строк `info` нужно (одна — как `TAX_REFUND_BROK_ACCOUNT`, или несколько по `additional_type` — как `TAX_RETAIN`).
- Проверить занятость id: prod max `bph=24`, `operation=26`, `info=78`, `status_to_operation=56` (`db-export/БД ИО.md`).
- Обновить test fixtures: `application-test.yml:125` (operation-cache), JSON ответа BPH.
- Negative-сценарий: неизвестный/отсутствующий `additional_type` → comment не подставляется (fallback `accComment` для `TAXES`).
- Композит/МП — вероятно out of scope (тот же `tax`, та же деталка) — согласовать (Q-06).
- Согласовать источник comment: `info.comment` после водораздела, `accComment` — fallback (правило SIHIST-3476, по аналогии с налогами).

### Актуализация после resolve (2026-09-12)

Решения из resolve, которые писатель и ревьюер должны считать актуальнее исходного current-state:

- GAP-GOAL-01: Статус BPH `COMPLETE` → `executed`; строка `status_to_operation` (`status_id=19`), набор как у `TAX_RETAIN` (D-05)
- GAP-UCAS-03: То же (D-05)
- GAP-UCTB-04: То же (D-05)
- GAP-CONS-01: Тип/статус-связка подтверждены решением (D-05)
- GAP-INT-13: Контракт статуса подтверждён (D-05)
- GAP-ALG-01: Шаг 3: статус `COMPLETE` имеет строку `status_to_operation` (`status_id=19`) (D-05)
- GAP-DM-01: `status_and_general_status = {"COMPLETE": "executed"}`; `status_to_operation` `status_id=19` (D-05)
- GAP-MAP-04: Допущение статуса подтверждено решением (D-05)
- GAP-MIG-05: Pre-checks/Validation: статус BPH `COMPLETE`, строка `status_to_operation` `status_id=19` (D-05)
- GAP-NFR-REL-03: Статус-членство подтверждено: для `MOEX_TAX` заведён `COMPLETE` (D-05)
- GAP-GOAL-03: Налог `MOEX_TAX` не влияет на агрегацию/Total-секции — отдельный учёт (D-06)
- GAP-UCAS-04: То же (D-06)
- GAP-UCTB-06: То же (D-06); зафиксировано в постусловии UC
- GAP-CONS-05: То же (D-06)
- GAP-ALG-04: То же (D-06)
- GAP-DM-06: То же (D-06)
- GAP-MAP-01: `operation.name` = «Удержание суммы налога» (D-07)
- GAP-MAP-02: `info.comment` = «биржевой налог» для всех `additional_type` (D-07)
- GAP-MAP-03: Фактический `additionalType` = набор `TAX_RETAIN` (D-08)
- GAP-MAP-05: `type` строго `TAXES`, Java не меняется (D-12)
- CH-01: C
- CH-02: A
- CH-03: A
- CH-08: A (уточнено)
- CH-10: B
- CH-11: A
- CH-13: Уточнено (не A)
- CH-14: B
- CH-15: A
- CH-18: A
- CH-19: A
- CH-20: A
- CH-21: Штатный порядок
- CH-22: A
- CH-23: Штатный порядок
- CH-24: A
- CH-04: Major
- CH-05: Minor
- CH-06: Major
- CH-07: Major

**Якоря полей из актуальной SPEC:**

`GET_OPERATIONS_WITH_DETAILS`, `comment`, `DECISIONS`, `MOEX_TAX`, `TAX_RETAIN`, `additionalType`, `OUT_MONEY`, `OUT_SECURITIES`, `TAX_PERIOD_END`, `INCENTIVE_PAYMENT`, `info`, `additional_type`

См. также § «Закрытые вопросы» ниже — не переспрашивать закрытые Q.
## Открытые вопросы

| ID | Вопрос | Где искать ответ |
|---|---|---|
| Q-01 | Точный BPH subtype: `MOEX_TAX`? В `repositories/`, `db-export/`, `analytics/` не найден. Известные subtypes `TAXES`: `TAX_RETAIN`, `TAX_REFUND_BROK_ACCOUNT` | Контракт BPH (`bph.yml`/конфиг BPH), PO / бизнес-аналитик, Jira |
| Q-02 | Значение `additionalType`, присылаемое BPH для `MOEX_TAX` (и будет ли оно непустым) | Контракт BPH; команда BPH |
| Q-03 | Статус BPH для `MOEX_TAX` — `COMPLETE` (→ `executed`)? Нужна ли строка `status_to_operation` | Контракт BPH; аналог SIHIST-3321 |
| Q-04 | `bc_id`: `110 (TAX_WITHHOLDING)` как у `tax`-`TAX_RETAIN`, или `NULL` (только BPH)? Влияет на ветку `isActualBphOperation()` | Контракт BC; PO; аналог SIHIST-3321 / сосед `bph-portfolio-size-tax` (там `bc_id=NULL`) |
| Q-05 | Держится ли «без правок Java»: значение `type` строго `TAXES` (константа `BphCommonClientConverter.java:40`)? Иначе fallback `accComment` не сработает | Контракт BPH (`type` в ответе) |
| Q-06 | Текст `comment` для UI и нужен ли отдельный заголовок деталки (сейчас `HistoryOperationTaxDetailsHeaderSection` = «Удержание налога» для всех налогов) | PO / бизнес-аналитик; Figma |
| Q-07 | `PortfolioOperationType` — где определён (файл в репо отсутствует, импорт из `api/ws`); подтвердить наличие `tax` | Генерённый модуль/артефакт сборки; `history.yml` (по соседу — `tax`@71, `tax_input`@93) |
| Q-08 | Откуда проливается изменения маппинга: changesets `SIHIST-3321` в репо **не найдены** (в `db-export` есть `databasechangelog`), хотя changelog = `<includeAll path="changesets">` | Сопровождение БД HO; каталог `history-ops/liquibase/changesets/`; пролив на стендах |
| Q-09 | Есть ли BC-аналог/`historyStart`-водораздел для `MOEX_TAX` (при наличии обеих сторон) | `bph_dynamic` config; команда BPH/сопровождения |
| Q-10 | Влияет ли новый налог на агрегацию/итоги (`Total`-секции) в деталке и ленте | Аналитика `TotalSumUtils`; PO |
| Q-16 | Поддерживать ли для `MOEX_TAX` статусы, отличные от `COMPLETE` (`CANCELLED`/`REJECTED`/`NOT_COMPLETED`/`DELETE`) — нужны ли строки `status_to_operation` | Команда BPH / PO; контракт BPH |
| Q-17 | Поведение HO при response headers `GET_OPERATIONS_WITH_DETAILS`, не объявленных в контракте BPH | Контракт BPH; команда BPH |
| Q-18 | Какое поле несёт подтип в ответе BPH: `subType` или `subtype` (`OperationData`, `bph.yml:1094-1100`) | Контракт BPH; фактический ответ BPH |
| Q-19 | Поведение при кодах `401`/`403`/`429` (rate-limit), не описанных в контракте BPH | Команда BPH / сопровождение |

## Закрытые вопросы

| ID | Дата | Решение | Где в spec | Источник |
|----|------|---------|------------|----------|
| Q-03 | 2026-09-12 | Статус BPH `COMPLETE` → general_status `executed`; строка `status_to_operation` новой operation ↔ `status_id=19`, набор статусов как у `TAX_RETAIN` | §2 (CN-10), §4.1.1, §4.2.2 (шаг 3), §4.2.3, §7.2 | DECISIONS D-05 |
| Q-10 | 2026-09-12 | Налог `MOEX_TAX` **не влияет** на агрегацию и итоговые (Total-) секции — ведётся отдельный учёт; отдельные правила агрегации для него | §1.1 (BR-10), §1.3 (постусловие «Успех») | DECISIONS D-06 |
| Q-01 | 2026-09-12 | Подтверждён subtype `MOEX_TAX` (набор `additionalType` как у `TAX_RETAIN`); незарегистрированный subtype семейства `TAXES` не отображается, отдельный лог/метрика не требуются | §1.1 (BR-02…BR-05), §1.3 (alt 6c.3), §4.1.1, §4.2.2 (шаг 4) | DECISIONS D-01, D-09 |
| Q-02 | 2026-09-12 | Фактический `additionalType` от BPH совпадает с набором `TAX_RETAIN` (`OUT_MONEY`, `OUT_SECURITIES`, `TAX_PERIOD_END`, `INCENTIVE_PAYMENT`) | §4.2.3 (validation, risks), §4.2.3-migration | DECISIONS D-08 |
| Q-05 | 2026-09-12 | `type` в ответе BPH строго `TAXES`, Java-код не меняется | §2 (CN-06, CN-07), §4.2.2 (шаг 6), §4.2.3 (маппинг) | DECISIONS D-12 |
| Q-06 | 2026-09-12 | `info.comment` = «биржевой налог» для всех значений `additional_type`; `operation.name` = «Удержание суммы налога»; заголовок деталки «Удержание налога» сохраняется | §1.2, §1.3, §2, §4.1.1, §4.2.2, §4.2.3 (модель и маппинг) | DECISIONS D-07 |
| Q-07 | 2026-09-12 | Значение `tax` в `PortfolioOperationType` подтверждено (`create_schema.sql:170`, `OperationTypeNameResolver.java:26`, `history.yml:71`) | §1.1 (gaps снят), §1.3 (gaps снят) | DECISIONS D-10 |
| Q-08 | 2026-09-12 | Пролив изменения маппинга — штатным Liquibase changeset в `history-ops/liquibase/changesets/`; каталог прошлого пролива `SIHIST-3321` уточняется у сопровождения | §2, §4.2.3-migration (среды) | DECISIONS D-13, D-04 |
| Q-09 | 2026-09-12 | BC-аналога для `MOEX_TAX` нет, `bc_id=NULL`, водораздел `historyStart` не применяется | §1.3 (gaps снят), §2 (CN-09), §4.2.3 (модель) | DECISIONS D-11 |
| Q-11 | 2026-09-12 | Отдельных SLO/числовых нагрузочных целей нет — обработка `MOEX_TAX` идёт в тех же лимитах history-ops, что и соседние BPH-налоги | §7 (Performance), §7 (Reliability, SLO) | DECISIONS D-14 |
| Q-12 | 2026-09-12 | Поведение при сбое BPH как у существующих налогов — без спец. retry, при недоступности пустой/частичный ответ; идемпотентность changeset штатная (`preConditions`/`MARK_RAN`) | §7 (Reliability, Graceful Degradation), §4.2.3-migration | DECISIONS D-15 |
| Q-13 | 2026-09-12 | Новых требований ИБ нет — каналы/доступ как у существующих налогов; PII в новых строках (`bph.subtype`, `info.comment`) отсутствует | §7 (Security), §4.1.2 (контракт) | DECISIONS D-16 |
| Q-14 | 2026-09-12 | Отдельных тоглов/настроек не вводится — налог работает как остальные, релевантен только существующий `enableServiceBPH` | §7 (Configuration), §7 (Toggles) | DECISIONS D-17 |
| Q-15 | 2026-09-12 | Новых логов/метрик не вводится — используются существующие (`eventType`, `history_ops_*`); допущения по миграции/целям/границам принимаются «как у существующих налогов» | §7 (Logging, Metrics), §4.2.3-migration, §1.1, §1.3, §2 | DECISIONS D-18 |
| Q-16 | 2026-09-12 | Для `MOEX_TAX` поддерживается только статус `COMPLETE` — новых строк `status_to_operation` не требуется; иные статусы не заявляются | §4.2.3 (маппинг, допущение по набору статусов) | DECISIONS D-19 |
| Q-17 | 2026-09-12 | HO не завязывается на response headers `GET_OPERATIONS_WITH_DETAILS` — обработка опирается только на тело ответа, текущее поведение сохраняется | §4.1.1 (Response headers) | DECISIONS D-20 |
| Q-18 | 2026-09-12 | Разбор подтипа идёт по `subtype` (текущая реализация); `subType` не используется, дополнительных действий нет | §4.1.1 (Response body: `subType`, примечание) | DECISIONS D-21 |
| Q-19 | 2026-09-12 | Для не описанных в контракте кодов `401`/`403`/`429` — штатная обработка ошибок транспорта, как у существующих интеграций; спец. логика (retry для `429`) не вводится | §4.1.1 (Коды ошибок) | DECISIONS D-22 |
| Q-20 | 2026-09-12 | BR-10 снимается как неприменимый к текущему объёму — правило удалено из spec; отдельного учёта `MOEX_TAX` в этой фиче нет | §1.1 (BR-10 удалён) | /resolve-challenges (CH-01), DECISIONS D-23 |
| Q-21 | 2026-09-12 | Sequence у таблиц `bph`/`operation`/`info`/`status_to_operation` есть (SERIAL подтверждён); changeset обязан вызвать `setval` после ручного задания `id` — **снято решением D-39 (см. запись Q-21 ниже)** | §4.2.3 (Migration, CS5, setval) | /resolve-challenges (CH-14), DECISIONS D-24 |
| Q-21 | 2026-09-12 | Штатный для history-ops способ задания `id` — **ручное назначение** из конфига (`${moexTax.*}`) + pre-check `SELECT max(id)`; продуктовые DDL объявляют `id INT PK` **без** `SERIAL`, sequence не создаётся → CS5 `setval` и утверждения о `SERIAL`/`<table>_id_seq` из spec убраны. Прежнее D-24 (`setval`) снято | §4.2.3 (модель, «Занятые id в проде», migration: CS5/SQL-эквивалент), риск-таблица | DECISIONS D-39 |
| Q-27 | 2026-09-12 | При `totalPrice = null` операция `MOEX_TAX` **не отбрасывается** — показывается с `lead.total_sum = null` (как у `TAX_RETAIN`), по факту `BphCommonClientConverter.convert()`; прежнее D-30 (отбрасывание) признано недействительным. Зафиксировано ограничением CN-16 | §1.3 (постусловие, шаг 1), §2 (CN-16), §4.1.1 (`totalPrice`, `lead.total_sum`) | DECISIONS D-40 |
| Q-22 | 2026-09-12 | `externalSystemId` глобально уникален между налогами → коллизии `lead.id = bph_tax_<externalSystemId>` между `TAX_RETAIN` и `MOEX_TAX` нет | §4.1.1 (`lead.id`), §4.2.3 (сравнение с `TAX_RETAIN`) | /resolve-challenges (CH-18), DECISIONS D-25 |
| Q-23 | 2026-09-12 | Окно рассинхрона кэша (`updateDelayMs`) мало/приемлемо, поведение как у существующих налогов; значение `updateDelayMs` — конфигурируемое/instance-specific (`OperationCacheLoaderProperties.java:7-8`), конкретное число в spec не фиксируется | CN-08, §4.2.3 (кэш) | /resolve-challenges (CH-19), DECISIONS D-26 |
| Q-24 | 2026-09-12 | Формулировка alt 6a/6b исправлена на «fallback → шаг 7»; ветки схлопнуты, цикла нет | §1.3 (alt 6a/6b) | /resolve-challenges (CH-02), DECISIONS D-27 |
| Q-25 | 2026-09-12 | Ветка alt 3a недостижима для `MOEX_TAX` (`bc_id=NULL`) и убрана; условие сохраняется только как регресс-тест | §1.3 (alt 3a), §4.2.2 | /resolve-challenges (CH-03), DECISIONS D-28 |
| Q-26 | 2026-09-12 | Различение `TAX_RETAIN`/`MOEX_TAX` обеспечивается **комментарием** из таблицы `info` по `type`/`subtype`/`additionalType`; отдельный признак/заголовок не вводится | §1.1 (BR-08), §1.3, §4.2.2 (шаг 8) | /resolve-challenges (CH-08), DECISIONS D-29 |
| Q-27 | 2026-09-12 | При `totalPrice = null` операция `MOEX_TAX` отбрасывается (в ленте/деталке не показывается) | §4.1.1 (`lead.total_sum`), §4.2.3 | /resolve-challenges (CH-10), DECISIONS D-30 |
| Q-28 | 2026-09-12 | Комментарий **всегда** берётся из таблицы `info` (по `type`/`subtype`/`additionalType`, с подстановкой параметров); `accComment` — только когда в таблице `null`; пустой комментарий не ожидается; значение для `MOEX_TAX` — «биржевой налог» (D-07) | §1.1 (BR-05/BR-09), §4.1.1, §4.2.2, §4.2.3, §7 | /resolve-challenges (CH-13), DECISIONS D-31, D-07 |
| Q-29 | 2026-09-12 | Rollback ограничен конкретными `${moexTax.*}` id (id-предикат вместо бизнес-предиката) | §4.2.3 (CS1–CS4 rollback, Rollback table) | /resolve-challenges (CH-15), DECISIONS D-32 |
| Q-30 | 2026-09-12 | Кэш читается одним SQL-снапшотом (`find_all_operations_v2.sql`) — «наполовину применённое» состояние не наблюдается | §4.2.3 («Как заполняется кэш») | /resolve-challenges (CH-20), DECISIONS D-33 |
| Q-31 | 2026-09-12 | Набор INSERT делится на changeSet по обычной практике history-ops; спец. требований к атомарности нет, зафиксирован штатный порядок пролива | §4.2.3 (Backfill, порядок пролива) | /resolve-challenges (CH-21), DECISIONS D-34 |
| Q-32 | 2026-09-12 | Детекция отсутствия `MOEX_TAX` не требуется — поведение как у существующих налогов (D-18); разрез метрики по `subtype` не вводится | §4.2.3 (Validation/приёмка) | /resolve-challenges (CH-22), DECISIONS D-35 |
| Q-33 | 2026-09-12 | Отдельный лог/счётчик «статус не сматчен» не вводится — поведение как у существующих налогов (D-09/D-18) | §1.3 (alt 3a/4a), §4.2.2 (таблица развилок) | /resolve-challenges (CH-23), DECISIONS D-36 |
| Q-34 | 2026-09-12 | Приёмка — по общим правилам history-ops; отдельные acceptance-критерии и фикстуры для границ не требуются | §4.2.3 (Validation, Test fixtures) | /resolve-challenges (CH-24), DECISIONS D-37 |
| Q-35 | 2026-09-12 | Как у `TAX_RETAIN` — валюта `totalPrice` не переносится, сумма берётся как есть (без конверсии) | §4.1.1 (`lead.total_sum`), §4.2.3 (сравнение с `TAX_RETAIN`) | /resolve-challenges (CH-11), DECISIONS D-38 |

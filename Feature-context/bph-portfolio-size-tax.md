# Контекст для фичи: налог за размер портфеля из BPH

## Задача (бриф)

> Добавление новой операции из источника БПХ (BPH). Операция **неторговая**
> (non-trading), посвящена **налогу за размер портфеля клиента** с порогом
> **от 5 000 000 ₽**. Налог приходит/взимается **отдельно по каждой операции**
> (не агрегированно).

Трактовка: в интеграции `history-ops` ↔ BPH по `GET_OPERATIONS_WITH_DETAILS`
добавляется новый подтип налоговой операции. Механика аналогична существующим
налогам (`TAX_RETAIN`, `MOEX_TAX`): data-driven через таблицы маппинга БД HO,
без правок Java-кода. Отличие — **новый BPH subtype** (в выгрузках не найден) и
**иной comment** для UI.

Отдельного SIHIST-тикета под «налог за размер портфеля» в `analytics/` **не
найдено** — бриф является первичным источником требования (см. Q-01).

## Затронутые области

| Область | Что затрагивается | Документы / код |
|---|---|---|
| БД маппинга HO | Новый `bph.subtype` (family `TAXES`), запись `operation`, строка `info`, связка `status_to_operation` | `db-export/БД ИО.md`; Liquibase-образец SIHIST-3321 в `create_schema.sql` |
| Запрос к BPH | Включение нового subtype в `subtypesAndStatuses` при `operationTypes` содержит `tax`/`tax_input` | `BphBcFilterService.buildBphRequestEntityByBphParams()` |
| Обработка ответа BPH | Фильтрация по `additionalType`, маппинг `comment`, watershed, статус | `BphBcFilterService.isActualBphOperation()`, `BphCommonClientConverter` |
| Исходящий ответ SEND_OPERATIONS | `type`, `comment`, `total_sum`, `general_status` — как у существующих налогов | SIHIST-3321, SIHIST-2811 |
| МП / композит | Без изменений — уже запрашивает `tax`, деталка `HISTORY_OPS_TAX_DETAILS_SCREEN` | `HistoryOperationTaxDetailsHeaderSection`, `TaxSectionCreator` |
| Java history-ops | **Не меняется** (по аналогии с MOEX_TAX) | — |
| Тесты | Liquibase test DB, фикстура ответа BPH, operation-cache | `application-test.yml`, `json/response/bph/` |

## Релевантная аналитика и спеки

| Документ | Что описывает | Почему релевантно |
|---|---|---|
| [SIHIST-3321](analytics/SIHIST/SIHIST_markdown_back/[SIHIST-3321]_Добавление_списание_налогов_для_типовых_операций_из_BPH.md) | Добавление налогов `TAX_RETAIN`/`TAX_REFUND_BROK_ACCOUNT` из BPH: таблица type/subtype/additionalType, маппинг в `tax`/`tax_input`, UPDATE БД | **Образец фичи** для нового налога |
| [SIHIST-3367](analytics/SIHIST/SIHIST_markdown_back/[SIHIST-3367]_Изменение_логики_обработки_ответа_от_bph_-_GET_OPERATIONS_WITH_DETAILS.md) | Алгоритм фильтрации типовых операций BPH (кэш, `additionalType`, watershed) | Операция включается, если есть в кэше и `additionalType` совпадает с `info` |
| [SIHIST-3476](analytics/SIHIST/SIHIST_markdown_back/[SIHIST-3476]_Технические_задачи_в_7.14.0.md) | Правило comment для налогов: после водораздела comment из `info` по `additional_type`; до — `accComment` | Ключевое правило comment для налогов |
| [SIHIST-2774](analytics/SIHIST/SIHIST_markdown_back/[SIHIST-2774]_База_данных_маппинга_простых_операций_из_BC_и_операций_из_BPH.md) | Схема таблиц `bph`, `operation`, `info`, `status_to_operation` | Куда добавлять новый subtype |
| [SIHIST-2796](analytics/SIHIST/SIHIST_markdown_back/[SIHIST-2796]_Формирование_запросов_к_BC_и_BPH_с_учётом_данных_из_БД.md) | Формирование запроса к BPH из кэша маппинга | Запрос строится автоматически при `bph_active=true` |
| [SIHIST-2811](analytics/SIHIST/SIHIST_markdown_back/[SIHIST-2811]_Обработка_ответов_от_BC_и_BPH_с_учётом_данных_из_БД.md) | Маппинг ответа BPH → SEND_OPERATIONS | Правила полей (`comment`, `total_sum`, `type`) |
| SPEC `bph-moex-tax` (Feature-writing/bph-moex-tax/) | Ближайший аналог: `TAXES/MOEX_TAX` → `tax`, `bc_id=110`, `additionalType=NULL`, comment из `info` | Паттерн «TAXES / subtype → tax» для нового налога |

## Релевантный код

| Файл | Компонент | Текущее поведение | Почему важно |
|---|---|---|---|
| `.../service/filter/BphBcFilterService.java:102-121` | `buildBphRequestEntityByBphParams()` | Собирает `type`, `subtype`, `statuses`, `additionalTypes` (только non-null из `info`) в запрос BPH | Новый subtype автоматически попадёт в запрос после INSERT в БД |
| `.../service/filter/BphBcFilterService.java:166-250` | `isActualBphOperation()` | Проверяет watershed (`formationDate` vs `historyStart`), затем `additionalType` ∈ `info.additional_type`; иначе INFO-лог + метрика `unexpected_additional_type_for_common_operation` | Нужна корректная строка в `info` с правильным `additional_type` |
| `.../service/conversion/BphCommonClientConverter.java:40,133-135` | константа `TAXES`, fallback `accComment` | Для `TAXES` при пустом comment из `info` подставляет `details.accComment` | Поведение comment для налогов после/до водораздела |
| `.../service/conversion/BphCommonClientConverter.java:220-262` | `getAdditionalInfoFromCache()`, `isCorrectAdditionalType()`, `getOperationFromCache()` | Матчит `bphType+bphSubtype` → `operation` (только `bphActive`), затем `additionalType` → `info.comment`; `additionalType` и `info.additional_type` сравниваются как `""` при null | Отличие нового налога — другой comment из БД |
| `.../service/conversion/BphCommonClientConverter.java:168-187` | `getId()` | `"bph_%s_%s"` от `operationType` и `externalSystemId` → `bph_tax_{id}` | Формат id на фронте |
| `.../adapter/bph/BphGateway.java:34,149,154` | `BphGateway`, `GET_OPERATIONS_WITH_DETAILS` | Gateway вызова BPH `POST /api/v1/incoming-gateway/operations-with-details` | Точка интеграции, Java не меняется |
| `.../model/Operation.java:11-46` | record `Operation`, `hasBphContext()`, `concatTypeAndSubtype()` | `hasBphContext = bphActive && type != null && statusAndGeneralStatus != null`; ключ watershed = `type\|subtype` | Условие включения в запрос и ключ водораздела |
| `.../adapter/bph/BphDynamicConfig.java:18-19` | `getStartDateWithDB()` | watershed по ключу `concatTypeAndSubtype()` | Для нового subtype нужен `historyStart` (Q-08) |
| `src/main/swagger/bph/bph.yml:216-240` | `POST /api/v1/incoming-gateway/operations-with-details` | Endpoint `GET_OPERATIONS_WITH_DETAILS`; headers `rqUID`,`systemName` required | Контракт BPH |
| `src/main/swagger/bph/bph.yml:1088-1098` | `OperationData` | Поля `type`, `subtype`/`subType`, `additionalType`, `totalPrice`, `formationDate`, `eventDate`, `status`, `agreement` | Ответ BPH для нового налога |
| `src/main/swagger/bph/bph.yml:1292-1326` | `subtypesAndStatuses[]` | `{ type, subtype, additionalTypes[0-1], statuses[1] }`; required `type`,`subtype`,`statuses` | Формат запроса BPH |
| `src/main/swagger/history/history.yml:60-93` | enum `PortfolioOperationType` | Содержит `tax` (71) и `tax_input` (93) | Фронтовый тип операции |
| `history-ops-screen-api/.../HistoryOperationTaxDetailsScreen.java:10` | `@Screen(bindWithScreenCode = "HISTORY_OPS_TAX_DETAILS_SCREEN")` | Деталка налога | UI не меняется |
| `history-ops-screen-api/.../HistoryOperationTaxDetailsHeaderSection.java:30` | `defaultTitleName("Удержание налога")` | Заголовок деталки налога без различия по subtype | UI не меняется |
| `history-ops-screen-api/.../TaxSectionCreator.java:28` | `titleText("Удержание налога")` | Заголовок карточки налога в ленте | UI не меняется |

## Данные (БД, выгрузки)

| Таблица / поле | Где найдено | Текущее устройство | На что влияет фича |
|---|---|---|---|
| `history_ops.type` id=7 | `db-export/БД ИО.md:319` | `TAXES` — семейство налогов | Новый subtype ссылается на `type_id=7` |
| `history_ops.operation_type` id=2 / id=20 | `db-export/БД ИО.md:326,344` | `tax` / `tax_input` | Фронтовый тип для нового налога |
| `history_ops.bph` id=19,20 | `db-export/БД ИО.md:425,428`; `create_schema.sql:592-596` | `TAX_RETAIN`, `TAX_REFUND_BROK_ACCOUNT` (type_id=7, active) | **INSERT** новый subtype (след. свободный id=25, т.к. max=24) |
| `history_ops.operation` id=2,23 | `db-export/БД ИО.md:476,477`; `create_schema.sql:599-604` | id=2 → `operation_type_id=2 (tax)`, `bc_id=110`, `bph_id=19`; id=23 → `operation_type_id=20 (tax_input)`, `bc_id=NULL`, `bph_id=20` | **INSERT** операция (след. свободный id=27, т.к. max=26) |
| `history_ops.info` id=2,46-49 | `db-export/БД ИО.md:527-531`; `create_schema.sql:620-624` | Comment для TAX_RETAIN по `additional_type`: `OUT_MONEY`, `OUT_SECURITIES`, `TAX_PERIOD_END`, `INCENTIVE_PAYMENT`; для TAX_REFUND_BROK_ACCOUNT — `additional_type=NULL` | **INSERT** info с comment для нового налога (след. свободный id=79, т.к. max=78) |
| `history_ops.status` id=19 | `create_schema.sql:607-608`; `db-export/БД ИО.md:375` | `COMPLETE` → `general_status_id=1 (executed)` | Переиспользовать статус `COMPLETE` |
| `history_ops.status_to_operation` id=28 | `create_schema.sql:611-613`; `db-export/БД ИО.md:586` | `operation_id=2 ↔ status_id=19` | **INSERT** связку (след. свободный id=57, т.к. max=56) |
| `history_ops.bph_bc` id=110 | `create_schema.sql:699`; `db-export/БД ИО.md:439` | `TAX_WITHHOLDING` (type_id=8 `MONEY_DIAS`) — BC-аналог налога | `bc_id=110` если у нового налога есть BC-аналог (Q-06) |
| Кэш `app-config.operation-cache` | `application-test.yml:125` | JSON: `TAX_RETAIN` c `bc_code:110`, `bc_active:true`, `status_and_general_status: {COMPLETE:executed}`, `info[]` с `additional_type` | Обновить default-value под новый subtype |

**Новый налог в текущей выгрузке БД отсутствует** — нет ни строки `bph.subtype`,
ни `operation`, ни `info` с комментарием про «размер портфеля».

## Интеграции и контракты

- Обмен: BPH `GET_OPERATIONS_WITH_DETAILS` (`POST /api/v1/incoming-gateway/operations-with-details`, `bph.yml:216`).
- Вход от BPH (lead): `type=TAXES` (уточнить, Q-02), `subtype=<новый>`, `additionalType=<значение|NULL>`, `status=COMPLETE`, `totalPrice`, `formationDate`, `eventDate`, `agreement`, `externalSystemId`.
- Запрос к BPH: `subtypesAndStatuses[]` = `{ type, subtype, additionalTypes[0-1], statuses[] }` (required `type`,`subtype`,`statuses`).
- Исходящий SEND_OPERATIONS: `type` из кэша (`tax`/`tax_input`), `comment` из `info`, `id = bph_<type>_<externalSystemId>`, `general_status=executed`.
- МП/композит передаёт `operationTypes: ["tax", ...]` — изменений на фронте не требуется.
- Фронтовый enum `PortfolioOperationType` уже содержит `tax` и `tax_input` — новый тип вводить не нужно.

## Ограничения и риски текущего состояния

- Без строки `info` с правильным `additional_type` операция **отфильтруется**
  (`unexpected_additional_type_for_common_operation` + INFO-лог).
- Один `operation` в кэше = одна пара `bph.type + bph.subtype`; для нового налога
  нужна **отдельная** запись `operation`, даже при том же `operation_type` (`tax`).
- Алгоритм запроса/ответа **не меняется** — ошибка в данных БД не компенсируется кодом.
- Watershed (`BphDynamicConfig.getStartDateWithDB()`, ключ `type|subtype`): для нового
  subtype нужно согласовать `historyStart`, иначе операции могут не запрашиваться/не
  показываться.
- Правило comment (SIHIST-3476): после водораздела comment из `info` по
  `additional_type`; при пустом comment — fallback `details.accComment`.
- Порог «от 5 млн ₽» — бизнес-условие начисления на стороне BPH, в коде HO фильтра по
  порогу нет (Q-09).

## Что учесть при написании фичи

- Следовать паттерну SIHIST-3321 / MOEX_TAX: таблица «BPH type / subtype / additionalType / operationTypes / comment».
- Зафиксировать, что **Java-код не меняется**; scope = Liquibase + тесты + пролив на стенды.
- Описать INSERT в `bph`, `operation`, `info`, `status_to_operation` (и `status` при необходимости).
- Указать `additionalType` и количество строк `info` (NULL — как MOEX_TAX, или несколько — как TAX_RETAIN).
- Обновить test fixtures: `application-test.yml` (operation-cache), JSON ответа BPH, `bph_request_all_completed.json`.
- Negative-сценарий: неизвестный `additionalType` → операция не попадает в ответ.
- Композит и МП — out of scope (тот же `tax`, та же деталка).
- Связать с SIHIST-3476: comment из `info`, не из `details.accComment`.

## Открытые вопросы / что проверить

| ID | Вопрос | Где искать ответ |
|---|---|---|
| Q-01 | Точное имя BPH subtype для «налог за размер портфеля» (в `analytics/`, `db-export/`, `repositories/` не найдено; для TAXES известны только `TAX_RETAIN`, `TAX_REFUND_BROK_ACCOUNT`, `TAX_RETAIN_REVERSAL`, `TRANSFER_IN`, `TRANSFER_OUT`) | Контракт BPH (`bph_config_*`), PO/бизнес-аналитик; Jira |
| Q-02 | Семейство операции — `TAXES` (type_id=7) или иное? Бриф: «налог» + «неторговая» | Контракт BPH; команда BPH |
| Q-03 | Фронтовый `operation_type` — `tax` (id=2) или `tax_input` (id=20)? «Взимается» → вероятно `tax` | PO; аналог SIHIST-3321 (TAX_RETAIN→tax) |
| Q-04 | `additionalType` в ответе BPH: `NULL` (один comment, как MOEX_TAX/TAX_REFUND_BROK_ACCOUNT) или несколько значений (как TAX_RETAIN — 4 шт.)? | Контракт BPH |
| Q-05 | Текст `comment` для UI нового налога | PO / бизнес-аналитик |
| Q-06 | `bc_id`: `110` (TAX_WITHHOLDING) как у `tax`, или `NULL` (только BPH, как `TAX_REFUND_BROK_ACCOUNT`)? | Контракт BC; аналог SIHIST-3321 |
| Q-07 | Статус BPH — `COMPLETE` (id=19 → `executed`), как у налогов? | Контракт BPH; SIHIST-3321 |
| Q-08 | Watershed `historyStart` для нового subtype (ключ `type|subtype`) | `bph_dynamic` config; команда BPH/сопровождения |
| Q-09 | Порог «от 5 млн ₽» — фильтруется ли на стороне HO или это условие начисления только в BPH? | PO; команда BPH |
| Q-10 | Смысл «отдельно по каждой операции»: нет агрегации/дедупликации? Влияет ли на уникальность `externalSystemId`/id? | PO; SIHIST-3367 (дедупликация) |

## Закрытые вопросы

| ID | Дата | Решение | Где в spec | Источник |
|----|------|---------|------------|----------|
| Q-01 | 2026-08-29 | BPH subtype = `PORTFOLIO_SIZE_TAX` | §1.1, §1.2, §1.3, §4.1.1, §4.2.3 | /resolve-gaps (GAP-GOAL-01, GAP-UCAS-01) |
| Q-02 | 2026-08-29 | Семейство = `TAXES` (type_id=7) | §1.1, §4.1.1, §4.2.3 | /resolve-gaps (GAP-C-01) |
| Q-03 | 2026-08-29 | `operation_type` = `tax` (id=2) | §1.1, §4.1.1, §4.2.3 | /resolve-gaps (GAP-UCTB-01) |
| Q-04 | 2026-08-29 | `additionalType` = `PORTFOLIO_AMOUNT_TAX` (одно непустое) | §4.1.1, §4.2.3 | /resolve-gaps (GAP-UCTB-02, GAP-INT-01) |
| Q-05 | 2026-08-29 | `comment`/`name` = «Налог за размер портфеля» | §4.1.1, §4.2.3 | /resolve-gaps (GAP-GOAL-02) |
| Q-06 | 2026-08-29 | `bc_id` = `NULL` — только BPH, без BC-аналога | §4.2.3 | /resolve-gaps (GAP-C-01) |
| Q-07 | 2026-08-29 | Статус BPH = `COMPLETE` (id=19 → `executed`) | §4.2.3 | /resolve-gaps (GAP-C-01) |
| Q-08 | 2026-08-29 | `historyStart` из ответа BPH `GET_OPERATION_TYPES` (ключ `type\|subtype`), без ручной настройки HO | §2, §4.2.2, §5.4 | /resolve-gaps (GAP-UCTB-03, GAP-C-02, GAP-ALG-01, GAP-NFR-01) |
| Q-08 (уточн.) | 2026-08-29 | Для `bc_id=NULL` `historyStart` **не используется**: `isActualBphOperation()` возвращает `true` досрочно, watershed/additionalType/статус и лог+метрика не выполняются; алерт не требуется | §2 Watershed, §4.2.2.2, §5.4 | /resolve-challenges (CH-01, CH-04) |
| Q-09 | 2026-08-29 | Порог «от 5 млн ₽» — условие начисления на стороне BPH; HO не фильтрует и отображает безусловно; алерт/метрика не требуется | §1.1 BR-02 | /resolve-challenges (CH-08) |
| Q-10 | 2026-08-29 | HO не дедуплицирует типовые операции по `externalSystemId` в одном ответе; дедупликация = торговые + типовые по окну start/end + сверка с кэшем Ignite (по id); уникальность externalSystemId — ответственность BPH | §1.1 BR-03, §4.2.2 | /resolve-challenges (CH-07) |

# Контекст для фичи: bph-moex-tax

## Задача (бриф)

> В интеграции `history-ops` ↔ BPH по `GET_OPERATIONS_WITH_DETAILS` нужно добавить
> обработку нового налога: BPH присылает `type = TAXES`, `subtype = MOEX_TAX` (новый
> подтип). В Java операция маппится в **тот же исходящий объект**, что и обычный налог
> (`operation_type = tax`), отличие — **другой `comment`**, который берётся из таблицы
> `info` по `additionalType`. Логика обработки идентична существующим налогам
> `TAX_RETAIN`; изменения **data-driven через БД**, без правок Java-кода.

**Трактовка.** Новый BPH subtype семейства `TAXES` (`MOEX_TAX`) маппится в уже
существующий фронтовый тип `operation_type = tax` (id=2) — тот же, что у `TAX_RETAIN`.
Отличие от `TAX_RETAIN` — только текст для UI (`comment`), который подставляется из
таблицы `info` по совпадению `additional_type`. Механика полностью переиспользует
data-driven конвейер «таблицы маппинга БД HO → кэш → запрос/обработка BPH», добавление —
INSERT в таблицы `bph`, `operation`, `info`, `status_to_operation` (образец — SIHIST-3321).

Ключевой факт текущего состояния: **subtype `MOEX_TAX` отсутствует** во всех выгрузках
(`db-export/`) и в коде (`repositories/`) — подтверждено grep-поиском. В семействе `TAXES`
сейчас активны только `TAX_RETAIN` и `TAX_REFUND_BROK_ACCOUNT`.

## Затронутые области

| Область | Что затрагивается | Документы / код |
|---|---|---|
| БД маппинга HO (`user_data.history_ops`) | Новый `bph.subtype` (`MOEX_TAX`, `type_id=7`), новая запись `operation` (`operation_type_id=2`), строки `info` (`comment` по `additional_type`), связка `status_to_operation` (`COMPLETE`) | `db-export/БД ИО.md`; Liquibase-образец SIHIST-3321 в `src/test/resources/db/init/create_schema.sql`; SQL кэша `src/main/resources/db/find_all_operations_v2.sql` |
| Запрос к BPH `GET_OPERATIONS_WITH_DETAILS` | Новый subtype автоматически попадает в `subtypesAndStatuses[]` при `operationTypes` содержит `tax` | `BphBcFilterService.buildBphRequestEntityByBphParams()` |
| Обработка ответа BPH | Фильтрация `additionalType`, watershed, маппинг `comment`, статус | `BphBcFilterService.isActualBphOperation()`; `BphCommonClientConverter` |
| Исходящий ответ `SEND_OPERATIONS` | `type=tax`, `comment` из `info`, `general_status=executed`, `id=bph_tax_<externalSystemId>` | SIHIST-3321 / SIHIST-2811 |
| МП / композит (screen-api) | **Без изменений** — тот же `type=tax`, та же деталка `HISTORY_OPS_TAX_DETAILS_SCREEN` | `HistoryOperationTaxDetailsScreen`, `TaxSectionCreator`, `HistoryOperationTaxDetailsHeaderSection` |
| Java `history-ops` | **Без изменений** (data-driven) | — |
| Тесты | Тестовая БД, фикстура ответа BPH, кэш `operation-cache` | `application-test.yml`, `json/response/bph/` |

## Релевантная аналитика и спеки

| Документ (analytics/, Feature-writing/) | Что описывает | Почему релевантно задаче |
|---|---|---|
| `analytics/02-Modules/MOD-001-history-ops/behavior/operation-type-catalog.md` | Таблица «Удержание налогов из BPH (3321)»: `TAXES/TAX_RETAIN` + `additionalType` `OUT_MONEY/OUT_SECURITIES/TAX_PERIOD_END/INCENTIVE_PAYMENT` → `tax`; `TAXES/TAX_REFUND_BROK_ACCOUNT` → `tax_input`; правило `comment`/`display_name` из `info` | **Точная таблица маппинга налогов** — образец для `MOEX_TAX` |
| `analytics/02-Modules/MOD-001-history-ops/data/bc-bph-mapping-db.md` | PostgreSQL-схема маппинга: `operation_type`, `type`, `bph`, `bph_bc`, `operation`, `info`, `status`, `status_to_operation`, `bc_status_to_operation`; форма кэш-строки | Куда и что INSERT-ить |
| `analytics/02-Modules/MOD-001-history-ops/behavior/bph-response-processing.md` | DB-aware mapping: построение `subtypesAndStatuses`/`additionalTypes` из кэша; фазы фильтрации `BphBcFilterService`; маппинг `lead.additionalType` ↔ `info.additional_type` | Алгоритм, который переиспользует новый налог без правок кода |
| `analytics/02-Modules/MOD-001-history-ops/integrations/bph.md` | Контракт `GET_OPERATIONS_WITH_DETAILS` (`POST /api/v1/incoming-gateway/operations-with-details`), поля lead | Контракт источника |
| SPEC `Feature-writing/bph-portfolio-size-tax/bph-portfolio-size-tax.md` | **Sibling-фича** (аналог-близнец): добавляет `TAXES/PORTFOLIO_SIZE_TAX` → `tax` тем же data-driven путём; ссылается на `bph-moex-tax` как на ближайший паттерн | Координация id строк в Liquibase и контрактного написания subtype |
| CONTEXT `Feature-context/bph-portfolio-size-tax.md` | Описывает паттерн SIHIST-3321/MOEX_TAX; перечисляет Java-классы и таблицы с якорями | Сверка якорей и список открытых Q sibling-фичи |

> Примечание: отдельного SIHIST-тикета именно под `MOEX_TAX` в `analytics/` не найдено —
> ближайшие тикеты: SIHIST-3321 (налоги `TAX_RETAIN`/`TAX_REFUND_BROK_ACCOUNT`),
> SIHIST-3367 (обработка ответа), SIHIST-2796/2811 (запрос/ответ DB-aware),
> SIHIST-3423 (additionalTypes в запросе), SIHIST-3476 (правило `comment` для налогов).

## Релевантный код

| Файл | Компонент (класс / метод) | Текущее поведение | Почему важно для фичи |
|---|---|---|---|
| `repositories/ИО/history-ops/src/main/java/.../service/filter/BphBcFilterService.java` | `buildBphRequestEntityByBphParams()` (~L102-121) | Собирает `{type, subtype, statuses}` + `additionalTypes[]` (только non-null `info.additional_type`) в запрос BPH | Новый subtype попадёт в запрос автоматически после INSERT в `bph`/`operation`/`info` |
| то же | `isActualBphOperation()` (~L166-250) | Проверяет watershed (`formationDate` vs `historyStart`), затем `additionalType` ∈ `info.additional_type`; иначе INFO-лог + метрика `unexpected_additional_type_for_common_operation`. Для операции **без bc-контекста** (`bc_id=NULL`) срабатывает ранний `return true` (L185-191) — watershed и `additionalType`-фильтр пропускаются | Определяет, применимы ли watershed/additionalType-фильтры к `MOEX_TAX` — зависит от `bc_id` (Q-03) |
| то же | `isBphCommonOperation()` / `isCommonOperationByBphContext()` (~L69-86) | Членство по статусу: `bphActive && type==bphType && subtype==bphSubtype && statusMap.containsKey(status)` | Операция пройдёт только если статус настроен в `status_to_operation` |
| `repositories/ИО/history-ops/src/main/java/.../service/conversion/BphCommonClientConverter.java` | константа `TAXES` (L40); `convert()` (L50-150) | Строит `HistoryOperationLead` с `type=operation.type()` (уже data-driven `PortfolioOperationType`), затем `getAdditionalInfoFromCache()` → `enrichComment()`/`enrichOperationDisplayName()`. Для `TAXES` при пустом comment из `info` — fallback `lead.setComment(operation.accComment())` (L133-137) | Место, где `comment` берётся из `info` по `additionalType`; fallback на `details.accComment` |
| то же | `getAdditionalInfoFromCache()`, `isCorrectAdditionalType()`, `getOperationFromCache()` (L220-262) | Матчит `bphType+bphSubtype` → `operation` (только `bphActive`), затем `additionalType` ↔ `info.additional_type` (null → `""`). Для coupon/dividend — всегда true | Отличие `MOEX_TAX` от `TAX_RETAIN` — другая строка `info` с иным `comment` |
| то же | `getId()` (L168-187) | `"bph_%s_%s".formatted(operationType.getValue(), externalSystemId)` → `bph_tax_<id>` | Формат id исходящей операции |
| `repositories/ИО/history-ops/src/main/java/.../adapter/bph/BphConverter.java` | `getTypesMap()` / `enrichTypesMapByCacheData()` (L52-75) | Строит маппинг `{type|subtype, bc_type|bc_subtype}` → `PortfolioOperationType.fromValue(operationType string)` из кэша | **Ядро data-driven маппинга**: пара `TAXES|MOEX_TAX` → `tax` появится без правок кода |
| `repositories/ИО/history-ops/src/main/java/.../adapter/bph/BphOperationConverter.java` | `convert()` | Парсит lead BPH (`type`/`subType`/`subtype`/`additionalType`/`formationDate`/`eventDate`/`status`/`agreement`) → `BphOperationWrapper` | Поля ответа BPH, доступные новому налогу |
| `repositories/ИО/history-ops/src/main/java/.../model/Operation.java` | record `Operation`, `toOperationTypeEnum()`, `hasBphContext()` | `toOperationTypeEnum() = PortfolioOperationType.fromValue(operationType)`; `hasBphContext = bphActive && type != null && statusAndGeneralStatus != null` | Форма кэш-строки; условие включения в запрос |
| `repositories/ИО/history-ops/src/main/java/.../cache/OperationCacheLoader.java` + `.../dao/OperationDAO` | загрузка кэша | Периодически грузит `operationDAO.findAll()`, группирует по `operationType` | Кэш, из которого строится запрос/маппинг |
| `repositories/ИО/history-ops/src/main/java/.../configuration/properties/OperationCacheLoaderProperties.java` | `@ConfigurationProperties(prefix="app-config.operation-cache")` | Поля `updateDelayMs`, `defaultValue` (bootstrap JSON), `includingNameTypes` | Ключ конфига кэша; bootstrap JSON нужно дополнить под `MOEX_TAX` |
| `repositories/ИО/history-ops/src/main/resources/db/find_all_operations_v2.sql` | SQL кэша | `json_agg` join `operation`/`operation_type`/`bph`/`bph_bc`/`status_to_operation`/`bc_status_to_operation`/`info` | Источник формы кэш-строки |
| `repositories/ИО/history-ops/src/main/swagger/history/history.yml` | enum `PortfolioOperationType` | `tax` (L71), `tax_input` (L93) | Фронтовый тип уже существует — новый вводить не нужно |
| `repositories/ИО/history-ops/src/main/swagger/bph/bph.yml` | `POST /api/v1/incoming-gateway/operations-with-details` (L216); `OperationData` (L1088); `subtypesAndStatuses[]` (L1292) | Контракт: lead с `type`/`subType`/`subtype`/`additionalType`; запрос `{type, subtype, additionalTypes[0-1], statuses[]}` (required `type`,`subtype`,`statuses`) | Контракт источника/запроса |
| `repositories/ИО/history-ops-screen-api/.../composite/screens/details/HistoryOperationTaxDetailsScreen.java` | `@Screen(bindWithScreenCode="HISTORY_OPS_TAX_DETAILS_SCREEN")` (L10) | Деталка налога | UI не меняется |
| `repositories/ИО/history-ops-screen-api/.../sections/details/tax/HistoryOperationTaxDetailsHeaderSection.java` | `defaultTitleName("Удержание налога")` (L30) | Заголовок деталки без различия по subtype | UI не меняется |
| `repositories/ИО/history-ops-screen-api/.../sections/feed/section/creators/TaxSectionCreator.java` | `titleText("Удержание налога")` (L28) | Заголовок карточки налога в ленте | UI не меняется |

## Данные (БД, выгрузки)

| Таблица / поле / запрос | Где найдено | Текущее устройство | На что влияет фича |
|---|---|---|---|
| `history_ops.type` id=7 | `db-export/БД ИО.md` (object `type`, строка `7 | TAXES`); `create_schema.sql` (changeset SIHIST-3321 `update ... set name='TAXES' where id=7`) | `TAXES` — семейство налогов | Новый subtype ссылается на `type_id=7` |
| `history_ops.operation_type` id=2 / id=20 | `db-export/БД ИО.md` (object `operation_type`, строки `2 | tax`, `20 | tax_input`) | `tax` / `tax_input` | `MOEX_TAX` → `operation_type_id=2` (`tax`) |
| `history_ops.bph` id=19,20 | `db-export/БД ИО.md:425,428`; `create_schema.sql:592-596` | `19 TAX_RETAIN` (type_id=7), `20 TAX_REFUND_BROK_ACCOUNT` (type_id=7), оба `is_active=true`; **`MOEX_TAX` отсутствует** | **INSERT** новый subtype `MOEX_TAX` |
| `history_ops.operation` id=2,23 | `db-export/БД ИО.md:1692,1713`; `create_schema.sql:599-604` | id=2 → `operation_type_id=2 (tax)`, `bc_id=110 (TAX_WITHHOLDING)`, `bph_id=19 (TAX_RETAIN)`, name «Удержание суммы налога»; id=23 → `operation_type_id=20 (tax_input)`, `bc_id=NULL`, `bph_id=20` | **INSERT** новую `operation` (`operation_type_id=2`, `bph_id=<MOEX_TAX>`); `bc_id` — открытый вопрос (Q-03) |
| `history_ops.info` (tax) | `db-export/БД ИО.md` (таблица `info`); `create_schema.sql:620-624` | Для `TAX_RETAIN` (operation 2): `OUT_MONEY`→«Удержание налога при выводе денежных средств», `OUT_SECURITIES`, `TAX_PERIOD_END`, `INCENTIVE_PAYMENT`; для `TAX_REFUND_BROK_ACCOUNT` (operation 23): `additional_type=NULL`, comment «Возврат излишне удержанного налога» | **INSERT** `info` с `comment` для `MOEX_TAX` по `additional_type` |
| `history_ops.status` id=19 | `db-export/БД ИО.md:375`; `create_schema.sql:607-608` | `COMPLETE` → `general_status_id=1 (executed)` | Переиспользовать статус `COMPLETE` |
| `history_ops.status_to_operation` id=28,29 | `db-export/БД ИО.md`; `create_schema.sql:611-613` | `28 → operation_id=2 (tax) ↔ status_id=19`; `29 → operation_id=23 (tax_input) ↔ status_id=19` | **INSERT** связку `operation ↔ status=COMPLETE` |
| `history_ops.bph_bc` id=110 | `db-export/БД ИО.md:439`; `create_schema.sql:699` | `TAX_WITHHOLDING` (`bph_type_id=8 MONEY_DIAS`) — BC-аналог налога | `bc_id=110`, если у `MOEX_TAX` есть BC-контекст (Q-03) |
| Кэш `app-config.operation-cache` (`default-value`) | `src/test/resources/application-test.yml` | JSON: `TAX_RETAIN` → `bc_code:110`, `bc_active:true`, `bph_active:true`, `status_and_general_status: {COMPLETE:executed}`, `info[]` с `additional_type`; `TAX_REFUND_BROK_ACCOUNT` → `tax_input`, `bc_active:false` | Обновить bootstrap JSON (default-value) под `MOEX_TAX` |

## Интеграции и контракты, которые нужно учесть

- Обмен: BPH `GET_OPERATIONS_WITH_DETAILS`, `POST /api/v1/incoming-gateway/operations-with-details` (`bph.yml:216`), синхронный REST/JSON, headers `rqUID`/`systemName` (`si2-ops`).
- Вход от BPH (lead): `type=TAXES`, `subtype=MOEX_TAX`, `additionalType=<значение|NULL>`, `status=COMPLETE`, `totalPrice`, `formationDate`, `eventDate`, `agreement`, `externalSystemId` (`OperationData`, `bph.yml:1088`).
- Запрос к BPH: `subtypesAndStatuses[] = { type, subtype, additionalTypes[0-1], statuses[] }`; required `type`,`subtype`,`statuses` (`bph.yml:1292`). `additionalTypes` собирается из non-null `info.additional_type`.
- Исходящий `SEND_OPERATIONS`: `type` из кэша (`tax`), `comment` из `info`, `id = bph_<type>_<externalSystemId>`, `general_status=executed`, `total_sum` из `totalPrice`.
- МП/композит передаёт `operationTypes: ["tax", ...]`; фронтовый enum `PortfolioOperationType` уже содержит `tax` — правок фронта нет.
- Зависимость: **BPH должен начать отдавать `MOEX_TAX`**; до этого HO не запрашивает и не показывает налог (no-op без сигнала).

## Ограничения и риски текущего состояния

- `MOEX_TAX` **отсутствует** в коде и выгрузках — точное написание subtype и `additionalType` подтверждается только контрактом BPH (Q-01, Q-02). Ошибка в написании → фильтр `additionalTypes` вернёт пусто, налог молча не отобразится.
- Один `operation` в кэше = одна пара `bph.type + bph.subtype`; для `MOEX_TAX` нужна **отдельная** строка `operation`, даже при том же `operation_type=tax` (нельзя «дописать» subtype к `operation` id=2).
- Ветвление watershed/`additionalType`-фильтра зависит от `bc_id` (Q-03):
  - `bc_id=110` (как `TAX_RETAIN`): применимы watershed (`historyStart` по ключу `type|subtype`) и `additionalType`-фильтр;
  - `bc_id=NULL` (как `TAX_REFUND_BROK_ACCOUNT`): ранний `return true` — watershed и `additionalType`-фильтр пропускаются, остаётся только статус-членство.
- Без строки `info` с верным `additional_type` операция с `bc_id=110` отфильтруется (`unexpected_additional_type_for_common_operation` + INFO-лог + метрика).
- Статус-членство проверяется всегда: нужна строка `status_to_operation` (`COMPLETE`), иначе операция не пройдёт `isBphCommonOperation`.
- Правило `comment` (SIHIST-3476): `comment` из `info` по `additional_type`; при пустом — fallback `details.accComment` (константа `TAXES` в `BphCommonClientConverter`).
- **Координация id строк с sibling-фичей `bph-portfolio-size-tax`** (Q-06): обе фичи INSERT-ят в одни и те же таблицы (`bph`/`operation`/`info`/`status_to_operation`) в `create_schema.sql`; при совпадении черновых id второй changeset упадёт по PK. Sibling уже резервирует test-черновики 23/25/53/38, prod-черновики 26/28/80/58 и ссылается на «bph-moex-tax владеет test 22/24/52/37, prod 25/27/79/57».
- Прошлый артефакт `Feature-writing/bph-moex-tax/bph-moex-tax.md` **отсутствует** (в папке только routing-state.json и .pipeline-active-task.json) — ссылки sibling-спеки на «§4.2.3 bph-moex-tax» не могут быть проверены по первичному документу.

## Что учесть при написании фичи

- Следовать паттерну SIHIST-3321: таблица «BPH type / subtype / additionalType / operationTypes / comment»; scope = Liquibase + тестовые фикстуры + пролив на стенды, **Java не меняется**.
- Зафиксировать INSERT в `bph` (subtype `MOEX_TAX`, `type_id=7`), `operation` (`operation_type_id=2`, `bph_id=<новый>`, `bc_id=?`), `info` (comment по `additional_type`), `status_to_operation` (`COMPLETE`). Статус `COMPLETE` переиспользуется — новая строка `status` не нужна.
- Определить `additionalType`: одно значение (non-null, как у `TAX_RETAIN`) или `NULL` (как у `TAX_REFUND_BROK_ACCOUNT`) — это влияет на `additionalTypes[]` в запросе и на `additionalType`-фильтр (Q-02).
- Определить `bc_id`: `110` (BC-контекст, watershed+additionalType применяются) или `NULL` (только BPH, ранний return) — бриф говорит «идентично TAX_RETAIN», что указывает на `110`, но требует подтверждения (Q-03).
- Обновить тестовые фикстуры: `application-test.yml` (`operation-cache` default-value), JSON ответа BPH, `bph_request_all_completed.json`.
- Negative-сценарий: неизвестный `additionalType` (при `bc_id=110`) → операция не попадает в ответ + метрика `unexpected_additional_type_for_common_operation`.
- Композит и МП — out of scope: тот же `type=tax`, деталка `HISTORY_OPS_TAX_DETAILS_SCREEN`, заголовок «Удержание налога» фиксированный; `comment` из `info` показывается в ленте как описание операции.
- Связать с SIHIST-3476: `comment` из `info`, не из `details.accComment` (fallback — только при пустом `info.comment`).

### Актуализация после resolve (2026-10-05)

Решения из resolve, которые писатель и ревьюер должны считать актуальнее исходного current-state:

- GAP-GOAL-02: subtype = `MOEX_TAX` (подтверждено контрактом BPH)
- GAP-UCTB-01: subtype = `MOEX_TAX`
- GAP-CONS-01: subtype = `MOEX_TAX` (допущение AS-01 → подтверждено)
- GAP-INT-01: subtype = `MOEX_TAX` в request/response
- GAP-ALG-06: subtype = `MOEX_TAX`
- GAP-DM-01: `bph.subtype` = `MOEX_TAX`
- GAP-MAP-01: Source `subtype` = `MOEX_TAX`
- GAP-MIG-01: INSERT `subtype='MOEX_TAX'`
- GAP-ACC-04: `subtype = MOEX_TAX`
- GAP-GOAL-03: `additionalType` = `NULL` (одна строка `info` с `additional_type=NULL`)
- GAP-UCTB-02: `additionalType` = `NULL`
- GAP-CONS-02: `additionalType` = `NULL`
- GAP-INT-02: `additionalType` = `NULL`; `additionalTypes[]` не заполняется
- GAP-ALG-02: `additionalType` = `NULL`
- GAP-DM-02: `info.additional_type` = `NULL`
- GAP-MAP-02: Source `additionalType` = `NULL`
- GAP-MIG-02: `info.additional_type = NULL`, одна строка
- GAP-ACC-02: `additionalType = NULL`
- GAP-GOAL-04: `bc_id` = `NULL` (только BPH, ранний return)
- GAP-UCTB-03: `bc_id` = `NULL`
- CH-06: —
- CH-08: —
- CH-11: —
- CH-12: —
- CH-13: —
- CH-01: A
- CH-02: A
- CH-03: B
- CH-04: A
- CH-05: A
- CH-07: A
- CH-09: A
- CH-10: A
- CH-14: A

**Якоря полей из актуальной SPEC:**

`MOEX_TAX`, `GET_OPERATIONS_WITH_DETAILS`, `additionalType`, `comment`, `TAXES`, `CONTEXT_DOC`, `TAX_RETAIN`, `TAX_REFUND_BROK_ACCOUNT`, `PortfolioOperationType`, `tax`, `info`, `additional_type`

См. также § «Закрытые вопросы» ниже — не переспрашивать закрытые Q.
## Открытые вопросы / что проверить

| ID | Вопрос | Где искать ответ |
|---|---|---|
| Q-01 | Точное написание BPH subtype `MOEX_TAX` (и подтверждение, что BPH будет его отдавать). В `db-export/` и `repositories/` 0 совпадений; в семействе `TAXES` сейчас только `TAX_RETAIN`, `TAX_REFUND_BROK_ACCOUNT` | Контракт BPH (`bph_config` / `GET_OPERATION_TYPES`), команда BPH |
| Q-02 | `additionalType` в ответе BPH для `MOEX_TAX`: конкретное значение (тогда нужна строка `info.additional_type` с таким же значением) или `NULL` (одна строка `info` с `additional_type=NULL`, как `TAX_REFUND_BROK_ACCOUNT`)? Бриф говорит «comment из info по additionalType» (намекает на непустой), но sibling-спека `bph-portfolio-size-tax` предполагала для MOEX_TAX `additionalType=NULL` | Контракт BPH; команда BPH |
| Q-03 | `bc_id` для новой `operation`: `110` (`TAX_WITHHOLDING`, двойной BPH+BC контекст — применимы watershed и `additionalType`-фильтр) или `NULL` (только BPH, ранний `return true` без watershed/additionalType)? Бриф «логика идентична TAX_RETAIN» → вероятно `110` | Контракт BC/BPH; SIHIST-3321; команда BPH |
| Q-04 | Текст `comment` (и `operation.name`) для `MOEX_TAX`. Sibling-спека упоминала `operation.name`=«Удержание налога MOEX», `info.comment`=«НАЛОГ МОСКОВСКОЙ БИРЖИ» (CH-09), но первичный SPEC `bph-moex-tax` отсутствует — факт не подтверждён | PO / бизнес-аналитик; команда BPH |
| Q-05 | Watershed `historyStart` для нового subtype (ключ `type|subtype`=`TAXES|MOEX_TAX`) в `bph_dynamic` config — актуален только при `bc_id=110` (Q-03) | `bph_dynamic` config; команда BPH/сопровождения |
| Q-06 | Стратегия id строк в Liquibase (test vs prod) и координация с sibling `bph-portfolio-size-tax` (не пересекаться по `bph`/`operation`/`info`/`status_to_operation`). Prod: `SELECT max(id)+1` или вставка без id + FK по business key | Согласовать порядок пролива с `bph-portfolio-size-tax`; DBA |
| Q-07 | Статус BPH для `MOEX_TAX` — `COMPLETE` (id=19 → `executed`), как у налогов? (переиспользовать `status_to_operation`, новую строку `status` не добавлять) | Контракт BPH; SIHIST-3321 |

## Закрытые вопросы

| ID | Дата | Решение | Где в spec | Источник |
|----|------|---------|------------|----------|
| Q-01 | 2026-10-05 | BPH subtype = `MOEX_TAX` (семейство `TAXES`, `type_id=7`) — подтверждено контрактом BPH | §1.1 (BR-01, CN-01), §4.1.1, §4.2.3 | /resolve-gaps (DECISIONS D-01) |
| Q-02 | 2026-10-05 | `additionalType` для `MOEX_TAX` = `NULL`; одна строка `info` с `additional_type = NULL` (как `TAX_REFUND_BROK_ACCOUNT`); `additionalTypes[]` запроса не заполняется | §1.1 («Противоречия»), §2 (CN-08), §4.1.1, §4.2.3 | /resolve-gaps (DECISIONS D-02) |
| Q-03 | 2026-10-05 | `bc_id` для `MOEX_TAX` = `NULL` (только BPH-контекст): watershed и `additionalType`-фильтр пропускаются (ранний `return true`), остаётся только статус-членство | §1.3, §2 (CN-09), §4.2.2 (BR-13), §4.2.3 | /resolve-gaps (DECISIONS D-03) |
| Q-04 | 2026-10-05 | `operation.name` = «Удержание налога MOEX», `info.comment` = «НАЛОГ МОСКОВСКОЙ БИРЖИ», `info.displayed_name` = `NULL` | §1.3, §4.1.1, §4.2.3, §4.2.4 | /resolve-gaps (DECISIONS D-04) |
| Q-05 | 2026-10-05 | Watershed для `MOEX_TAX` не задаётся — ключ `TAXES\|MOEX_TAX` в `bph_dynamic` config не добавляется (неактуально при `bc_id = NULL`) | §2 (CN-10), §4.2.2 | /resolve-gaps (DECISIONS D-05) |
| Q-06 | 2026-10-05 | Id строк Liquibase зафиксированы: bph-moex-tax владеет test 22/24/52/37, prod 25/27/79/57 (без пересечения с sibling `bph-portfolio-size-tax`) | §2 (CN-03), §4.2.3, §4.2.5 | /resolve-gaps (DECISIONS D-06) |
| Q-07 | 2026-10-05 | Статус BPH для `MOEX_TAX` = `COMPLETE` (id=19 → `general_status=executed`); переиспользуется `status_to_operation`, новая строка `status` не добавляется | §2 (CN-11), §4.1.1, §4.2.3 | /resolve-gaps (DECISIONS D-07) |

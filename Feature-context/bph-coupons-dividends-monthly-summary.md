# Контекст для фичи: bph-coupons-dividends-monthly-summary

## Задача (бриф)

> Нужно написать спецификацию к задаче по вызову **новой** ручки BPH для суммирования купонов и дивидендов за месяц. Ручку проектируем мы сами (контракт ещё не существует в коде), коллеги реализуют её по нашей спецификации. Ручка вызывается **в параллель** с запросом основной истории (main history request / лента операций), как параллельный source-запрос в history-ops. Её данные попадают в композит (BDUI `history-ops-screen-api`), где появляется **новая секция на экране ленты** (сумма купонов и дивидендов за месяц). Функционал нужен **и на общем экране истории, и на экране карточки инструмента**.

Трактовка: это **current-state контекст**, не проектирование. Фича фундаментально отличается от sibling-спек `bph-moex-tax` / `bph-portfolio-size-tax` (те data-driven, без Java и без BDUI): здесь проектируется **новый контракт BPH** (новый endpoint, которого нет в `bph.yml`), **новый параллельный source-запрос** в history-ops (аналог `bphGetLinkedEvents`) и **новая секция** в композите ленты + на карточке инструмента. Купоны и дивиденды как таковые в коде и БД уже есть (типы `coupon`, `coupon_output`, `dividend_input`, `dividend_output`) — новым является их **месячное суммирование** в отдельной сводной секции.

---

## Затронутые области

| Область | Что затрагивается | Документы / код |
|---|---|---|
| Контракт BPH (`bph.yml`) | Новый endpoint «сумма купонов/дивидендов за месяц»; новых endpoint-ов в текущем `bph.yml` нет | `repositories/ИО/history-ops/src/main/swagger/bph/bph.yml` (paths:13-970) |
| history-ops — оркестрация источников | Новый параллельный source-запрос в `Mono.zip(...)` | `service/operation/SourceOperationService.java:84-198`; `service/execution/OperationCollectorAllOperationService.java:37-50` |
| history-ops — gateway-паттерн | Новый gateway + `RpcNamesForRequestCondition` + фиче-флаг | `adapter/AbstractOperationGateway.java`, `adapter/AbstractSplitStatusGateway.java`, `adapter/RpcNamesForRequestCondition.java`, `adapter/bph/linked_events/BphLinkedOperationsGateway.java` |
| history-ops — клиент BPH | Новый метод `BphClient` + DTO из OpenAPI | `adapter/bph/BphClient.java:13-60` |
| history-ops-screen-api — композит ленты | Новая секция в `sections[]` экрана ленты | `composite/sections/feed/*`, `enums/SectionCreatorType.java`, `composite/sections/feed/section/creators/` |
| history-ops-screen-api — карточка инструмента | Та же секция на экране карточки инструмента | `analytics/…/behavior/instrument-card-queries.md`; `composite/screens/feed/screen/` |
| Исходящий контракт | Возможное новое поле/секция в `history.yml` и SEND_OPERATIONS_FEED | `src/main/swagger/history/history.yml`; `analytics/…/MOD-002…/api/send-operations-feed.md` |
| Данные (`history_ops`) | Купоны/дивиденды — транзит из BPH, маппинг через справочные таблицы | `db-export/БД ИО.md:1630-1716` |

---

## Релевантная аналитика и спеки

| Документ | Что описывает | Почему релевантно задаче |
|---|---|---|
| `analytics/02-Modules/MOD-001-history-ops/behavior/feed-orchestration.md` | Параллельные вызовы источников (шаг 5), маршрутизация по `operationTypes` (763), partial failure / `bcDataComplete` (670), RqCoordinator | Образец того, как включается параллельный source-запрос и как он влияет на `bcDataComplete`/`failOperationTypes` |
| `analytics/02-Modules/MOD-001-history-ops/behavior/instrument-card-queries.md` | GET_OPERATIONS с `instrumentFilter`; 24 `operationTypes`, включая `coupon`, `coupon_output`, `dividend_input`, `dividend_output`; 2 параллельных запроса (active+history) | Образец экрана карточки инструмента, куда нужна та же секция |
| `analytics/02-Modules/MOD-001-history-ops/integrations/bph.md` | Контракт BPH `GET_LINKED_EVENTS` / `GET_OPERATIONS_WITH_DETAILS`, endpoint'ы, заголовки, маппинг | Паттерн контракта BPH; купоны/дивиденды идут через `GET_OPERATIONS_WITH_DETAILS` |
| `analytics/02-Modules/MOD-001-history-ops/integrations/corp-actions.md` | КД из BPH: `CA_CASH_MOVEMENT` subtypes, маппинг `type/subtype/additionalType` → типы МП | Источник правил типизации купонов/дивидендов как `CA_CASH_MOVEMENT` |
| `analytics/02-Modules/MOD-001-history-ops/behavior/operation-type-catalog.md` | BPH simple types (varmargin, tax), `failOperationTypes`, маппинг через DB | Паттерн data-driven маппинга simple-типов BPH |
| `analytics/02-Modules/MOD-001-history-ops/behavior/instrument-enrichment.md` | `BphCommonEnricher` (isin-only/ticker-only), «BPH coupon/dividend instrument block» (2048) | Купоны/дивиденды обогащаются инструментом по isin |
| `analytics/02-Modules/MOD-001-history-ops/integrations/feature-toggle.md` | Каталог toggles (`FeatureToggleName`), getSession | Как заводятся фиче-флаги для новых запросов |
| `analytics/02-Modules/MOD-002-history-ops-screen-api/behavior/composite-feed-backend.md` | Сборка `screenData` + `sections`, маппинг `failOperationTypes → failedOperationType` | Где в композите ленты появляется новая секция |
| `analytics/02-Modules/MOD-002-history-ops-screen-api/api/get-operations-feed.md` / `send-operations-feed.md` | REST-контракт ленты композита | Куда добавить новую секцию/поле |
| `analytics/04-Frontend/composite-feed-screen.md` | Экран ленты: типы секций (`history.feed.title`, `history.feed.operation`, `history.feed.operationActive`) | Секции ленты AS IS; сводной секции сейчас нет |
| `analytics/04-Frontend/composite-detail-screen.md` | Деталка операции; деталки купонов/дивидендов | Соседние экраны; не путать «карточку инструмента» с «деталкой операции» |
| `Feature-writing/bph-linked-events-yield/bph-linked-events-yield.md` | Новое поле в существующем endpoint; сквозной проброс BPH→HO→`history.yml`→BDUI | Ближайший reference по сквозному пробросу и правке контрактов (`bph.yml` + `history.yml`) |
| `Feature-writing/bph-moex-tax/bph-moex-tax.md` | Data-driven добавление налога (таблицы `bph`/`operation`/`info`/`status_to_operation`) | Reference по маппинг-таблицам и Liquibase (но тут Java/BDUI не меняются — в отличие от нашей фичи) |
| `Feature-writing/bph-portfolio-size-tax/bph-portfolio-size-tax.md` | То же, полная структура секций 4.x | Reference по структуре фичи-спеки |

---

## Релевантный код

### Параллельные source-запросы (history-ops)

| Файл | Компонент (класс/метод/якорь) | Текущее поведение | Почему важно для фичи |
|---|---|---|---|
| `service/operation/SourceOperationService.java` | `getOperationsFromSources()` (строки 84-198), record `SourceOperations` (65-81) | Все gateway-запросы запускаются **параллельно** через один `Mono.zip(...)` (156-197): OG, DCA/ECM/DCM, `bphGateway`, `bphLinkedOperationsGateway`, `bphDynamicConfigService` | **Точка добавления** нового параллельного запроса к BPH (новый Mono + поле в `SourceOperations` + позиция в `Mono.zip`) |
| `service/execution/OperationCollectorAllOperationService.java` | `getOperations()` (37-50), `processOperations()` (60-78) | Вызывает `SourceOperationService`, затем merge + пагинация | Верхнеуровневый collector, вызывающий параллельный fetch |
| `adapter/AbstractOperationGateway.java` | `getOperations()` (48-84): `enabled()` → `matchFilter` → `matchInstrumentType` → `generalStatusFilter` → `isActiveGateway` | Базовая логика включения gateway: фиче-флаг + фильтр типов + фильтр инструмента + кэш пагинации | Шаблон для нового gateway; `enabled()` возвращает пусто, если флаг выключен |
| `adapter/AbstractSplitStatusGateway.java` | `generalStatusFilter()` (29-37), `ruleKey()` (25) | Для запроса с `instrumentFilter` берёт `RequestRule` (active/inactive) по `ruleKey()` | Управление составом статусов по `app-config-dynamic` |
| `adapter/RpcNamesForRequestCondition.java` | enum, строки 8-25 | 9 RPC-имён → ключи конфиг-мапы: `ogGetTradeOrders`, `bphGetLinkedEvents`, `bphGetOperationsWithDetails`, `bphGetBphOrders`, DCM/ECM/DCA | Новый RPC-ключ (например `bphGetCouponsDividendsMonthlySummary`) добавляется сюда |
| `adapter/bph/linked_events/BphLinkedOperationsGateway.java` | класс; `ruleKey()` (144-147), `enabled()` (62-66), `exSystem()="BPH"`, `eventType()="GET_LINKED_EVENTS"`, `createRequest()` (86-119) | Образец BPH-gateway, возвращающего `bphGetLinkedEvents` как конфиг-ключ | **Главный образец** для нового параллельного BPH-запроса |
| `adapter/bph/BphClient.java` | WebClient, строки 15-58: `OPERATIONS_URL`, `OPERATION_TYPES_URL`, `LINKED_EVENTS_URL` | Ручной WebClient (не сгенерированный) с 3 endpoint'ами; DTO (`RequestParamsData`, `RequestLinkedData`, `ApiV1IncomingGateway…Response`) — сгенерированы из `bph.yml` | Сюда добавляется новый метод под новый endpoint; DTO регенерируются из OpenAPI |
| `adapter/auth/FeatureToggleName.java` | enum, строки 7-28 | Toggles: `enableServiceBPH`, `enableBphLinkedCommissions`, `enableBphTradingOperations`, … | Новый toggle для включения нового запроса |
| `model/ExecutionProcess.java` | `isBphLinkedCommissionsEnabled()` (100-102), `isBphLinkedTradingOpsEnabled()` (104-106) | Читает `featureToggles` map из getSession | Новый `is…Enabled()` метод для нового флага |
| `configuration/properties/AppConfigDynamicProperties.java` | `instrumentFilterRequestsDynamic` (17); `feedRequestsDynamic` **закомментирован** (18); `RequestRule{active,inactive}` (20-25) | Конфиг-мапа `app-config-dynamic.instrument-filter-requests-dynamic.<rpc>`; для ленты (без instrumentFilter) мапа не активна | Ключевой нюанс: фича-флаг по `ruleKey()` сейчас работает **только для карточки инструмента** |
| `service/RequestRuleService.java` | `getRequestRule()` (15-24), `defaultRule()` (26-39) | Для feed (`hasInstrumentFilter=false`) возвращает пустую мапу (`Map.of()`), default `active=true, inactive=true` | Подтверждает: `feedRequestsDynamic` не заведён; комментарий «поменять на false, когда подкинем ключи для запроса с ленты» (33) |
| `service/SplitStatusFilter.java` | `build()` (22-41) | По `RequestRule.active/inactive` фильтрует статусы | Механика active/inactive для нового запроса |

### Композит ленты и секции (history-ops-screen-api)

| Файл | Компонент (класс/якорь) | Текущее поведение | Почему важно для фичи |
|---|---|---|---|
| `models/CompositeOperationsFeedInputData.java` | класс; `getScreenSelector()="HISTORY_OPS_FEED_SCREEN"` (100-102) | Входные данные сборки ленты композита | Контекст сборки экрана ленты |
| `services/screen/composite/CompositeScreenService.java` | `getFeed()` / `getScreenForOperation()` (9-11) | Интерфейс сборки экранов | Точка входа сборки ленты и деталки |
| `composite/sections/feed/SectionCreator.java` | интерфейс `createSection()` / `getType()` | Контракт создателя секции | Для новой секции — новый `SectionCreator` (или иной механизм) |
| `composite/sections/feed/SectionCreatorRegistry.java` | `resolveType()` switch (37-70): `COUPON → COUPON_INPUT`, `DIVIDEND_INPUT → DIVIDEND_INPUT`, … | Маппинг `PortfolioOperationType` → `SectionCreatorType` для карточек операций | Показывает, что секции сейчас строятся **per-operation**; сводная секция — иной тип |
| `enums/SectionCreatorType.java` | enum, 34 значения (`TITLE`, `COUPON_INPUT`, `COUPON_OUTPUT`, `DIVIDEND_INPUT`, `DIVIDEND_OUTPUT`, …) | Реестр типов секций | Новый тип сводной секции добавляется сюда (если per-type подход) |
| `composite/sections/feed/section/creators/TitleSectionCreator.java` | `createSection()` → тип `history.feed.title` (49-57) | Секция заголовка дня | Пример не-operation секции (не привязана к карточке) — ближайший аналог сводной секции |
| `composite/sections/feed/section/creators/AbstractSectionCreator.java` | `resolveType()` (64-72): `history.feed.operation` / `history.feed.operationActive` | База для карточек операций | Карточки операций AS IS |
| `composite/sections/feed/section/creators/CouponInputSectionCreator.java` | `buildContext()` (17-27): title «Выплата купонов», `amountPrefix("+")` | Карточка зачисления купона | Показывает существующее отображение купона |
| `composite/sections/details/coupon/input/HistoryOperationCouponDetailsHeaderSection.java` | детальная секция купона | Шапка деталки купона | Деталки купонов/дивидендов уже есть (см. БД-словарь экранов) |
| `composite/sections/details/dividend/input/HistoryOperationDividendInputDetailsHeaderSection.java` | детальная секция дивиденда | Шапка деталки дивиденда | То же |

### Купоны и дивиденды (типизация в коде)

| Файл | Компонент (якорь) | Текущее поведение | Почему важно для фичи |
|---|---|---|---|
| `adapter/bph/BphOperationWrapper.java` | `CA_CASH_MOVEMENT` (22), `COUPON_DIVIDEND_SUBTYPES` (24-26) | `INTEREST_PAYMENT_CREDIT`, `CASH_DIVIDEND_CREDIT`, `CASH_DIVIDEND_DEBIT`, `INTEREST_PAYMENT_DEBIT` | Канонический набор BPH-subtypes купонов/дивидендов |
| `adapter/bph/common/BphCommonWrapper.java` | `isCouponDividendOperation()` (74-76) | `"CA_CASH_MOVEMENT".equals(originalType) && COUPON_DIVIDEND_SUBTYPES.contains(bphType)` | Признак «купон/дивиденд» в коде |
| `service/filter/BphBcFilterService.java` | строка 131 (та же проверка `CA_CASH_MOVEMENT` + `COUPON_DIVIDEND_SUBTYPES`) | Фильтр simple-типов BPH | Место фильтрации ответа BPH |
| `service/FailOperationTypeService.java` | строки 50-52: `DIVIDEND_INPUT`, `DIVIDEND_OUTPUT`, `COUPON` | Купоны/дивиденды учитываются в `failOperationTypes` при сбое `GET_OPERATIONS_WITH_DETAILS` | Для новой ручки потребуется решение по `failOperationTypes`/`bcDataComplete` |
| `adapter/bph/BphConverter.java` | строки 207, 238-239: detail-ключи `leg1_coupon_amount`, `coupon1`, `coupon2` | Доп. поля купонов в деталях | Существующие детальные поля купонов |

---

## Данные (БД, выгрузки)

Источник: `db-export/БД ИО.md` (схема `history_ops`).

| Таблица / поле | Где найдено | Текущее устройство | На что влияет фича |
|---|---|---|---|
| `operation_type` | `db-export/БД ИО.md:1540-1555` | `coupon` (id 5), `dividend_input` (6), `dividend_output` (11), `coupon_output` (14) | Типы операций купонов/дивидендов уже существуют; сводная секция — **не** новый тип операции |
| `bph` (справочник type/subtype) | `db-export/БД ИО.md:1630-1660` | `INTEREST_PAYMENT_CREDIT` (1), `CASH_DIVIDEND_CREDIT` (2), `CASH_DIVIDEND_DEBIT` (3), `INTEREST_PAYMENT_DEBIT` (4), все `type_id=1 (CA_CASH_MOVEMENT)` | BPH-subtypes купонов/дивидендов |
| `bph_bc` (legacy BC ↔ BPH) | `db-export/БД ИО.md:1662-1682` | `COUPON_CREDITING` (114), `DIVIDEND_CREDITING` (111), `DIVIDEND_WITHDRAWAL` (112) | Legacy BC-коды купонов/дивидендов |
| `operation` (маппинг ИО↔BC/BPH) | `db-export/БД ИО.md:1695-1705` | id=5 `coupon`→114→1 «Зачисление купона»; id=6 `dividend_input`→111→2; id=12 `dividend_output`→112→3; id=15 `coupon_output`→NULL→4 | Маппинг купонов/дивидендов data-driven |
| `general_status`, `status` | `db-export/БД ИО.md:1557-1606` | `COMPLETE` (id 19) → `executed` (1) | Статусы для новых операций (если понадобятся) |
| Словарь экранов/секций | `db-export/БД ИО.md:868-871, 949-956, 1234-1271` | Деталки `HISTORY_OPS_COUPON_DETAILS_SCREEN`, `…_COUPON_OUTPUT_…`, `…_DIVIDEND_INPUT_…`, `…_DIVIDEND_OUTPUT_…` + секции заголовка/параметров | Деталки купонов/дивидендов уже есть; сводной секции **нет** |
| Фильтр ленты | `db-export/БД ИО.md:858` | Группа «Купоны и дивиденды»: `DIVIDEND_INPUT`, `DIVIDEND_OUTPUT`, `COUPON`, `COUPON_OUTPUT` | Купоны/дивиденды уже есть в фильтре ленты |

> **Ключевой вывод по данным:** отдельной таблицы/колонки для «суммы купонов и дивидендов за месяц» **нет**. Купоны/дивиденды — это транзитные операции из BPH `GET_OPERATIONS_WITH_DETAILS` (тип `CA_CASH_MOVEMENT`), маппятся через справочные таблицы `bph`/`operation`/`info`/`status_to_operation`. Сумма за месяц будет приходить из **новой ручки BPH** (агрегация на стороне BPH), а не вычисляться из строк БД HO.

---

## Интеграции и контракты, которые нужно учесть

- **BPH `bph.yml`** (`src/main/swagger/bph/bph.yml`, OpenAPI 3.0.1). Существующие endpoint'ы (paths:13-970): `GET /operations`, `POST /operations-with-details`, `GET /operation/details`, справочники `/operation-types[/{type}[/subtypes/{subtype}[/statuses|fields-info]]]`, `POST /operations/linked-events`. **Endpoint'а для суммы купонов/дивидендов нет** — он проектируется с нуля.
  - Схемы: `RequestLinkedData` (bph.yml:1053-1087), `OperationData` (bph.yml:1088+), `LinkedEventsData` (bph.yml:991-1052), `ResponseStatusData`, `ErrorData`, `DetailData`.
  - Заголовки: `rqUID` (uuid), `systemName` (`si2-ops` / в коде `BphClient` использует `history_ops`).
- **DTO генерируются из OpenAPI** (`bph.yml` → `RequestLinkedData`, `ApiV1IncomingGatewayOperationsLinkedEventsPost200Response` и т.п.). Новый endpoint = новая схема в `bph.yml` + ребилд DTO. (Подтверждено: `BphClient` ссылается на сгенерированные типы; в `bph-linked-events-yield` зафиксировано «DTO регенерируются из OpenAPI».)
- **`BphClient`** (`adapter/bph/BphClient.java`) — ручной `WebClient`; новый метод добавляется вручную под новый endpoint.
- **Исходящий контракт `history.yml`** (`src/main/swagger/history/history.yml`): `PortfolioOperationType` (строки 60-93, включает `coupon`, `coupon_output`, `dividend_input`, `dividend_output`), `HistoryOperationLead` (456-506), `HistoryOperationBase`, `OperationHistoryResponse` (`bcDataComplete`, `failOperationTypes`). Для сводной секции возможен новый payload в композит (не обязательно новый `PortfolioOperationType`).
- **Композит screen-api**: REST `POST /history/api/public/v1/screens/feed` → `screenData` + `sections[]` (`send-operations-feed.md`, `composite-feed-backend.md`). Секции имеют `type` (`history.feed.title`, `history.feed.operation`, `history.feed.operationActive`).
- **Фиче-флаги**: `app-config-dynamic.instrument-filter-requests-dynamic.<rpc>.active/inactive` (только карточка инструмента); для ленты `feedRequestsDynamic` закомментирован (`AppConfigDynamicProperties.java:18`, `RequestRuleService.java:18-20`).
- **Домен**: `eventType`/`exSystem` для наблюдаемости — образец `exSystem="BPH"`, `eventType="GET_LINKED_EVENTS"` (`BphLinkedOperationsGateway.java:127-134`).

---

## Ограничения и риски текущего состояния

- **Контракт BPH не существует.** Новая ручка проектируется «с листа» — нет проверяемого `bph.yml`/кода; все поля и имена endpoint'а будут решениями спецификации (ср. `bph-linked-events-yield` GAP-INT-04/05). Технические факты для новой ручки проверить по коду невозможно — это `Q-XX`, не подтверждаемые факты.
- **Фиче-флаг параллельного запроса для ленты не заведён.** `RequestRuleService` для feed возвращает пустую мапу, `feedRequestsDynamic` закомментирован (комментарий «поменять на false, когда подкинем ключи для запроса с ленты»). Включение нового запроса на ленте (а не только на карточке) потребует завести `feedRequestsDynamic`/аналогичный механизм.
- **Секции ленты строятся per-operation.** `SectionCreatorRegistry` маппит `PortfolioOperationType → SectionCreatorType` для карточек операций; сводная секция (агрегат за месяц, не карточка) — другой тип секции, ближайший аналог — `TitleSectionCreator` (не-operation секция). Механику вставки сводной секции в поток `sections[]` нужно проектировать отдельно.
- **Купоны/дивиденды уже есть как отдельные операции** (`coupon`, `coupon_output`, `dividend_input`, `dividend_output`) — новая секция не должна дублировать/конфликтовать с ними, это **агрегат**, а не операция.
- **Сводная секция не укладывается в `failOperationTypes`.** Механизм неполноты (`bcDataComplete`, `failOperationTypes[]`) описан для операций; для сводной секции при сбое новой ручки BPH поведение (скрыть секцию vs пометить ленту неполной) не определено.
- **Карточка инструмента vs лента.** На карточке запросы идут с `instrumentFilter` и по `ruleKey()` действует `instrumentFilterRequestsDynamic`; на ленте — нет. Для секции на карточке инструмента нужно определить, тот же это запрос с фильтром инструмента или отдельный.
- **Валюта сумм.** Купоны/дивиденды могут быть в разных валютах (`totalPrice.currency`); агрегация «за месяц» требует решения по валютам.

---

## Что учесть при написании фичи

- **Новый endpoint BPH** описывать по образцу `POST /operations/linked-events` из `bph.yml` (request schema → `ResponseStatusData` + data array; заголовки `rqUID`/`systemName`). Зафиксировать: имя endpoint, метод, request/response схему, поля суммы (value/currency), период «месяц», группировку (по договорам? по инструментам?). Это `Q-01…Q-02` — решения, а не подтверждаемые факты.
- **Параллельный source-запрос** в history-ops: новый gateway (образец `BphLinkedOperationsGateway`), новый `RpcNamesForRequestCondition`, новый `FeatureToggleName` + `ExecutionProcess.is…Enabled()`, новый метод `BphClient`, новый Mono в `SourceOperationService.getOperationsFromSources()` + поле в `SourceOperations` + позиция в `Mono.zip`.
- **Фиче-флаг**: учесть, что для ленты `feedRequestsDynamic` не активен (`RequestRuleService.java:18-20`) — решить, как включается запрос на общем экране истории.
- **Композит**: описать новую секцию ленты (тип, `content`, порядок/`order`, где в `sections[]`), и её же на карточке инструмента; учесть механизм сборки (`CompositeScreenService.getFeed` → `SectionCreator`/иной путь для не-operation секции).
- **Исходящий контракт**: решить, как сводные данные доезжают от HO до композита (новое поле в SEND_OPERATIONS/`history.yml` или отдельный канал) и в каком поле ответа SEND_OPERATIONS_FEED появляется секция.
- **Обратная совместимость**: новая секция и новый endpoint не должны ломать текущие ответы BPH и экран ленты (ср. CN-01/CN-03 в `bph-linked-events-yield`).
- **Sibling-фичи как reference**: `bph-linked-events-yield` (сквозной проброс поля через контракты), `bph-moex-tax`/`bph-portfolio-size-tax` (структура разделов 1.x/4.x, но они data-driven без Java/BDUI — не копировать слепо).

---

### Актуализация после resolve (2026-08-30)

Решения из resolve, которые писатель и ревьюер должны считать актуальнее исходного current-state:

- GAP-UCTB-01, GAP-INT-01, GAP-ALG-01, GAP-MAP-01, GAP-OBS-01, GAP-CONS-01: `POST /api/v1/incoming-gateway/operations/coupons-dividends-monthly-summary`; `eventType=GET_COUPONS_DIVIDENDS_MONTHLY_SUMMARY`; RPC-ключ `bphGetCouponsDividendsMonthlySummary`
- GAP-UCTB-02, GAP-INT-02, GAP-ALG-02, GAP-MAP-02: `data` = один объект `{period, totalCouponsSum, totalDividendsSum, totalCouponsDividendsSum}`, без разбивки по договорам/инструментам
- GAP-UCTB-03, GAP-INT-03, GAP-ALG-03, GAP-MAP-03: Период задаётся `startSearchDate`/`endSearchDate`; в ответе `period="YYYY-MM"`
- GAP-UCTB-04, GAP-INT-04, GAP-ALG-04, GAP-MAP-04: Каждая сумма — список `PriceData[]` (по одному элементу на валюту); секция отображает мультивалютно
- GAP-UCTB-05, GAP-INT-05, GAP-ALG-05, GAP-NFR-09, GAP-OBS-03, GAP-CONS-03: Заводится `feedRequestsDynamic` с ключом `bphGetCouponsDividendsMonthlySummary` + `FeatureToggleName.enableBphCouponsDividendsMonthlySummary`
- GAP-UCTB-06, GAP-INT-06, GAP-ALG-06, GAP-MAP-06: Тип секции `history.feed.couponsDividendsSummary` (`SectionCreatorType`), по образцу `TitleSectionCreator`; позиция `order=0`
- GAP-UCTB-07, GAP-INT-07, GAP-ALG-07, GAP-MAP-05: Поле `couponsDividendsMonthlySummary` в `history.yml` (`OperationHistoryResponse`)
- GAP-UCTB-08, GAP-INT-08, GAP-ALG-08, GAP-MAP-09, GAP-NFR-08, GAP-OBS-04, GAP-OBS-05, GAP-CONS-04: При пустом/нулевом ответе и при сбое секция скрывается; ручка не влияет на `bcDataComplete`/`failOperationTypes`; метрика `summary_empty`
- GAP-UCTB-09, GAP-INT-09, GAP-ALG-09, GAP-MAP-07, GAP-CONS-05: Один endpoint; на карточке инструмента передаётся `instrumentId`, на ленте — без фильтра
- GAP-UCTB-10, GAP-INT-10, GAP-ALG-10: Сводная секция не операция: не учитывается в лимите 100 и в `SourcesInfo`/пагинации
- GAP-UCTB-11, GAP-INT-11, GAP-ALG-11, GAP-MAP-10: Сводная сумма — независимый расчёт на стороне BPH, не вычисляется из операций `CA_CASH_MOVEMENT` ленты
- GAP-GOAL-01, GAP-GOAL-02: Инициатор/дата постановки не указаны в брифе (зафиксировано допущением)
- GAP-GOAL-03, GAP-GOAL-04, GAP-OBS-07: «Улучшение UX без количественной метрики»; срок/релиз не задан на этапе проектирования
- GAP-UCAS-01, GAP-UCAS-02, GAP-UCAS-03: Частота/стоимость/приоритет проблемы AS IS — «Не оценивается»
- GAP-UCAS-04: Источники OG/DCA/ECM/DCM сгруппированы в один участник диаграммы (примечание в §1.2)
- GAP-INT-12, GAP-NFR-01, GAP-NFR-02, GAP-OBS-02: Auth без отдельной security scheme (как `bph.yml`); timeout/retry/rate-limit наследуют `BphClient`; суммы маскируются в логах
- GAP-NFR-03, GAP-NFR-05, GAP-NFR-07, GAP-OBS-06: p85/SLA/RPS/CCU/SLO и параметры БД BPH определяются после load-теста
- GAP-NFR-04: Web-vitals (LCP/FID/CLS/TTI) не меняются
- GAP-NFR-06: Кэширование сводной суммы не предусмотрено
- GAP-NFR-10: Toggle `false` по умолчанию; `app-config-dynamic` ключи active/inactive=true; валидация boolean
- CH-01: «Месяц из periodFilter ленты»
- CH-02: «Сводка независима» (согласовано: CH-03 побеждает)
- CH-03: «Сводку показывать»
- CH-04: «Сверка не требуется»
- CH-05: «Сводку показывать»
- CH-06: «Сумма по инструменту»
- CH-07: «Опциональны + дефолт месяц»
- CH-08: «Серверная таймзона history-ops»
- CH-09: «onErrorResume → пустая сводка»
- CH-10: «Инвариант как требование к BPH»
- CH-11: «period по startSearchDate»
- CH-12: «Дополнить коды»
- CH-13: «Как пусто»
- CH-14: «agreements — опциональный фильтр»
- CH-15: «Версионирование»
- CH-16: «Только зачисления»
- CH-17: «Наследовать BphClient»
- CH-18: «Toggle — мастер»
- CH-19: «Отдельный gateway»
- CH-20: «Принять сырое логирование»

**Якоря полей из актуальной SPEC:**

`coupon`, `coupon_output`, `dividend_input`, `dividend_output`, `bcDataComplete`, `GET_OPERATIONS_WITH_DETAILS`, `feedRequestsDynamic`, `getHistoryOperationsFeed`, `CA_CASH_MOVEMENT`, `INTEREST_PAYMENT_CREDIT`, `CASH_DIVIDEND_CREDIT`, `CASH_DIVIDEND_DEBIT`

См. также § «Закрытые вопросы» ниже — не переспрашивать закрытые Q.
## Открытые вопросы / что проверить

| ID | Вопрос | Где искать ответ |
|---|---|---|
| Q-01 | Имя и сигнатура нового endpoint BPH (path, метод GET/POST, имя в `bph.yml`, `eventType` для наблюдаемости). В текущем `bph.yml` такого endpoint нет (проверено: paths:13-970) | Команда BPH / решение спецификации; образец `operations/linked-events` в `bph.yml` |
| Q-02 | Формат ответа новой ручки: что именно суммируется — общая сумма купонов+дивидендов за календарный месяц? Разбивка по договорам/инструментам? Одна сумма или массив периодов? | Бриф / Product Owner; команда BPH (что может отдавать агрегированно) |
| Q-03 | Границы «месяца» и периода: календарный месяц, скользящий период, или привязка к `periodFilter`/`endSearchDate` запроса ленты | Бриф / PO |
| Q-04 | Валюты сумм: агрегация по каждой валюте отдельно или единая? Как отображать мультивалютную сумму в секции | PO / команда screen-api |
| Q-05 | Как включается параллельный запрос на **ленте** (не карточке): `feedRequestsDynamic` закомментирован (`RequestRuleService.java:18-20`, `AppConfigDynamicProperties.java:18`). Нужно ли заводить отдельный toggle/ключ для feed | Команда history-ops; код `RequestRuleService`/`AppConfigDynamicProperties` |
| Q-06 | Как сводная секция встраивается в `sections[]` ленты: это новый не-operation `SectionCreator` (по образцу `TitleSectionCreator`) или отдельный механизм сборки вне `SectionCreatorRegistry`? Какой `type` секции (например `history.feed.couponsDividendsSummary`)? | Команда screen-api; `composite/sections/feed/*`, `SectionCreatorRegistry.java` |
| Q-07 | Как сводные данные доезжают до композита: новое поле в SEND_OPERATIONS / `history.yml`, отдельный параллельный источник в screen-api, или расширение SEND_OPERATIONS_FEED? | Команда history-ops + screen-api; `history.yml`, `send-operations-feed.md` |
| Q-08 | Поведение при сбое новой ручки BPH: скрыть сводную секцию, показать заглушку, или пометить ленту `bcDataComplete=false`/добавить в `failOperationTypes`? (`FailOperationTypeService` сейчас работает по типам операций) | Команда history-ops / PO; `FailOperationTypeService.java`, `feed-orchestration.md` (670) |
| Q-09 | На карточке инструмента сводная секция — это тот же параллельный запрос с `instrumentFilter`, или отдельная логика/ручка? | Команда history-ops; `instrument-card-queries.md`, `AbstractOperationGateway.matchInstrumentType` |
| Q-10 | Влияет ли новая сводная секция на пагинацию/RqCoordinator (секция не операция, поэтому не входит в `SourcesInfo`/лимит 100 операций)? | Команда history-ops; `feed-orchestration.md` (RqCoordinator), `SourceOperationService` |
| Q-11 | Связь с существующими операциями купонов/дивидендов (`coupon`, `coupon_output`, `dividend_input`, `dividend_output`): сводная секция — это агрегат тех же операций BPH `CA_CASH_MOVEMENT` или независимые данные от BPH? | Команда BPH / PO; `BphOperationWrapper.COUPON_DIVIDEND_SUBTYPES` |

## Закрытые вопросы

| ID | Дата | Решение | Где в spec | Источник |
|----|------|---------|------------|----------|
| Q-01 | 2026-08-30 | Endpoint `POST /api/v1/incoming-gateway/operations/coupons-dividends-monthly-summary`; `eventType=GET_COUPONS_DIVIDENDS_MONTHLY_SUMMARY`; RPC-ключ `bphGetCouponsDividendsMonthlySummary` | §4.1.1, §4.1.1.1, §4.2.2, §5.3 | /resolve-gaps (GAP-INT-01 и др.) |
| Q-02 | 2026-08-30 | Формат ответа — один объект `data` с `period`, `totalCouponsSum`, `totalDividendsSum`, `totalCouponsDividendsSum` (без разбивки по договорам/инструментам) | §4.1.1 | /resolve-gaps (GAP-INT-02) |
| Q-03 | 2026-08-30 | Границы месяца — календарный месяц через `startSearchDate`/`endSearchDate`; в ответе `period="YYYY-MM"` | §4.1.1 | /resolve-gaps (GAP-INT-03) |
| Q-04 | 2026-08-30 | Валюты — суммы разбиты по валютам: каждая сумма = список `PriceData[]` (по строке на валюту) | §4.1.1, маппинг | /resolve-gaps (GAP-INT-04) |
| Q-05 | 2026-08-30 | Включение на ленте — завести `feedRequestsDynamic` (ключ `bphGetCouponsDividendsMonthlySummary`) + `FeatureToggleName.enableBphCouponsDividendsMonthlySummary` | §4.1.1.1, §5.4, §5.5 | /resolve-gaps (GAP-INT-05, GAP-NFR-09) |
| Q-06 | 2026-08-30 | Секция — новый не-operation `SectionCreator` по образцу `TitleSectionCreator`, тип `history.feed.couponsDividendsSummary`, `order=0` | §4.1.1.2 | /resolve-gaps (GAP-INT-06) |
| Q-07 | 2026-08-30 | Доставка — новое поле `couponsDividendsMonthlySummary` в `OperationHistoryResponse` (`history.yml`) | §4.1.1.2, маппинг | /resolve-gaps (GAP-INT-07) |
| Q-08 | 2026-08-30 | Сбой/пустой ответ — сводная секция скрывается; ручка не влияет на `bcDataComplete`/`failOperationTypes`; метрика `summary_empty` | §1.3, §4.2.2, §7.2, §5.3.2 | /resolve-gaps (GAP-INT-08) |
| Q-09 | 2026-08-30 | Карточка инструмента — тот же запрос с параметром `instrumentId` (на ленте без фильтра) | §1.3, §4.1.1 | /resolve-gaps (GAP-INT-09) |
| Q-10 | 2026-08-30 | Пагинация — сводная секция не входит в лимит 100 операций и в `SourcesInfo` | §4.1.1.1, §4.2.2 | /resolve-gaps (GAP-INT-10) |
| Q-11 | 2026-08-30 | Связь с операциями — сводная сумма это независимые данные от BPH (не вычисляется из операций `CA_CASH_MOVEMENT` ленты) | §4.1.1.1 | /resolve-gaps (GAP-INT-11) |
| Q-03 | 2026-08-30 | Уточнено: месяц = месяц `periodFilter` ленты (иначе текущий календарный); границы в таймзоне Europe/Moscow (на wire UTC); даты опциональны → дефолт текущий месяц; пересечение месяцев → `period` по `startSearchDate` | §4.1.1, §4.2.2, CN-13 | /resolve-challenges (CH-01, CH-07, CH-08, CH-11) |
| Q-08 | 2026-08-30 | Уточнено: независимость от `bcDataComplete` явно зафиксирована [BR-07]; сводка скрывается только при сбое/пустом ответе самой ручки; изоляция ошибки `onErrorResume` | §1.1 BR-07, §4.2.2 alt 8a, §4.1.1.1 | /resolve-challenges (CH-02, CH-03, CH-09) |
| Q-09 | 2026-08-30 | Уточнено: `instrumentId` сужает агрегат до одного инструмента (целевой UX «сумма по инструменту за месяц») | §4.1.1 | /resolve-challenges (CH-06) |
| Q-11 | 2026-08-30 | Уточнено: сверка с карточками операций ленты не выполняется (возможное расхождение допустимо) [BR-08] | §1.1 BR-08 | /resolve-challenges (CH-04) |
| Q-05 | 2026-08-30 | Уточнено: матрица включения toggle/config [CH-18] — toggle мастер-переключатель; на ленте нужен ключ `feedRequestsDynamic` | §5.5 | /resolve-challenges (CH-18) |

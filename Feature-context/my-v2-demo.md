# Контекст для фичи: my-v2-demo

## Задача (бриф)

> Новая ручка BPH «Сумма купонов и дивидендов за месяц» (BPH monthly summary). Контракта ещё нет — `bph.yml` не содержит endpoint; ручку проектируем мы, коллеги BPH реализуют по спеке. Купоны и дивиденды как операции уже есть (`CA_CASH_MOVEMENT` / типы МП `coupon`, `coupon_output`, `dividend_input`, `dividend_output`); новым является именно месячная сводка. `history-ops` подключает параллельный source-запрос к новой ручке вместе с основной историей (лентой); образец подключения — gateway `BphLinkedOperationsGateway` (`GetLinkedEvents`), не сам `GET_LINKED_EVENTS`. Корпоративные действия (DCA/ECM/DCM) и карточки купонов/дивидендов в ленте НЕ заменяются. `history-ops-screen-api` (BDUI-композит) добавляет новую секцию на экране ленты и на карточке инструмента (раздел «История»); это агрегат, не новая операция и не деталка.

Трактовка: фича — **integration** (новый BPH-контракт + параллельный source-запрос в HO + новая секция в BDUI-композите). Купоны/дивиденды как операции остаются AS IS; появляется агрегированная месячная сводка по ним.

## Затронутые области

| Область | Что затрагивается | Документы / код |
|---|---|---|
| BPH (внешняя система, Brokerage Portfolio History) | Новый endpoint месячной сводки купонов/дивидендов (контракт проектируем) | `repositories/ИО/history-ops/src/main/swagger/bph/bph.yml`; `analytics/02-Modules/MOD-001-history-ops/integrations/bph.md` |
| history-ops (HO) — агрегация | Новый parallel source-gateway к ручке BPH; не меняет ленту КД | `repositories/ИО/history-ops/.../adapter/bph/linked_events/BphLinkedOperationsGateway.java`, `BphClient.java`, `service/operation/SourceOperationTradeService.java` |
| history-ops-screen-api (BDUI-композит) | Новая секция на экране ленты и карточки инструмента | `analytics/02-Modules/MOD-002-history-ops-screen-api/behavior/composite-feed-backend.md`; `repositories/ИО/history-ops-screen-api/.../composite/sections/feed/section/creators/AbstractSectionCreator.java` |
| Данные (справочник) | Маппинг `CA_CASH_MOVEMENT` → `coupon`/`coupon_output`/`dividend_input`/`dividend_output` (не меняется, используется как опора) | `db-export/БД ИО.md` (таблицы `type`, `operation_type`, `bph`, `operation`) |
| Соседние фичи (reference) | Паттерн «новый BPH-параметр + новая секция композита» | `Feature-writing/composite-active-order-commission/*.md`, `Feature-writing/bph-linked-events-yield/*.md` |

## Релевантная аналитика и спеки

| Документ | Что описывает | Почему релевантно задаче |
|---|---|---|
| `analytics/02-Modules/MOD-001-history-ops/integrations/bph.md` | Интеграция HO↔BPH: `GET_LINKED_EVENTS`, `GET_OPERATIONS_WITH_DETAILS`, заголовки `rqUID`/`systemName`, приоритет слияния OG→linked→with-details | Контракт и паттерн вызова BPH; сюда добавляется новая ручка |
| `analytics/02-Modules/MOD-001-history-ops/integrations/corp-actions.md` | `CA_CASH_MOVEMENT` как BPH-тип денежных КД; маппинг type/subtype/additionalType → типы МП | Подтверждает, что `CA_CASH_MOVEMENT` — тип-носитель купонов/дивидендов |
| `analytics/02-Modules/MOD-001-history-ops/behavior/feed-orchestration.md` | Оркестрация ленты: параллельные вызовы источников, `Mono.zip`, `bcDataComplete`, `failOperationTypes`, `RqCoordinator` | Паттерн добавления параллельного source-запроса в общий merge |
| `analytics/02-Modules/MOD-001-history-ops/behavior/operation-type-catalog.md` | Маршрутизация источников по `operationTypes`; `failOperationTypes` | Куда «встанет» новый запрос и как сообщать о его недоступности |
| `analytics/02-Modules/MOD-001-history-ops/behavior/bph-response-processing.md` | DB-aware маппинг BPH lead → МП (`subtypesAndStatuses`, `additionalTypes`) | Как BPH-ответ нормализуется; релевантно для формы ответа новой ручки |
| `analytics/02-Modules/MOD-001-history-ops/behavior/instrument-card-queries.md` | Карточка инструмента: `instrumentFilter`, 24 типа операции, раздел «История» | Вторая точка отображения новой секции |
| `analytics/02-Modules/MOD-002-history-ops-screen-api/behavior/composite-feed-backend.md` | Сборка экрана композита: `screenData` + `sections`, типы секций `history.feed.*`, `failedOperationType` | Куда добавляется новая секция ленты |
| `Feature-writing/composite-active-order-commission/composite-active-order-commission.md` | Ближайший аналог: новый BPH-параметр (linked events) + шильдик на feed-карточке + фича-тогл | Шаблон структуры фичи «параллельный источник → композит» |
| `Feature-writing/bph-linked-events-yield/bph-linked-events-yield.md` | Подключение `GET_LINKED_EVENTS` через `BphLinkedOperationsGateway`, приоритет слияния | Образец описания gateway и сценариев |

## Релевантный код

| Файл | Компонент (класс / метод / endpoint) | Текущее поведение | Почему важно для фичи |
|---|---|---|---|
| `repositories/ИО/history-ops/src/main/swagger/bph/bph.yml` | OpenAPI `BPH Incoming-gateway`; paths `/operations`, `/operations-with-details`, `/operation/details`, `/operation-types/*`, `/operations/linked-events` | **Нет** endpoint месячной сводки (grep `summary`/`monthly` даёт только тексты `summary:` OpenAPI-описаний, не пути). `linked-events` — POST `/api/v1/incoming-gateway/operations/linked-events` (схема `RequestLinkedData` → `LinkedEventsData`) | Контракт новой ручки проектируем; образец формы — `RequestLinkedData`/`LinkedEventsData` |
| `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/adapter/bph/BphClient.java` | `getLinkedEvents` → `LINKED_EVENTS_URL = "/api/v1/incoming-gateway/operations/linked-events"`; `getOperations` → `/operations-with-details`; `getConfig` → `/operation-types`; заголовки `systemName: history_ops`, `rqUID` | WebClient-клиент с тремя методами-вызовами BPH | Новая ручка потребует нового метода (и URL) в `BphClient` |
| `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/adapter/bph/linked_events/BphLinkedOperationsGateway.java` | `BphLinkedOperationsGateway extends AbstractSplitStatusGateway<..., BphRawLinkedEventsWrapper, String>`; `getOperationsInternal`; `eventType()="GET_LINKED_EVENTS"`; `exSystem()="BPH"`; `createRequest` строит `RequestLinkedData` (agreements, startSearchDate/endSearchDate, pageSize=`bphProperties.pageSizeForLinkedEvents()`, `FilterDateEnum`) | Образец gateway для **параллельного source-запроса** к BPH (не сам обмен) | Проектируемый gateway месячной сводки должен следовать этой же модели (`AbstractSplitStatusGateway`/`getOperationsInternal`) |
| `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/service/operation/SourceOperationTradeService.java` | `getOperationsFromSources`; `Mono.zip(..., dealsFromOg, bphLinkedEvents)` — параллельное объединение источников | Параллельный запуск источников через reactor `Mono.zip`; результат в `TradeOperations.bphLinkedOperations` | Точка, где подключается параллельный вызов новой ручки |
| `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/service/operation/SourceOperationService.java` | `Mono.zip` по источникам простых операций; `SourceOperations` | Аналогичный параллельный запуск для простых операций (BPH simple types) | Параллельный запрос сводки может встать сюда либо в trade-ветку |
| `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/adapter/bph/BphOperationWrapper.java` | `CA_CASH_MOVEMENT = "CA_CASH_MOVEMENT"`; `COUPON_DIVIDEND_SUBTYPES = {INTEREST_PAYMENT_CREDIT, CASH_DIVIDEND_CREDIT, CASH_DIVIDEND_DEBIT, INTEREST_PAYMENT_DEBIT}` | Кодовая константа-перечень BPH-субтипов купонов/дивидендов | Фиксирует подмножество, по которому считается сводка |
| `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/adapter/bph/common/BphCommonWrapper.java` | `isCouponDividendOperation()` = `"CA_CASH_MOVEMENT".equals(originalType) && COUPON_DIVIDEND_SUBTYPES.contains(bphType)` | Предикат определения операции купона/дивиденда | Логика отбора операций, агрегируемых в сводку |
| `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/service/FailOperationTypeService.java` | `DG_DEPENDENT_OPERATION_TYPES` включает `DIVIDEND_INPUT`, `DIVIDEND_OUTPUT`, `COUPON` | Типы, влияющие на полноту/ошибки | Учесть `COUPON_OUTPUT` и поведение при недоступности новой ручки |
| `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/configuration/properties/BphProperties.java` | `@ConfigurationProperties(prefix="app-config.bph")`: `deadline`, `url`, `pageSizeForLinkedEvents`, `pageSizeForTrades` | Конфиг BPH-вызовов | Потребуется новый ключ (напр. pageSize/URL) для новой ручки |
| `repositories/ИО/history-ops-screen-api/src/main/java/com/sberbank/si20/history/ops/controllers/ScreenController.java` | REST `/history/api/public/v1/screens/feed` (`getFeed`), `/operationDetails/{id}` (`getOperationById`) | Две REST-точки композита; feed собирает экран ленты | Новая секция добавляется в сборку `feed`; карточка инструмента — через `InstrumentFeedFilter` |
| `repositories/ИО/history-ops-screen-api/src/main/java/com/sberbank/si20/history/ops/composite/sections/feed/section/creators/AbstractSectionCreator.java` | `history.feed.operationActive` / `history.feed.operation`; `TitleSectionCreator` → `history.feed.title` | Типы секций ленты композита | Новая секция получит свой тип `history.feed.*` |
| `repositories/ИО/history-ops-screen-api/src/main/java/com/sberbank/si20/history/ops/dtos/InstrumentFeedFilter.java` (+ `AbstractFeedFilter` subtype `INSTRUMENT`) | Фильтр карточки инструмента (`isin`, `ticker`) | Композит поддерживает фильтр по инструменту в feed | Карточка инструмента (раздел «История») обслуживается через feed с `INSTRUMENT`-фильтром |

## Данные (БД, выгрузки)

| Таблица / поле / запрос | Где найдено | Текущее устройство | На что влияет фича |
|---|---|---|---|
| `type` | `db-export/БД ИО.md` (таблица `type`, строки 1–9) | `id=1 → CA_CASH_MOVEMENT`; также `CASH_FLOW`, `NON_TRADE_ORDERS`, `SM_SECURITY_MOVEMENT`, `VAR_MARGIN`, `COMMISSION`, `TAXES`, `MONEY_DIAS`, `CA_SECURITIES_MOVEMENT` | Подтверждает `CA_CASH_MOVEMENT` как тип-носитель купонов/дивидендов |
| `operation_type` | `db-export/БД ИО.md` (таблица `operation_type`) | `id=5 coupon`, `id=6 dividend_input`, `id=11 dividend_output`, `id=14 coupon_output` | Четыре типа МП, агрегируемые в месячную сводку |
| `bph` | `db-export/БД ИО.md` (таблица `bph`, строки 1637–1640) | `id=1 INTEREST_PAYMENT_CREDIT → type_id 1 (CA_CASH_MOVEMENT)`, `id=2 CASH_DIVIDEND_CREDIT`, `id=3 CASH_DIVIDEND_DEBIT`, `id=4 INTEREST_PAYMENT_DEBIT` (все `type_id=1`) | Субтипы BPH, по которым считается сводка |
| `operation` | `db-export/БД ИО.md` (таблица `operation`, строки 1695–1705) | `id=5 → operation_type 5 (coupon), bph 1 (INTEREST_PAYMENT_CREDIT) — «Зачисление купона»`; `id=6 → 6/2 «Зачисление дивидендов»`; `id=12 → 11/3 «Списание дивидендов»`; `id=15 → 14/4 «Списание купонов»` | Связь тип МП ↔ субтип BPH (CREDIT=зачисление, DEBIT=списание) |
| `screen` / `screen_data` / `section` | `db-export/БД ИО.md` (screen-api) | `screen_data id=2 operationsHistory` с tabs `ACTIVE`/`HISTORY`; `screen` id=71/72 `HISTORY_OPS_FEED_SCREEN`; карточки контента купонов/дивидендов в `content` (id 6–9) | Структура экрана ленты и место новой секции |
| `info` | `db-export/БД ИО.md` (таблица `info`) | `id=5` (Зачисление купона) `comment=$name$`; `id=6/12/15` — купон/дивиденды | Отображаемые имена карточек купонов/дивидендов (не меняются) |

## Интеграции и контракты, которые нужно учесть

- **BPH REST** (синхронный POST, JSON): точка входа `bph-incoming-gateway`. Заголовки `rqUID`, `systemName` (`history_ops` в коде `BphClient`, в analytics `si2-ops` — расхождение, см. Q-04). Существующие обмены: `GET_LINKED_EVENTS` (`/operations/linked-events`), `GET_OPERATIONS_WITH_DETAILS` (`/operations-with-details`), `GET_OPERATION_TYPES` (`/operation-types`).
- **Паттерн подключения** (образец из брифа): `BphLinkedOperationsGateway.getOperationsInternal` → `bphClient.getLinkedEvents` → `RequestLinkedData`. Для новой ручки — аналогичный gateway + метод в `BphClient` + URL в `bph.yml`.
- **Параллельность**: источники объединяются через `Mono.zip` (`SourceOperationTradeService`, `SourceOperationService`); новая сводка подключается как ещё один параллельный источник, не в общий merge ленты (это агрегат, не операция).
- **Термины домена**: `CA_CASH_MOVEMENT` (BPH type денежных КД), `coupon`/`coupon_output`/`dividend_input`/`dividend_output` (типы МП), `history-ops-screen-api` = BDUI-композит/BFF, `GET_LINKED_EVENTS` ≠ `GetLinkedEvents` (обмен BPH ≠ метод gateway).
- **Границы**: КД (DCA/ECM/DCM) и карточки купонов/дивидендов в ленте НЕ заменяются; новая секция — агрегат, не новая операция и не деталка.

## Ограничения и риски текущего состояния

- **Контракта нет**: `bph.yml` (1492 строки) не содержит endpoint месячной сводки; все существующие paths перечислены в § Релевантный код. Риск: форму запроса/ответа фиксируем мы, BPH реализует по спеке — контракт должен быть самодостаточным (service/rpc/message/поля).
- **Расхождение analytics vs код** по `systemName`: analytics `bph.md` декларирует `si2-ops`, код `BphClient` шлёт `history_ops` (технический факт — побеждает код). Зафиксировано как Q-04.
- **Обратная совместимость**: лента, КД и карточки купонов/дивидендов должны остаться без изменений; новая секция — аддитивная.
- **Partial failure**: при недоступности новой ручки поведение (`bcDataComplete`, показ секции, fallback) не определено в AS IS — открытый вопрос.
- **Карточка инструмента**: раздел «История» обслуживается через `instrumentFilter`; агрегат по инструменту и по всему портфелю может различаться по входным фильтрам (см. Q-03).

## Что учесть при написании фичи

- Использовать паттерн `composite-active-order-commission` и `bph-linked-events-yield` для структуры: BR/CN + Use Case AS IS/TO BE + контракт-таблицы + sequence-диаграмма.
- Для контракта BPH обязательны service / rpc (endpoint path) / message (request/response) / поля; сослаться на `RequestLinkedData`/`LinkedEventsData` как образец.
- Зафиксировать набор агрегируемых типов МП: `coupon`, `coupon_output`, `dividend_input`, `dividend_output` (и их BPH-субтипы `INTEREST_PAYMENT_CREDIT/DEBIT`, `CASH_DIVIDEND_CREDIT/DEBIT`).
- Новая секция композита: определить код/тип секции (`history.feed.*` или новый), место на экране ленты и на карточке инструмента; разделить «лента» и «карточка инструмента».
- Отдельно описать поведение при недоступности/ошибке новой ручки (partial failure, `failOperationTypes`-аналог, скрытие секции) и фича-тогл (по образцу соседних фич — default OFF).
- Учесть, что агрегат не является `PortfolioOperationType` и не попадает в `operation_type`/`operation` маппинг БД — это отдельная сущность экрана.

### Актуализация после resolve (2026-09-25)

Решения из resolve, которые писатель и ревьюер должны считать актуальнее исходного current-state:

- GAP-UCAS-01: Состав источников ленты AS IS зафиксирован: `GET_LINKED_EVENTS` + `GET_OPERATIONS_WITH_DETAILS` (носитель `CA_CASH_MOVEMENT`)
- GAP-UCAS-03: Пустая лента → пустое состояние (принято как есть)
- GAP-UCTB-01: Endpoint `POST /api/v1/incoming-gateway/operations/monthly-summary`
- GAP-UCTB-06: Пустой месяц → нулевые суммы (bucket `0`)
- GAP-CONS-01: Имя/path/форма request/response зафиксированы
- GAP-INT-01: Endpoint сигнатура зафиксирована
- GAP-INT-02: Request `RequestMonthlySummaryData` (период + `agreements`)
- GAP-INT-03: Response `MonthlySummaryData` (`total` + разбивка)
- GAP-INT-06: Пустой результат → нулевые суммы (bucket `0`)
- GAP-ALG-01: Имя/path ручки зафиксировано
- GAP-ALG-06: Пустой месяц → нулевые суммы (bucket `0`)
- GAP-DM-03: Форма `MonthlySummary` зафиксирована
- GAP-MAP-01: Имена полей `MonthlySummaryData` зафиксированы
- GAP-NFR-04: Новый ключ конфига в `BphProperties` (URL/pageSize)
- GAP-OBS-01: `eventType = GET_MONTHLY_SUMMARY`
- GAP-OBS-02: Маскирование сумм по `LoggerConstants.HIDDEN_TEXT`
- GAP-CONS-02: `systemName = history_ops`
- GAP-INT-04: `systemName = history_ops` (код `BphClient`)
- GAP-UCAS-02: Частичная лента — существующий механизм `bcDataComplete`/`failOperationTypes`
- GAP-UCTB-04: Секция скрывается целиком; не влияет на полноту ленты

**Якоря полей из актуальной SPEC:**

`coupon`, `coupon_output`, `dividend_input`, `dividend_output`, `CA_CASH_MOVEMENT`, `bph.yml`, `BphLinkedOperationsGateway`, `GetLinkedEvents`, `GET_LINKED_EVENTS`, `isin`, `ticker`, `INSTRUMENT`

См. также § «Закрытые вопросы» ниже — не переспрашивать закрытые Q.
## Открытые вопросы / что проверить

| ID | Вопрос | Где искать ответ |
|---|---|---|
| Q-01 | Имя и path нового BPH-endpoint месячной сводки (напр. `/api/v1/incoming-gateway/operations/monthly-summary` или иной), а также форма request/response (период, валюта, разбивка coupon/dividend_input/dividend_output/coupon_output) | Владельцы контракта BPH; фиксируется в спеке; аналог — `bph.yml` `/operations/linked-events` |
| Q-02 | Какой идентификатор/тип секции получит агрегат в композите (новый `history.feed.*`-код) и входит ли он в общий маппинг `section`/`content` БД screen-api или рендерится отдельно | `repositories/ИО/history-ops-screen-api/.../composite/sections/feed/section/creators/*`; `db-export/БД ИО.md` (screen-api `section`) |
| Q-03 | Карточка инструмента (раздел «История»): агрегат считается по `instrumentFilter` (isin/ticker) или по всему портфелю? Различается ли сводка «лента» vs «карточка инструмента» | `analytics/.../behavior/instrument-card-queries.md`; владелец композита screen-api |
| Q-04 | Расхождение `systemName` для BPH-вызовов: analytics `bph.md` = `si2-ops`, код `BphClient` = `history_ops`. Какой использовать для новой ручки | `repositories/ИО/history-ops/.../BphClient.java` (побеждает код); владельцы BPH incoming-gateway |
| Q-05 | Поведение при недоступности/таймауте новой ручки: скрывать секцию целиком, показывать пустую, влиять ли на `bcDataComplete`/`failOperationTypes` ленты | Паттерн `FailOperationTypeService`; `analytics/.../feed-orchestration.md` § partial failure |
| Q-06 | Наличие фича-тогла для новой секции и default (по образцу соседних фич — OFF до готовности BPH) | `repositories/ИО/history-ops-screen-api` session toggles; `Feature-writing/composite-active-order-commission` D-07 |
| Q-07 | Валюты и округление суммы месячной сводки (мультивалютный портфель: RUB/USD/SUR), формат `{value, currency}` | Паттерн `totalPrice {value, currency}` в `bph.md`; владельцы BPH |

## Закрытые вопросы

| ID | Дата | Решение | Где в spec | Источник |
|----|------|---------|------------|----------|
| Q-01 | 2026-09-25 | Контракт зафиксирован: `POST /api/v1/incoming-gateway/operations/monthly-summary`, request `RequestMonthlySummaryData` (период + `agreements`), response `MonthlySummaryData` (`total` + `coupon`/`couponOutput`/`dividendInput`/`dividendOutput`, `{value,currency}`); `eventType=GET_MONTHLY_SUMMARY`; новый ключ конфига в `BphProperties`; пустой месяц → нули (bucket `0`); логи с маскированием сумм по `LoggerConstants.HIDDEN_TEXT` | §4.1.1, §4.2.2, §4.2.3, §4.2.4, §5 | /resolve-gaps (D-01) |
| Q-04 | 2026-09-25 | `systemName = history_ops` (код `BphClient`; analytics `si2-ops` — снято) | §2 (CN-05), §4.1.1 | /resolve-gaps (D-02) |
| Q-05 | 2026-09-25 | При недоступности/таймауте/ошибке ручки — скрывать секцию целиком; лента и КД без изменений; не влияет на `bcDataComplete`/`failOperationTypes` ленты | §1.2, §1.3, §2 (CN-12), §4.2.2, §4.2.4, §5 | /resolve-gaps (D-03) |
| Q-03 | 2026-09-25 | Сводка на карточке инструмента — по `instrumentFilter` (`agreements` = isin/ticker), только по выбранному инструменту; отличается от сводки ленты (весь портфель) | §2 (CN-10), §4.2.2, §4.2.4 | /resolve-gaps (D-04) |
| Q-07 | 2026-09-25 | Отдельные суммы по RUB/USD/SUR без пересчёта; `value` decimal, округление до 2 знаков; формат `{value, currency}` | §2 (CN-11), §4.1.1, §4.2.3, §4.2.4, §5 | /resolve-gaps (D-05) |
| Q-02 | 2026-09-25 | Код секции `history.feed.monthlySummary` (по образцу `history.feed.*`), транзитный рендер — без новой строки в `section`/`content`/`screen_section` БД screen-api; отдельные UI-события и секция-специфичная метрика не вводятся | §1.3, §4.2.2, §4.2.3, §4.2.4, §5 (Метрики) | /resolve-gaps (D-06) |
| Q-06 | 2026-09-25 | Фича-тогл `enable_monthly_summary`, default `false` (OFF) | §2 (CN-09), §4.2.2, §4.2.4, §5 (Тогглы, Конфигурация) | /resolve-gaps (D-07) |
| Q-08 | 2026-09-25 | Количественные NFR/SLO не задаются — секция аддитивна, класс запроса не меняется (допущение CN-13); prod-поля лога `service`/`environment` не фиксируются | §2 (CN-13), §5 (5.2.1–5.2.7, Надёжность, Логирование) | /resolve-gaps (D-08) |
| Q-09 | 2026-09-25 | Инициатор — Product Owner истории операций, дата — дата брифа (2026-09-25); метрики улучшения и срок/релиз не заданы (допущение CN-14) | §1.1, §2 (CN-14) | /resolve-gaps (D-09) |

# Контекст для фичи: bph-coupons-dividends-monthly-summary

## Задача (бриф)

> Новая ручка BPH «Сумма купонов и дивидендов за месяц» (BPH monthly summary). Контракта ещё нет (bph.yml не содержит endpoint) — ручку проектируем мы, коллеги BPH реализуют по спеке. Купоны и дивиденды как операции уже есть (CA_CASH_MOVEMENT / типы МП coupon, coupon_output, dividend_input, dividend_output); новым является именно месячная сводка. history-ops подключает параллельный source-запрос к новой ручке вместе с основной историей (лента); образец подключения — gateway BphLinkedOperationsGateway (GetLinkedEvents), не сам GET_LINKED_EVENTS. Корпоративные действия (DCA/ECM/DCM) и карточки купонов/дивидендов в ленте НЕ заменяются. history-ops-screen-api (BDUI-композит) добавляет новую секцию на экране ленты и на карточке инструмента (раздел «История»); это агрегат, не новая операция и не деталка.

**Трактовка:** это интеграционно-экранная фича. Существующие операции «купон/дивиденд» (и их карточки/деталки) уже реализованы; добавляется **новая агрегатная ручка BPH** (месячная сумма купонов и дивидендов), которую history-ops запрашивает параллельно с основными источниками ленты (по образцу подключения `BphLinkedOperationsGateway`), а композит `history-ops-screen-api` отображает результат как отдельную секцию на ленте и на карточке инструмента. Контракт BPH для новой ручки отсутствует — это TO BE, который фиксируется в спеке и передаётся команде BPH.

## Затронутые области

| Область | Что затрагивается | Документы / код |
|---|---|---|
| BPH (внешняя система) | Новый endpoint агрегата «сумма купонов и дивидендов за месяц»; контракт в `bph.yml` | `repositories/ИО/history-ops/src/main/swagger/bph/bph.yml` (текущий, без endpoint) |
| history-ops | Новый parallel source-запрос к ручке BPH + конвертация в ответ композита; НЕ заменяет существующие типы | `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/adapter/bph/…`; `analytics/02-Modules/MOD-001-history-ops/integrations/bph.md`, `behavior/feed-orchestration.md` |
| history-ops-screen-api (BDUI-композит) | Новая секция на ленте и на карточке инструмента (раздел «История») | `analytics/02-Modules/MOD-002-history-ops-screen-api/behavior/composite-feed-backend.md`; `repositories/ИО/history-ops-screen-api/src/test/resources/db/init-test-screens.sql` |
| Исходящий контракт history-ops | Возможное расширение ответа под агрегат | `repositories/ИО/history-ops/src/main/swagger/history/history.yml` |

## Релевантная аналитика и спеки

| Документ (analytics/, Feature-writing/) | Что описывает | Почему релевантно задаче |
|---|---|---|
| `analytics/02-Modules/MOD-001-history-ops/integrations/bph.md` | Интеграция HO↔BPH: адаптеры `BphGateway`/`BphTradesGateway`/`BphLinkedOperationsGateway`, обмены `GET_LINKED_EVENTS` и `GET_OPERATIONS_WITH_DETAILS`, заголовки `rqUID`/`systemName` | Канонический контекст подключения к BPH; образец контракта и приоритетов слияния |
| `analytics/02-Modules/MOD-001-history-ops/integrations/corp-actions.md` | КД: `CA_CASH_MOVEMENT` (денежные КД) и `SM_SECURITY_MOVEMENT`; meet (934) + BPH CA (3131) | Подтверждает `CA_CASH_MOVEMENT` как тип BPH для купонов/дивидендов и что DCA/ECM/DCM — отдельные каналы |
| `analytics/02-Modules/MOD-001-history-ops/behavior/feed-orchestration.md` | Оркестрация ленты: параллельные source-запросы, маршрутизация по operationTypes, `RqCoordinator` пагинация, partial failure (`bcDataComplete`, `failOperationTypes`) | Место встраивания нового parallel-запроса; правила полноты и сортировки |
| `analytics/02-Modules/MOD-001-history-ops/behavior/operation-type-catalog.md` | Маппинг типов МП ↔ BPH/BC/OG; `failOperationTypes` | Подтверждает, что coupon/dividend идут через `GET_OPERATIONS_WITH_DETAILS` |
| `analytics/02-Modules/MOD-001-history-ops/behavior/instrument-card-queries.md` | Раздел «История» на карточке инструмента: `instrumentFilter`, 24 типа (включая coupon/coupon_output/dividend_input/dividend_output) | Точка размещения новой секции на карточке инструмента |
| `analytics/02-Modules/MOD-002-history-ops-screen-api/behavior/composite-feed-backend.md` | Сборка ленты композита: `screenData` + `sections`, шаблоны секций PostgreSQL | Место добавления новой секции на экране ленты |
| `Feature-writing/bph-linked-events-yield/bph-linked-events-yield.md` | Sibling-фича: новое поле BPH → gateway → конвертеры → `history.yml` → композит | Ближайший аналог сквозного проброса нового BPH-данного до экрана; паттерн DTO-регенерации из OpenAPI |

## Релевантный код

| Файл | Компонент (класс / метод / endpoint / proto) | Текущее поведение | Почему важно для фичи |
|---|---|---|---|
| `repositories/ИО/history-ops/src/main/swagger/bph/bph.yml` | OpenAPI BPH Incoming-gateway; paths `/operations`, `/operations-with-details`, `/operation/details`, `/operation-types*`, `/operations/linked-events` | Контракт ленты, детализации и словарей BPH; **endpoint месячной сводки отсутствует** (grep по `monthly`/`summary` даёт только описания `summary:` эндпоинтов) | Место, где фиксируется новый контракт агрегата (TO BE) |
| `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/adapter/bph/BphClient.java` | `getOperations()`, `getLinkedEvents()`, `getConfig()` | WebClient-клиент к BPH, ровно три вызова; метод месячной сводки отсутствует | Сюда добавляется вызов новой ручки (по образцу `getLinkedEvents`) |
| `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/adapter/bph/linked_events/BphLinkedOperationsGateway.java` | `BphLinkedOperationsGateway extends AbstractSplitStatusGateway`; `eventType()="GET_LINKED_EVENTS"`, `exSystem()="BPH"`, `ruleKey()=BPH_GET_LINKED_EVENTS`; `enabled()` = `isBphLinkedCommissionsEnabled() || isBphLinkedTradingOpsEnabled()` | Parallel gateway для связанных сущностей; `createRequest()` формирует `RequestLinkedData` | **Образец** подключения нового source-запроса (структура gateway, тоggl, `RpcNamesForRequestCondition`) |
| `repositories/ИО/history-ops/src/main/swagger/bph/bph.yml` → `RequestLinkedData` (стр. ~1053) | `agreements` (required, maxItems 100), `startSearchDate`, `endSearchDate`, `dateForFilter` (`FilterDateEnum`), `page` (0–1000), `pageSize` (1–4000) | Тело запроса `GET_LINKED_EVENTS` | Ориентир для формы запроса новой агрегатной ручки |
| `repositories/ИО/history-ops/src/main/swagger/bph/bph.yml` → `OperationData` (стр. ~1088) | `type`, `subType`/`subtype`, `additionalType`, `formationDate`, `eventDate`, `externalSystemId`, `price`, `totalPrice`, `quantity`, `status`, `instrument` | Модель lead операции BPH | Показывает, из каких полей сейчас собирается операция (для агрегата модель иная — см. Q-01) |
| `repositories/ИО/history-ops/src/test/java/com/sberbank/si20/history/ops/CommissionTest.java` | константа `app-config.operation-cache.default-value` (JSON маппинга типов) | Маппинг `operation_type` → `type`/`bphType`/`bph_subtype`/`bc_subtype` | Подтверждает типы: `coupon`, `coupon_output`, `dividend_input`, `dividend_output` → `type=CA_CASH_MOVEMENT` |
| `repositories/ИО/history-ops/src/main/swagger/history/history.yml` | Исходящий контракт history-ops | Данные операций для клиента/композита | Точка возможного расширения ответа под агрегат (если агрегат пробрасывается через HO-контракт, а не отдельно) |

## Данные (БД, выгрузки)

| Таблица / поле / запрос | Где найдено | Текущее устройство | На что влияет фича |
|---|---|---|---|
| `bph` (24 кол.: `id`, `subtype`, `type_id`, `is_active`) | `db-export/БД ИО.md` (строки 19, 1417, 1630) | Справочник связок `type/subtype` BPH с флагом активности | Не меняется фичей; подтверждает, что купоны/дивиденды уже маппятся через БД |
| `bph_bc` (14 кол.: `id`, `bph_type_id`, `bph_subtype`, `is_active`) | `db-export/БД ИО.md` (20, 1662) | Справочник legacy BC-подтипов в терминах BPH | Не меняется |
| `operation` (26 кол.: `id`, `operation_type_id`, `bc_id`, `bph_id`, `name`) | `db-export/БД ИО.md` (21, 1454, 1686) | Центральная таблица маппинга тип ИО ↔ источник | Не меняется; агрегат — не новая операция, отдельной строки не предполагает (Q-05) |
| `type` (9 кол.) | `db-export/БД ИО.md` (1412, 1456) | Семейства операций источников (`CA_CASH_MOVEMENT` и др.) | Ориентир: `CA_CASH_MOVEMENT` — семейство денежных КД |
| Таблицы `status_to_operation`, `bc_status_to_operation`, `cancellation_bph` | `db-export/БД ИО.md` (1421–1423) | Маппинг статусов и правила отмены | Не затрагиваются |

## Интеграции и контракты, которые нужно учесть

- **BPH — протокол REST/JSON, синхронный, заголовки `rqUID` (uuid) и `systemName` (`si2-ops`)** (`analytics/…/integrations/bph.md`; в `BphClient` значение `systemName` в коде — `history_ops`). В спеке зафиксировать согласованное значение.
- **Существующие обмены BPH:** `GET_LINKED_EVENTS` (`POST /operations/linked-events`) и `GET_OPERATIONS_WITH_DETAILS` (`POST /operations-with-details`). Новая ручка — третий обмен, по образцу подключения `BphLinkedOperationsGateway` (eventType/`RpcNamesForRequestCondition`/feature-флаг).
- **Маршрутизация источников в ленте:** coupon/coupon_output/dividend_input/dividend_output сейчас идут через `GET_OPERATIONS_WITH_DETAILS` + mapping `bph_bc` (`BphGateway`, `BphBcFilterService`) — см. `feed-orchestration.md`. Агрегат — новый параллельный запрос, НЕ замена этих вызовов.
- **Корпоративные действия не заменяются:** DCA (`corp_actions_*` gateways: depository_bids/meet/sec_transfers), ECM (`IpoSpoGateway`: ipo/spo), DCM (`IboGateway`: ibo) — отдельные источники (`corp-actions.md`, `feed-orchestration.md`).
- **Карточки купонов/дивидендов в screen-api уже есть:** `HISTORY_OPS_COUPON_DETAILS_SCREEN`, `HISTORY_OPS_COUPON_OUTPUT_DETAILS_SCREEN`, `HISTORY_OPS_DIVIDEND_INPUT_DETAILS_SCREEN`, `HISTORY_OPS_DIVIDEND_OUTPUT_DETAILS_SCREEN` (по `operationType` = `COUPON`/`COUPON_OUTPUT`/`DIVIDEND_INPUT`/`DIVIDEND_OUTPUT`) — `repositories/ИО/history-ops-screen-api/src/test/resources/db/init-test-screens.sql`.
- **Композит ленты:** REST `POST /history/api/public/v1/screens/feed` → gRPC `getHistoryOperationsFeed` → `SEND_OPERATIONS` → `screenData` + `sections[]` (шаблоны секций в PostgreSQL `sections`). Новая секция — это новый шаблон/блок `sections`, не карточка операции.
- **Фильтр ленты** уже содержит группу «Купоны и дивиденды» с кодами `DIVIDEND_INPUT`, `DIVIDEND_OUTPUT`, `COUPON`, `COUPON_OUTPUT` (`init-test-screens.sql`, JSON `screenData`).

## Ограничения и риски текущего состояния

- **Контракта нет.** В `bph.yml` нет endpoint агрегата; `BphClient` не имеет метода. Все атрибуты ручки (path, request/response, типы агрегата, валюта, период) — TO BE, согласуются с командой BPH (см. Q-01…Q-04).
- **Агрегат ≠ операция.** Существующая модель оперирует lead-операциями (`OperationData`/`DetailsData`); месячная сумма — иная структура. Нельзя переиспользовать текущие конвертеры lead без адаптации (Q-05).
- **Обратная совместимость.** Новая ручка должна быть опциональной: при её отсутствии/ошибке лента и карточка инструмента работают как раньше (partial failure, `bcDataComplete`/`failOperationTypes`). Не должна ломать существующие DCA/ECM/DCM и карточки купонов/дивидендов.
- **Фиче-флаг.** Parallel-запросы в HO управляются тоggl (пример: `isBphLinkedCommissionsEnabled()`/`isBphLinkedTradingOpsEnabled()` у `BphLinkedOperationsGateway`). Для новой ручки нужен свой toggle (Q-08).
- **Пагинация/полнота.** Если агрегат участвует в ленте — нужно решить, входит ли он в `RqCoordinator`/`bcDataComplete` или это независимая секция с собственным жизненным циклом (Q-06, Q-07).

## Что учесть при написании фичи

- Фиксировать контракт новой ручки BPH в `bph.yml` (path, method, request/response schema, `FilterDateEnum`/период), по образцу существующих `RequestLinkedData`/`ResponseStatusData`/`data[]`.
- Спроектировать новый gateway в history-ops по образцу `BphLinkedOperationsGateway`: `exSystem()="BPH"`, собственный `eventType()`/`RpcNamesForRequestCondition`, `enabled()` через feature-флаг, `BphClient`-метод.
- Определить, как агрегат попадает в композит: через расширение исходящего `history.yml`/`SEND_OPERATIONS` или отдельным полем/блоком ответа; и как `screen-api` рендерит новую секцию (`sections`-шаблон, не карточка операции).
- Явно зафиксировать, что DCA/ECM/DCM и карточки купонов/дивидендов не заменяются (против anti-паттерна «спека как implementation ticket» и «partial contract tables»).
- Ссылаться на sibling `bph-linked-events-yield` для сквозного паттерна (контракт → DTO-регенерация → gateway → конвертер → history.yml → композит).

### Актуализация после resolve (2026-09-16)

Решения из resolve, которые писатель и ревьюер должны считать актуальнее исходного current-state:

- Осталось открытыми к разрешению: ## Сессия 1 (2026-09-16)

Этап `needs-answer`: закрытий фактом нет — все гэпы батча 1 — подлинные
TO BE-решения по контракту новой ручки BPH (контракта в `bph.yml` нет, ручку
проектируем мы). Строки записаны в `DECISIONS`, spec **не** правился.
- ---------: ------------------
- Q-01 контракт ручки: GAP-GOAL-01, GAP-UCTB-01, GAP-INT-01, GAP-ALG-01, GAP-DM-01, GAP-MAP-01, GAP-NFR-01
- Q-02 объём агрегата: GAP-GOAL-02, GAP-UCTB-02, GAP-INT-02, GAP-ALG-02, GAP-DM-02, GAP-MAP-02
- Q-03 состав типов: GAP-GOAL-03, GAP-UCTB-03, GAP-INT-03, GAP-ALG-03, GAP-DM-03
- Q-04 период: GAP-GOAL-04, GAP-UCTB-04, GAP-INT-04, GAP-ALG-04, GAP-DM-04, GAP-MAP-06
- Q-10 systemName: GAP-GOAL-07, GAP-UCTB-10, GAP-CONS-04, GAP-INT-06, GAP-ALG-10, GAP-NFR-03
- GAP-GOAL-01, GAP-UCTB-01, GAP-INT-01, GAP-ALG-01, GAP-DM-01, GAP-MAP-01, GAP-NFR-01: Контракт `POST /api/v1/incoming-gateway/operations/coupons-dividends-monthly-summary`, схемы `RequestCouponsDividendsMonthlySummaryData`/`CouponsDividendsMonthlySummaryData`
- GAP-GOAL-02, GAP-UCTB-02, GAP-INT-02, GAP-ALG-02, GAP-DM-02, GAP-MAP-02: Агрегат по инструменту (`isin`), раздельно купоны/дивиденды, мультивалютный массив
- GAP-GOAL-03, GAP-UCTB-03, GAP-INT-03, GAP-ALG-03, GAP-DM-03: Только `coupon`/`coupon_output`/`dividend_input`/`dividend_output`
- GAP-GOAL-04, GAP-UCTB-04, GAP-INT-04, GAP-ALG-04, GAP-DM-04, GAP-MAP-06: Календарный месяц по `eventDate`, `period.startDate`/`period.endDate`
- GAP-GOAL-07, GAP-UCTB-10, GAP-CONS-04, GAP-INT-06, GAP-ALG-10, GAP-NFR-03: `systemName` = `history_ops`
- GAP-UCTB-05, GAP-INT-07, GAP-ALG-05, GAP-DM-05, GAP-MAP-03: Секция: `type`=`history.feed.couponsDividendsMonthlySummary`, `code`=`HISTORY_OPS_COUPONS_DIVIDENDS_MONTHLY_SUMMARY_SECTION`, `content.data`={period, couponTotals[], dividendTotals[], isin}; на ленте вверху, на карточке в «Истории»
- GAP-UCTB-06, GAP-INT-08, GAP-ALG-06, GAP-NFR-09, GAP-UCAS-01, GAP-OBS-01: Gateway: `eventType()`=`GET_COUPONS_DIVIDENDS_MONTHLY_SUMMARY`, `ruleKey()`=`bphGetCouponsDividendsMonthlySummary`, `exSystem()="BPH"`; не в RqCoordinator/пагинации, не кэшируется, запрашивается на каждой странице ленты
- GAP-UCAS-02, GAP-UCTB-07, GAP-CONS-01, GAP-INT-09, GAP-ALG-07, GAP-MAP-05, GAP-NFR-07, GAP-OBS-02, GAP-OBS-05: При недоступности/пустом: секция скрывается, лента не неполна (bcDataComplete/failOperationTypes не меняются), лог WARN
- GAP-UCTB-08, GAP-CONS-02, GAP-ALG-08, GAP-NFR-02: Feature-флаг `enableBphCouponsDividendsMonthlySummary` (+ enum FeatureToggleName), default false
- GAP-UCTB-09, GAP-CONS-03, GAP-INT-05, GAP-ALG-09, GAP-DM-06, GAP-MAP-04, GAP-NFR-12, GAP-OBS-04: Канал: расширение `OperationHistoryResponse` полем `couponsDividendsMonthlySummary` (агрегат целиком)
- (residual D-02): Лента: сводка по всем инструментам из соглашений клиента (запрос списком isin), секция = перечень инструментов с суммами
- GAP-GOAL-05, GAP-GOAL-06: Non-SMART: метрики/срок не заданы в брифе (улучшение UX)
- GAP-INT-10, GAP-NFR-04, GAP-NFR-06: test-default как AS IS: `deadline=50000ms`, без rate-limit/retry; auth scheme не объявлена (как у существующих)
- CH-01: A (D-17)
- CH-02: A (D-18)
- CH-03: A (D-19)
- CH-04: C (D-20)
- CH-05: B (D-21)
- CH-06: A (D-22)
- CH-07: A (D-23)
- CH-10: A (D-24)
- CH-11: C (D-25)
- CH-12: A (D-26)
- CH-14: A (D-27)
- CH-15: A (D-28)
- CH-13: —
- CH-18: —
- CH-08: Minor
- CH-09: Minor
- CH-16: Minor
- CH-17: Minor
- CH-19: Minor
- CH-20: Minor

**Якоря полей из актуальной SPEC:**

`agreements`, `failOperationTypes`, `screenData`, `Client`, `ScreenApi`, `HistoryOps`, `BPH`, `CorpActions`, `activate`, `deactivate`, `actor`, `participant`

См. также § «Закрытые вопросы» ниже — не переспрашивать закрытые Q.
## Открытые вопросы / что проверить

| ID | Вопрос | Где искать ответ |
|---|---|---|
| Q-01 | Финальный контракт новой ручки BPH: путь (`/api/v1/incoming-gateway/…`), HTTP-метод, поля запроса и структура ответа агрегата (сумма, валюта, месяц)? | Команда BPH; текущий `bph.yml` и смежные обмены `GET_LINKED_EVENTS`/`GET_OPERATIONS_WITH_DETAILS` |
| Q-02 | Что именно агрегирует ручка: сумма купонов+дивидендов по портфелю (все договоры) или на инструмент; раздельно ли купоны и дивиденды, по валютам или одной суммой? | Бриф владельца продукта; команда BPH |
| Q-03 | Какие типы операций входят в агрегат: только `coupon`/`coupon_output`/`dividend_input`/`dividend_output` или также другие `CA_CASH_MOVEMENT` (`redemption`, `funds_payment_*`, `liquidation_*`)? | Бриф; `corp-actions.md`, маппинг `CommissionTest.java` |
| Q-04 | Период агрегации: календарный месяц или скользящее окно; по какой дате считается месяц (`eventDate`/`formationDate`)? | Бриф; `bph.yml` `FilterDateEnum` |
| Q-05 | Как агрегат представлен в history-ops и screen-api: отдельная секция в ответе композита (не `operationType`, не деталка)? Нужен ли новый код секции/шаблон `sections`? | Команда history-ops-screen-api; `init-test-screens.sql`, `composite-feed-backend.md` |
| Q-06 | Как новый source-запрос встраивается в оркестрацию ленты: отдельный gateway с собственным `eventType`/toggle, участвует ли в `RqCoordinator` пагинации и `bcDataComplete`? | Команда history-ops; `BphLinkedOperationsGateway`, `feed-orchestration.md` |
| Q-07 | Поведение при недоступности ручки: скрывать секцию, показывать предупреждение (`failOperationTypes`) или считать ленту неполной? | Команда history-ops; `feed-orchestration.md` § Partial failure |
| Q-08 | Имя feature-флага для новой ручки (аналогично `bphGetLinkedEvents.active`)? | Команда history-ops; контекст `bph-linked-events-yield` |
| Q-09 | Нужно ли расширять исходящий `history.yml`/`SEND_OPERATIONS` под агрегат, или screen-api получает агрегат отдельным каналом? | Владельцы контрактов HO и screen-api |
| Q-10 | Значение `systemName` в новом запросе: `si2-ops` (по аналитике) или `history_ops` (по коду `BphClient`)? | `BphClient.java` vs `bph.md` — расхождение зафиксировать как согласование с BPH |
| Q-11 | Агрегат «по инструменту» (решение D-02) — как для **ленты** задаётся инструмент/список инструментов (`isin`)? Карточка инструмента очевидна (single `isin` из `instrumentFilter`); для ленты — нет. | Бриф владельца продукта; команда BPH / history-ops |

## Закрытые вопросы

| ID | Дата | Решение | Где в spec | Источник |
|----|------|---------|------------|----------|
| Q-01 | 2026-09-16 | Контракт: `POST /api/v1/incoming-gateway/operations/coupons-dividends-monthly-summary`, схемы `RequestCouponsDividendsMonthlySummaryData` / `CouponsDividendsMonthlySummaryData` | §4.1.1, §2 CN-02, §4.2.2, §4.2.3 | /resolve-gaps (D-01) |
| Q-02 | 2026-09-16 | Агрегат по инструменту (ключ `isin`), раздельно купоны/дивиденды, мультивалютный массив `PriceData[]` (`couponTotals`/`dividendTotals`); пустой результат — `data: []` | §4.1.1, §4.2.2, §4.2.3, маппинг | /resolve-gaps (D-02) |
| Q-03 | 2026-09-16 | Состав типов: только `coupon`/`coupon_output`/`dividend_input`/`dividend_output` | §4.1.1, §4.2.2, §4.2.3 | /resolve-gaps (D-03) |
| Q-04 | 2026-09-16 | Календарный месяц по `eventDate` (`EVENT_DATE`), форма `period.startDate`/`period.endDate` | §4.1.1, §4.2.2, §4.2.3, маппинг | /resolve-gaps (D-04) |
| Q-10 | 2026-09-16 | `systemName` = `history_ops` | §2 CN-01, §4.1.1, §4.2.2, §5.1, §5.4 | /resolve-gaps (D-05) |
| Q-05 | 2026-09-16 | Секция композита: `type`=`history.feed.couponsDividendsMonthlySummary`, `code`=`HISTORY_OPS_COUPONS_DIVIDENDS_MONTHLY_SUMMARY_SECTION`, `content.data`={`period`, `couponTotals[]`, `dividendTotals[]`, `isin`}; на ленте — вверху, на карточке — в разделе «История» | §1.3, §4.1.1.2, §4.2.2.4, §4.2.3, маппинг | /resolve-gaps (D-06) |
| Q-06 | 2026-09-16 | Gateway: `eventType()`=`GET_COUPONS_DIVIDENDS_MONTHLY_SUMMARY`, `ruleKey()`=`bphGetCouponsDividendsMonthlySummary`, `exSystem()="BPH"`; не участвует в `RqCoordinator`/пагинации, не кэшируется, запрашивается на каждой странице ленты | §4.1.1, §4.2.2.1, §5.3.1, §5.3.2 | /resolve-gaps (D-07) |
| Q-07 | 2026-09-16 | При недоступности/пустом: секция скрывается без предупреждения, лента НЕ неполна (`bcDataComplete`/`failOperationTypes` не меняются), лог WARN | §2 CN-03, §4.2.2, §5.2-reliability, §5.3.1 | /resolve-gaps (D-08) |
| Q-08 | 2026-09-16 | Feature-флаг `enableBphCouponsDividendsMonthlySummary` (+ enum `FeatureToggleName`), default `false` | §2 CN-04, §5.4, §5.5 | /resolve-gaps (D-09) |
| Q-09 | 2026-09-16 | Канал доставки: расширение `OperationHistoryResponse` полем `couponsDividendsMonthlySummary` (агрегат целиком) | §2 CN-05, §4.1.1.1, §4.2.2.3, §4.2.3, маппинг, §5.5 | /resolve-gaps (D-10) |
| Q-11 | 2026-09-16 | На ленте сводка по всем инструментам из соглашений клиента (запрос списком `isin`), секция = перечень инструментов с суммами | §1.3, §4.1.1, §4.2.2.1 | /resolve-gaps (D-11) |

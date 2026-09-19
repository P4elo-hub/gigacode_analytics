# Контекст для фичи: bph-linked-events-yield

## Задача (бриф)

> В интеграции `history-ops` ↔ BPH по `GetLinkedEvents` нужно:
> 1. добавить новый параметр в интеграцию;
> 2. читать из ответа BPH новый параметр «доходность» (рабочее имя поля — `yield`);
> 3. пробросить его на фронт;
> 4. учесть в композите BDUI (`history-ops-screen-api`).
>
> Имя `yield` выбрано как рабочее (бриф разрешает придумать имя). Финальное имя поля в каждом контракте нужно согласовать — фиксируй это как открытые вопросы Q-XX.

**Трактовка:** аддитивное расширение цепочки «источник → агрегатор → экран» одним признаком «доходность» на пути заявок из BPH linked events. Фича симметрична соседней `og-trading-order-yield` (та же «доходность», но на пути заявок из Order Gateway). «Параметр» в брифе = новое поле в контракте интеграции BPH `GetLinkedEvents` (ответ), которое читается в `history-ops`, пробрасывается сквозь исходящие контракты HO и отображается композитом BDUI. Это **current-state документ**: решения о финальном имени/формате не принимаются, а фиксируются как открытые вопросы Q-XX.

Память проекта (`memory/MEMORY.md`, запись `bph-linked-events-yield — additive contract field only`) подтверждает: фича — только аддитивное поле контракта, без изменения модели данных и без пересчёта значения.

## Затронутые области

| Область | Что затрагивается | Документы / код |
|---|---|---|
| BPH incoming-gateway (внешний контракт) | Новое поле в ответе `GET_LINKED_EVENTS` (схема `OperationData` / `details[]`) | `repositories/ИО/history-ops/sowa/sigma_alpha/to_bph_rq_http/history_get_linked_events/schemes/json/POST_api_v1_incoming-gateway_operations_linked-events_response_200.json`; `analytics/02-Modules/MOD-001-history-ops/integrations/bph.md` |
| history-ops — адаптер BPH | Чтение нового поля из ответа BPH и перенос в модель операции (gateway → raw converter → converters → wrappers → creator) | `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/adapter/bph/linked_events/**` |
| history-ops — исходящие контракты | Новое поле в REST `history.yml` и gRPC `historyOperationDetails.proto` (общие для OG- и BPH-фич) | `history-ops/src/main/swagger/history/history.yml`; `history-ops-grpc-client/history-ops-grpc-client-api/src/main/proto/historyOperationDetails.proto` |
| history-ops — маппинг модели | Чтение нового поля в `DetailsResponseMapper` и прокидка в `GetDetailsResponse` | `history-ops/src/main/java/com/sberbank/si20/history/ops/model/DetailsResponseMapper.java` |
| history-ops-screen-api (композит BDUI) | Отображение доходности на экране (кастомайзеры feed / деталки) | `history-ops-screen-api/src/main/java/com/sberbank/si20/history/ops/composite/screen/.../customizers/*` |
| Данные (БД) | **Не затрагивается** — доходность транзитна (аналог OG-фичи: поле не сохраняется) | `db-export/БД ИО.md` (таблицы `bph`, `operation`, `cancellation_bph` — справочники маппинга, колонки доходности нет) |

## Релевантная аналитика и спеки

| Документ | Что описывает | Почему релевантно задаче |
|---|---|---|
| `analytics/02-Modules/MOD-001-history-ops/integrations/bph.md` | Полный контракт `GET_LINKED_EVENTS` (request/response), приоритет слияния OG → GET_LINKED_EVENTS → GET_OPERATION_WITH_DETAILS, таблица маппинга полей BPH → HO | Источник AS IS контракта BPH, где появится новое поле |
| `analytics/02-Modules/MOD-001-history-ops/behavior/bph-response-processing.md` | Обработка ответов BPH, маппинг lead → МП, `details[]` key/value как расширенные поля | Показывает, где в BPH-ответе могут лежать «новые» поля (lead vs details) |
| `analytics/02-Modules/MOD-001-history-ops/api/grpc-to-screen-api.md` | gRPC-контракт HO ↔ screen-api (`GET_OPERATIONS_FEED` / `SEND_OPERATIONS_FEED`), маппинг полей | Показывает, как поле доходит до композита |
| `analytics/02-Modules/MOD-002-history-ops-screen-api/behavior/composite-feed-backend.md` | Сборка ленты композита, section types, кастомайзеры | Где доходность учитывается на экране |
| `analytics/02-Modules/MOD-002-history-ops-screen-api/api/get-operations-feed.md` | REST-фасад `/history/api/public/v1/screens/feed` | Входная точка композита |
| `Feature-writing/og-trading-order-yield/og-trading-order-yield.md` (+ `-decisions.md`, `-code-alignment.md`) | Симметричная OG-фича «доходность»: имя `yield`, формат `PriceData {value, currency}`, proto-поле 99, уровень lead | **Главный reference** по имени/формату/нумерации исходящего контракта |
| `Feature-writing/composite-active-order-commission/composite-active-order-commission.md` | Аналог паттерна «добавить параметр в BPH linked events» (`precalc_commission`) и пробросить до композита | Показывает сквозной путь нового BPH-параметра (BR-05, CN-02) |
| `Feature-writing/bph-coupons-dividends-monthly-summary/bph-coupons-dividends-monthly-summary.md` | Диаграмма цепочки клиент → композит → history-ops → источники | Описывает общий поток ленты истории операций |

## Релевантный код

| Файл | Компонент (класс / метод / endpoint / proto) | Текущее поведение | Почему важно для фичи |
|---|---|---|---|
| `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/adapter/bph/linked_events/BphLinkedOperationsGateway.java` | `BphLinkedOperationsGateway`; `getOperationsInternal()` → `bphClient.getLinkedEvents()`; `eventType()="GET_LINKED_EVENTS"`, `exSystem()="BPH"` | Точка входа в BPH `GET_LINKED_EVENTS`; `SUPPORTED_OPERATION_TYPES = {TRANSACTION_BUY, TRANSACTION_SELL, COMISSION}`; признак включения `isBphLinkedCommissionsEnabled() / isBphLinkedTradingOpsEnabled()` | Первый хоп цепочки: здесь ответ BPH с новым полем попадает в HO |
| `repositories/ИО/history-ops/.../adapter/bph/linked_events/converter/BphLinkedEventsRawConverter.java` | `BphLinkedEventsRawConverter` → `BphRawLinkedEventsWrapper` | Обёртка сырого ответа (`condTradeOrder`, `tradeOrder`, `dealsWithCommissions`) | Новое поле заявки доступно отсюда |
| `repositories/ИО/history-ops/.../adapter/bph/linked_events/converter/BphLinkedEventsConverterForTrades.java` | `BphLinkedEventsConverterForTrades` → `BphLinkedOperationsWrapperForTrades` | Сборка main/parent order + deals + commissions; drop-правила | Ветка заявок (trades) — целевая для доходности |
| `repositories/ИО/history-ops/.../adapter/bph/linked_events/converter/BphLinkedTradeOrderBaseConverterForTrades.java` | `BphLinkedTradeOrderBaseConverterForTrades.convert()` | Читает `OperationData lead` (subtype, additionalType, price, totalPrice, quantity, status, instrument, agreement, parentIds) + `details[]` map (exchange, valueIssued, rejectReason, accruedInterest, conditionPrice, marketStopLimit, marketTakeProfit) → `BphLinkedMainTradeOrderWrapperForTrades` | Здесь читается новое поле `yield` из `lead` или `details[]` и кладётся в wrapper |
| `repositories/ИО/history-ops/.../adapter/bph/linked_events/wrapper/BphLinkedMainTradeOrderWrapperForTrades.java` | `BphLinkedMainTradeOrderWrapperForTrades` | Поля заявки (type, additionalType, price, totalPriceCurrency, quantity, status, valueIssued, accruedInterest, conditionPrice, …). Поля `yield` **нет** | Сюда добавляется новое поле wrapper'а |
| `repositories/ИО/history-ops/.../service/conversion/operation/creator/BphLinkedTradeOperationCreator.java` | `BphLinkedTradeOperationCreator.createOperation()` → `HistoryOperationBase` | Собирает `HistoryOperationLead` + `ReportOrderOperationDetails` из wrapper'а; `HistoryOperationLead.builder()` без доходности | Здесь доходность переносится в модель HO (lead или details) |
| `repositories/ИО/history-ops/src/main/swagger/history/history.yml` | Схемы `HistoryOperationLead` (18 полей, до `channel`), `ReportOrderOperationDetails` (до `auto_follow`), `HistoryOperationBase` | REST-контракт HO; `PriceData` **не определён**, поля `yield` **нет** | Сюда добавляется новое поле и (вероятно) схема `PriceData` |
| `repositories/ИО/history-ops-grpc-client/history-ops-grpc-client-api/src/main/proto/historyOperationDetails.proto` | `message GetDetailsResponse`; `service HistoryOperationDetailsService.getOperationsFeed`; последнее поле `auto_follow = 98` | gRPC-контракт HO → screen-api; поля `yield`/`PriceData` **нет**; свободный номер 99 | Сюда добавляется `optional PriceData yield = 99` (общий с OG-фичей) |
| `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/model/DetailsResponseMapper.java` | `DetailsResponseMapper.convert(JsonNode source)` | Читает snake_case JSON модели HO → `GetDetailsResponse` через `convertDouble/convertString/...` и `setCommissionValue(...)` и т.п. | Здесь добавляется чтение `yield` и `setYield(...)` |
| `repositories/ИО/history-ops-screen-api/src/main/java/com/sberbank/si20/history/ops/composite/screen/details/operation/sections/customizers/CommissionCustomizer.java` | `CommissionCustomizer` (`operation.hasCommissionValue()` / `getCommissionValue()`) | Пример кастомайзера, читающего поле из proto `GetDetailsResponse` и формирующего `ContentParameter` | Образец, как композит отобразит новое поле (потребуется свой кастомайзер) |

### Цепочка проброса (AS IS)

```
BPH GET_LINKED_EVENTS (REST JSON)
  → BphLinkedOperationsGateway (bphClient.getLinkedEvents)
  → BphLinkedEventsRawConverter → BphRawLinkedEventsWrapper
  → BphLinkedEventsConverterForTrades → BphLinkedOperationsWrapperForTrades
  → BphLinkedTradeOrderBaseConverterForTrades(+Unconditional/Conditional) → BphLinkedMainTradeOrderWrapperForTrades
  → BphLinkedTradeOperationCreator → HistoryOperationBase (HistoryOperationLead + ReportOrderOperationDetails)
  → [сериализация в REST history.yml]
  → DetailsResponseMapper.convert(JsonNode) → GetDetailsResponse (gRPC historyOperationDetails.proto)
  → history-ops-screen-api (композит) → фронт
```

## Данные (БД, выгрузки)

| Таблица / поле | Где найдено | Текущее устройство | На что влияет фича |
|---|---|---|---|
| `bph` (id, subtype, type_id, is_active) | `db-export/БД ИО.md` (строка 19, 81–86) | Справочник маппинга BPH subtype → HO operation type | Не меняется; доходность не сохраняется |
| `operation` (id, operation_type_id, bc_id, bph_id, name) | `db-export/БД ИО.md` (строка 21, 99–106) | Справочник типов операций | Не меняется |
| `cancellation_bph` (id, info_id, status_id, available_cancellation, cancellation_comment) | `db-export/БД ИО.md` (строка 25, 131) | Правила отмены выводов | Не меняется |

**Вывод:** в схеме `history-ops` нет хранилища для деталей заявки и нет колонки «доходность». По аналогу OG-фичи (`og-trading-order-yield-code-alignment.md`, finding D-01/AC-15: «схема БД history-ops не меняется; доходность — транзитное поле») доходность на пути BPH также ожидается транзитной — переносится из ответа BPH в исходящие контракты без сохранения в БД.

## Интеграции и контракты, которые нужно учесть

### 1. Входящий контракт BPH `GET_LINKED_EVENTS` (REST JSON, OpenAPI-схема)

- Endpoint: `POST /api/v1/incoming-gateway/operations/linked-events` (`analytics/02-Modules/MOD-001-history-ops/integrations/bph.md`).
- Запрос — `RequestLinkedData`: `agreements` (обяз.), `startSearchDate`, `endSearchDate`, `dateForFilter` (`EVENT_DATE`/`FORMATION_DATE`/`ADDITIONAL_DATE`), `page`, `pageSize`. Якорь: `.../history_get_linked_events/schemes/json/POST_api_v1_incoming-gateway_operations_linked-events_request.json`.
- Ответ — `data[].linkedEvents[].tradeOrder|condTradeOrder` (объект заявки с `lead` = `OperationData` + `details[]`), `dealsWithCommissions[]`. Якорь: `.../history_get_linked_events/schemes/json/POST_api_v1_incoming-gateway_operations_linked-events_response_200.json`.
- `OperationData` (lead) содержит: `type`, `subType`, `subtype`, `additionalType`, `externalSystemVersion`, `formationDate`, `eventDate`, `additionalDate`, `externalSystemId`, `price`, `totalPrice` (тип `PriceData {value: string, currency: string}`), `quantity`, `quantityFact`, `tradingSection`, `account`, `status`, `instrument`, `ucpId`, `agreement`, `parent`, `parentIds`, `batchId`, `isFact`. **Поля `yield` нет** — новое поле добавляется сюда (или в `details[]` как key/value).
- `details[]` — массив `DetailData {key, value}` (расширенные поля; в коде читаются через `bphConverter.deserializeDetails(...)`).

### 2. Исходящий контракт HO → screen-api (gRPC, общий с OG-фичей)

- `historyOperationDetails.proto`, `message GetDetailsResponse`: последнее занятое поле `auto_follow = 98`; `commission_value = 65` (прецедент «новый параметр из источника → поле proto»). Свободный номер **99** подтверждён в `og-trading-order-yield-code-alignment.md` (finding C-04).
- OG-фича уже зафиксировала: `optional PriceData yield = 99;` (решение D-01/D-11). Тип `PriceData` в proto **отсутствует** и должен быть добавлен (новый message или импорт; в OG-спеке форма «инлайн vs разделяемое с BPH» не зафиксирована — см. CH-10).

### 3. Исходящий контракт HO (REST `history.yml`, общий с OG-фичей)

- `HistoryOperationLead` — 18 полей (`id`…`channel`); `ReportOrderOperationDetails` — 32 поля (до `auto_follow`). Поля `yield` нет; схемы `PriceData` в `components.schemas` **нет** (проверено grep по `PriceData|yield` — совпадений нет).
- OG-фича зафиксировала размещение `yield` на уровне **lead** (`HistoryOperationLead`), а не в `ReportOrderOperationDetails` (finding C-07/C-08).

### 4. Приоритет слияния заявок

- OG (`GetTradeOrders`) → BPH `GET_LINKED_EVENTS` → BPH `GET_OPERATION_WITH_DETAILS` (`analytics/.../integrations/bph.md`, «Приоритет слияния торговых заявок»).
- Для заявки, присутствующей и в OG, и в BPH, приоритетна OG-заявка; сделки/комиссии — из того же источника (`og-trading-order-yield.md`, BR-05: «доходность для OG-заявки берётся из ОГ; если нет — дозаполняется из BPH»).

## Ограничения и риски текущего состояния

1. **Внешний контракт BPH** — OpenAPI JSON-схема `GET_LINKED_EVENTS` принадлежит команде BPH (`bph-incoming-gateway`). Правку поля (имя + тип + уровень) выполняет BPH; `history-ops` пересобирает DTO/стабы из схемы (аналог OG-фичи: proto ОГ правят владельцы `trade-operations-commons`, HO лишь пересобирает стабы — CN-02).
2. **Расхождение формата `yield` OG vs BPH** — зафиксировано в `og-trading-order-yield-code-alignment.md` (D-26): OG-спека = `PriceData {value, currency}` optional на уровне lead; на момент подготовки OG-спеки BPH-спека описывалась как `number`, обязательное (GAP-INT-07). Синхронизация BPH-спеки **не выполнялась** — принятый риск; при подключении обоих путей формат/обязательность должны быть приведены к единому.
3. **Нет `PriceData` в исходящих контрактах** — ни в `history.yml`, ни в `historyOperationDetails.proto` типа `PriceData` нет; его нужно ввести (форма «инлайн vs разделяемый между OG/BPH» не зафиксирована).
4. **Доходность — транзитное поле** — не сохраняется в БД HO (подтверждено отсутствием колонки/чанджесета и аналогом OG-фичи).
5. **Не описано в analytics** — термин «доходность»/`yield` в `analytics/` отсутствует (подтверждено в `og-trading-order-yield-gaps-resolved.md`: `grep -i 'доходност|yield|profitab' analytics/` — совпадений нет). Источник и семантика значения (готовое от BPH vs вычисляемое в HO) в текущей аналитике не зафиксированы.
6. **Композит читает proto напрямую** — screen-api потребляет `GetDetailsResponse` из `history-ops-grpc-client`; для отображения доходности потребуется отдельный кастомайзер (по образцу `CommissionCustomizer`).

## Что учесть при написании фичи

1. **Полный путь из 4 хопов** обязателен: BPH-ответ → HO-модель → исходящие контракты (REST `history.yml` + gRPC `historyOperationDetails.proto`) → композит. Пропуск любого слоя = поле не дойдёт до фронта (аналог BR-04 OG-фичи).
2. **Согласовать имя и формат `yield` единообразно с OG-фичей** (`PriceData {value, currency}`, имя `yield`) — исходящие контракты (`history.yml`, `historyOperationDetails.proto`) общие для обоих путей; OG уже зарезервировал proto-поле 99.
3. **Уровень размещения**: в OG-фиче доходность на уровне `HistoryOperationLead` (lead), не в `ReportOrderOperationDetails`. Для BPH — то же место (единая семантика).
4. **Источник значения в BPH-ответе**: определить, придёт ли `yield` как новое поле `OperationData` (lead) или как запись `details[] {key, value}`. От этого зависит точка чтения в `BphLinkedTradeOrderBaseConverterForTrades`.
5. **Какая сущность несёт доходность**: `tradeOrder` (безусловная заявка), `condTradeOrder` (условная), обе — или также комиссии. В OG-фиче доходность — по всей заявке целиком (готовое значение).
6. **Опциональность/presence**: поле опциональное; отсутствие ≠ нулевое значение; `0` и отрицательные значения — допустимы (аналог OG BR-05/BR-06). Учесть «значение есть» vs «пустой value».
7. **Приоритет слияния**: OG-заявка приоритетна; доходность OG-заявки берётся из ОГ, при отсутствии — дозаполняется из BPH. Для BPH-only заявки доходность — только из BPH.
8. **Фича-тогл**: в OG-фиче отдельного тогла под `yield` нет (T-05). Для BPH — проверить, нужен ли тогл, либо возврат безусловный (аналог BPH-параметра `precalc_commission` в `composite-active-order-commission` шёл с тоглом OFF до готовности BPH).
9. **Данные**: БД HO не меняется (транзитное поле), чанджесет не нужен.
10. **Синхронизация релизов**: релиз привязывается к симметричной OG-фиче (D-06 OG-фичи); при параллельной разработке держать формат единым.

### Актуализация после resolve (2026-09-20)

Решения из resolve, которые писатель и ревьюер должны считать актуальнее исходного current-state:

- GAP-UCAS-01: Таймаут/retry вызова BPH `GET_LINKED_EVENTS` задаётся runtime-конфигом HO (`WebClientBphConfiguration`), в analytics не описан; фича новых значений timeout/retry/fallback не вводит. Источник: `analytics/02-Modules/MOD-001-history-ops/integrations/bph.md` § «Таймауты, retry и fallback»
- GAP-UCTB-01, GAP-CONS-01, GAP-INT-01, GAP-ALG-01, GAP-MAP-01: Входящий контракт BPH: поле `yield` — объект `PriceData {value, currency}`
- GAP-UCTB-02, GAP-CONS-02, GAP-INT-02, GAP-ALG-02, GAP-MAP-02: REST `history.yml` `HistoryOperationLead`: `yield` = `PriceData {value, currency}`; схема `PriceData` вводится в `components.schemas`
- GAP-UCTB-03, GAP-CONS-03, GAP-INT-03, GAP-ALG-03, GAP-MAP-03: gRPC `historyOperationDetails.proto` `GetDetailsResponse`: `optional PriceData yield = 99`; тип `PriceData` — инлайн `message`
- GAP-UCTB-04, GAP-CONS-04, GAP-INT-04, GAP-ALG-04, GAP-MAP-04: Композит BDUI: «Доходность» (формат `{value} {currency}`), только в деталке
- GAP-UCTB-05, GAP-CONS-05, GAP-INT-05, GAP-ALG-05, GAP-MAP-05: В BPH-ответе поле приходит в `OperationData` (lead), читается напрямую
- GAP-UCTB-06, GAP-CONS-06, GAP-INT-06, GAP-ALG-06, GAP-MAP-06: Доходность несёт только `tradeOrder` (безусловная заявка)
- GAP-UCTB-07, GAP-INT-09, GAP-ALG-07, GAP-MAP-07: Уровень размещения в HO — `HistoryOperationLead` (lead)
- GAP-UCTB-08, GAP-INT-10, GAP-ALG-08, GAP-MAP-08: Пустой `value` = «нет значения» (поле не заполняется/не отображается); `0` и отрицательные допустимы и отображаются «как есть»
- GAP-UCTB-09, GAP-CONS-07, GAP-INT-07, GAP-ALG-09, GAP-MAP-09: Поле приходит безусловно; новый параметр запроса не нужен
- GAP-UCTB-10, GAP-CONS-08, GAP-INT-08, GAP-ALG-10, GAP-MAP-10: Фича-тогл для BPH-ветки доходности (OFF до готовности BPH, kill-switch); при OFF поле `yield` не читается и не пробрасывается
- GAP-UCTB-11, GAP-CONS-09, GAP-INT-11, GAP-ALG-11, GAP-MAP-11: Готовое значение от BPH (passthrough, без пересчёта); нечитаемый формат → `null`, поток не прерывается
- GAP-UCTB-12, GAP-CONS-10, GAP-INT-12, GAP-ALG-12, GAP-MAP-12: Привести BPH к единому `PriceData {value, currency}` optional (выравнивание с OG)
- CH-02: —
- CH-07: —
- CH-09: —
- CH-10: —
- CH-01: a
- CH-03: b
- CH-04: a
- CH-05: b
- CH-06: a
- CH-08: a
- CH-11: a
- CH-12: b
- CH-13: a
- CH-14: a

**Якоря полей из актуальной SPEC:**

`transaction_buy`, `transaction_sell`, `GET_LINKED_EVENTS`, `yield`, `failOperationTypes`, `GetTradeOrders`, `GET_OPERATION_WITH_DETAILS`, `BPH`, `activate`, `deactivate`, `actor`, `participant`

См. также § «Закрытые вопросы» ниже — не переспрашивать закрытые Q.
## Открытые вопросы / что проверить

| ID | Вопрос | Где искать ответ |
|---|---|---|
| Q-01 | Финальное имя поля «доходность» во **входящем контракте BPH** (`GET_LINKED_EVENTS`, OpenAPI JSON): `yield`, `profitability`, `yieldData` или иное? | Команда BPH (владелец `bph-incoming-gateway`); схема `.../history_get_linked_events/schemes/json/*_response_200.json` |
| Q-02 | Финальное имя и формат поля в **REST `history.yml`** (`HistoryOperationLead`): `yield` как `PriceData {value, currency}`? (схемы `PriceData` в `history.yml` нет) | `history-ops/src/main/swagger/history/history.yml`; решение D-01 OG-фичи (уже `yield` = `PriceData`) |
| Q-03 | Финальное имя и формат поля в **gRPC `historyOperationDetails.proto`** (`GetDetailsResponse`): `optional PriceData yield = 99`? Откуда берётся тип `PriceData` (инлайн message vs импорт)? | `history-ops-grpc-client/.../proto/historyOperationDetails.proto`; решение D-11 OG-фичи (поле 99 свободно) |
| Q-04 | Финальное имя поля в **композите BDUI** (screen-api → фронт) и где отображается (feed-карточка, деталка, оба)? | `history-ops-screen-api/.../composite/screen/.../customizers/*`; команда screen-api |
| Q-05 | Где в BPH-ответе придёт `yield`: новое поле `OperationData` (lead) или запись `details[] {key, value}`? | Команда BPH; схема `..._response_200.json` (definitions `OperationData` / `DetailData`) |
| Q-06 | Какая сущность несёт доходность: `tradeOrder`, `condTradeOrder`, обе, или также комиссии (`dealsWithCommissions[].commissions`)? | Команда BPH; `analytics/.../integrations/bph.md` (структура `linkedEvents`) |
| Q-07 | Уровень размещения в модели HO: `HistoryOperationLead` (lead) или `ReportOrderOperationDetails` (details)? OG-фича зафиксировала lead | `history.yml` (`HistoryOperationLead` / `ReportOrderOperationDetails`); OG-фича (BR-04, C-07/C-08) |
| Q-08 | Семантика пустого/неполного значения: `yield = {value: "", currency: "RUB"}` — «значения нет» или «пустое поле»? `0` и отрицательные значения? | Команда BPH + PO; OG-фича (CH-01, CH-11, BR-05/BR-06) |
| Q-09 | Требуется ли новый **параметр запроса** `RequestLinkedData` (чтобы BPH начал возвращать `yield`), или поле приходит в ответе безусловно? | Команда BPH; `.../history_get_linked_events/schemes/json/POST_api_v1_incoming-gateway_operations_linked-events_request.json` |
| Q-10 | Нужен ли **фича-тогл** для ветки BPH (по образцу `precalc_commission` с тоглом OFF до готовности BPH)? | `history-ops` (константы тоглов, `ExecutionProcess`); `composite-active-order-commission.md` (CN-02) |
| Q-11 | Источник и семантика значения `yield`: готовое значение от BPH (по всей заявке, комиссии учтены) или HO что-то пересчитывает? | PO + команда BPH; OG-фича (BR-06: ОГ отдаёт готовое, HO не пересчитывает) |
| Q-12 | Привести ли расхождение формата OG/BPH `yield` к единому (`PriceData`), или BPH-спека остаётся `number`? (зафиксированный риск D-26 OG-фичи) | PO / владельцы контрактов; `og-trading-order-yield-code-alignment.md` (D-26, CN-15) |

## Закрытые вопросы

| ID | Дата | Решение | Где в spec | Источник |
|----|------|---------|------------|----------|
| Q-01 | 2026-09-20 | Входящий контракт BPH: поле `yield` — объект `PriceData {value, currency}` | §1.3, §2 CN-01, §4.1.1.1, §4.2.3-mapping | /resolve-gaps D-01 |
| Q-02 | 2026-09-20 | REST `history.yml` `HistoryOperationLead`: `yield` = `PriceData {value, currency}`; схема `PriceData` вводится в `components.schemas` | §2 CN-02/CN-06, §4.1.1.3, §4.2.3-mapping | /resolve-gaps D-02 |
| Q-03 | 2026-09-20 | gRPC `historyOperationDetails.proto` `GetDetailsResponse`: `optional PriceData yield = 99`; тип `PriceData` — инлайн `message` | §2 CN-02/CN-06, §4.1.1.2, §4.2.3-mapping | /resolve-gaps D-03 |
| Q-04 | 2026-09-20 | Композит BDUI: «Доходность» (формат `{value} {currency}`), только в деталке | §2 CN-11, §4.1.1.4, §4.2.3-mapping | /resolve-gaps D-04 |
| Q-05 | 2026-09-20 | В BPH-ответе поле приходит в `OperationData` (lead), читается напрямую | §1.3, §2 CN-01, §4.1.1.1, §4.2.2 | /resolve-gaps D-05 |
| Q-06 | 2026-09-20 | Доходность несёт только `tradeOrder` (безусловная заявка) | §2 CN-01, §4.1.1.1, §4.2.3-mapping | /resolve-gaps D-06 |
| Q-07 | 2026-09-20 | Уровень размещения в HO — `HistoryOperationLead` (lead) | §2 CN-07, §4.1.1.2, §4.2.3-mapping | /resolve-gaps D-07 |
| Q-08 | 2026-09-20 | Пустой `value` = «нет значения» (поле не заполняется/не отображается); `0` и отрицательные допустимы и отображаются «как есть» | §2 CN-08, §4.1.1.1, §4.2.3-mapping | /resolve-gaps D-08 |
| Q-09 | 2026-09-20 | Поле приходит безусловно; новый параметр запроса не нужен | §2 CN-01, §4.1.1.1, §4.2.3-mapping | /resolve-gaps D-09 |
| Q-10 | 2026-09-20 | Без фича-тогла: поле пробрасывается безусловно | §4.1.1.1, §4.2.3-mapping | /resolve-gaps D-10 |
| Q-11 | 2026-09-20 | Готовое значение от BPH (passthrough, без пересчёта); нечитаемый формат → `null`, поток не прерывается | §2 CN-10, §4.1.1, §4.2.3-mapping | /resolve-gaps D-11 |
| Q-12 | 2026-09-20 | Привести BPH к единому `PriceData {value, currency}` optional (выравнивание с OG) | §2 CN-03, §4.1.1.1, §4.2.3-mapping | /resolve-gaps D-12 |

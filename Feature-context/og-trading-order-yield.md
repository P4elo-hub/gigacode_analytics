# Контекст для фичи: доходность торговой заявки в интеграции Order Gateway (ОГ)

## Задача (бриф)

> Доработать интеграцию `history-ops` ↔ **Order Gateway (ОГ)** так, чтобы в ответе
> `GetTradeOrders` для **торговой заявки** приходило значение **доходности**.
> Имя поля в контрактах команда выбирает сама (рабочее имя — `yield`).

> «Так же» в брифе означает симметрию с параллельной доработкой по BPH
> (`GetLinkedEvents`, см. `Feature-writing/bph-linked-events-yield/bph-linked-events-yield.md`): доходность
> должна появиться и на пути заявок из ОГ, а не только из BPH linked events.

## Затронутые области

| Область | Что затрагивается | Документы / код |
|---|---|---|
| Контракт ОГ (gRPC) | Новое поле в `TradeOrder` ответа `GetTradeOrders` | `history-ops/src/main/proto/order-gateway.proto` (копия из `trade-operations-commons`) |
| Gateway интеграции | Вызов `getTradeOrders`, логирование `exSystem=OG` | `OrderGrpcGateway.java` |
| Маппинг ответа ОГ | Чтение нового поля из `TradeOrder` → внутренняя модель | `OrderGrpcConverter.java`, `OrderGatewayOrderWrapper.java` |
| Сборка операции | Перенос доходности в итоговую торговую операцию | `OgTradeOperationCreator.java`, `OrderMerger.java` |
| Исходящий контракт history-ops | Проброс поля наружу (на фронт / screen-api) | `history-ops/src/main/swagger/history/history.yml` |
| Композит BDUI | Учёт поля на экране истории | `history-ops-screen-api/.../composite` |
| Конфигурация запроса | Включение запроса заявок из ОГ | `RpcNamesForRequestCondition.OG_GET_TRADE_ORDERS`, `app-config-dynamic...ogGetTradeOrders` |

## Релевантная аналитика и спеки

| Документ (analytics/, Feature-writing/) | Что описывает | Почему релевантно задаче |
|---|---|---|
| `analytics/.../[SIHIST-1232]_gRPC_апi_order-gateway_для_заявок.md` | gRPC-интеграция `history-ops` ↔ order-gateway, метод `GetTradeOrders`, таблица полей `TradeOrder` | Базовый контракт ОГ для торговых заявок; поля `bond_denomination`, `value_per_instrument_item_pcnt` и др. уже описаны — **доходности нет** |
| `analytics/.../[SIHIST-3502]_...GET_LINKED_EVENTS_(ВЕ).md` | Получение торговых операций из BPH; приоритет источников; насыщение заявок сделками и комиссиями | ОГ (`GetTradeOrders`) — **приоритетный источник** заявок; BPH linked events — дополнительный; правила слияния в `OrderMerger` |
| `analytics/.../[SIHIST-3503]_...GET_OPERATION_WITH_DETAILS_(ВЕ).md` | Легаси-заявки BPH; тот же приоритет ОГ | Контекст мульти-источниковой обработки торговых заявок |
| `analytics/.../[SIHIST-3373]_Композит_-_Деталка_(BE).md` | Маппинг полей торговой заявки на экран деталки BDUI (`value_by_instrument_item`, `bond_denomination`, `value_per_instrument_item_pcnt` и др.) | Куда может лечь доходность на UI; сейчас доходность не описана |
| `analytics/.../[SIHIST-3662]_Расширение_атрибутного_состава_для_торговых_операций.md` | Атрибуты торговых операций в ответе НО, в т.ч. `value_by_instrument_item_prct` для облигаций | Образец добавления облигационных полей по пути OG → ответ НО |
| `Feature-writing/bph-linked-events-yield/bph-linked-events-yield.md` | Доходность в интеграции BPH `GetLinkedEvents` (рабочее имя `yield`) | Сibling-фича; общий исходящий контракт `history.yml` и BDUI; согласование имени/типа поля |

## Релевантный код

| Файл | Компонент (класс / метод / контракт) | Текущее поведение | Почему важно для фичи |
|---|---|---|---|
| `history-ops/src/main/proto/order-gateway.proto` | `TradeOrder` (стр. 71–120), `GetTradeOrdersRequest/Response`, `OrdersService.GetTradeOrders` | Proto-контракт ОГ; поля заявки (`value_per_instrument_item`, `bond_denomination`, `value_per_instrument_item_pcnt` и др.); **поля доходности нет** | **Точка добавления** нового поля в ответе ОГ; proto синхронизируется с `trade-operations-commons` |
| `.../adapter/order_gateway/OrderGrpcGateway.java` | `OrderGrpcGateway`, `exSystem()="OG"`, `eventType()="GET_TRADE_ORDERS"`, `responseSupplier()→getTradeOrders` | Запрашивает заявки через gRPC, конвертирует `TradeOrder` → `OrderGatewayOrderWrapper` | Точка входа интеграции; изменение proto потребует регенерации gRPC-классов |
| `.../adapter/order_gateway/converter/OrderGatewayOrderConverter.java` | `toOrdersRequest()` | Формирует `GetTradeOrdersRequest` (agreements, instrument_filter, order_filter, order_by, период при `isOgDatesEnabled()`) | Запрос сейчас не содержит параметров доходности; уточнить, нужен ли параметр запроса или поле приходит безусловно |
| `.../adapter/order_gateway/converter/OrderGrpcConverter.java` | `convert(TradeOrder, ExecutionProcess)` | Маппит все поля `TradeOrder` в `OrderGatewayOrderWrapper` (цена, номинал, НКД, проценты и т.д.) | **Точка чтения** нового поля доходности из ответа ОГ |
| `.../adapter/order_gateway/OrderGatewayOrderWrapper.java` | immutable wrapper заявки ОГ | Хранит атрибуты заявки, включая `valuePerInstrumentItemPcnt`, `bondDenomination`; **доходности нет** | **Точка добавления** поля во внутреннюю модель |
| `.../service/conversion/operation/creator/OgTradeOperationCreator.java` | `createTradeOperationByOg()` | Собирает `HistoryOperationLead` + `ReportOrderOperationDetails` из `OrderGatewayOrderWrapper`; облигационные поля (`valuePerInstrumentItemPcnt`, `bondDenomination`, `accruedInterestByItem`) кладёт в **details** | **Точка маппинга** доходности в итоговую операцию; по аналогии с `valuePerInstrumentItemPcnt` логично класть в `ReportOrderOperationDetails`, а не в lead |
| `.../service/conversion/operation/merger/OrderMerger.java` | `merge(...)`, приоритет ОГ над BPH/BC | Сливает заявки из ОГ, BPH linked events и BC по `exchangeOrderId`; для совпадений приоритет у ОГ | Заявки из ОГ — основной путь; доходность должна попасть в операцию до отдачи наружу |
| `.../service/operation/SourceOperationService.java` | `SourceOperations.ogOrders`, вызов `orderGrpcGateway` | Параллельно запрашивает ОГ, BPH, BC и др.; `ogOrders` передаётся в merger | Контекст оркестрации источников |
| `history-ops/src/main/swagger/history/history.yml` | `ReportOrderOperationDetails` (376+), `HistoryOperationLead` (456+) | Исходящий контракт; `value_per_instrument_item_pcnt` в details; **поля доходности нет** | **Точка добавления** поля в исходящий ответ |
| `.../adapter/order_gateway/converter/ActiveOrderConverter.java` | `ActiveOrder` → `OrderGatewayOrderWrapper` | Отдельный путь для **активных заявок** (`GetActiveOrders`); полей доходности нет | Уточнить, нужна ли доходность и для активных заявок |
| `.../counter/adapter/GetTradeOrdersGateway.java`, `OgConverter.java` | Счётчик активных операций | Упрощённый маппинг `TradeOrder` → `ActiveOperationWrapper` (id, agreement, date, status) | Вероятно **не затрагивается** — счётчику доходность не нужна |
| `.../adapter/RpcNamesForRequestCondition.java` | `OG_GET_TRADE_ORDERS("ogGetTradeOrders")` | Ключ конфигурации запроса заявок ОГ | Управление включением запроса; учесть в тестах |

## Данные (БД, выгрузки)

| Таблица / поле / запрос | Где найдено | Текущее устройство | На что влияет фича |
|---|---|---|---|
| `history_ops.operation`, `status_to_operation`, `info` | `db-export/БД ИО.md` | Метаданные операций в БД НО | По аналогии с BPH-yield: доходность, вероятно, **транзитное поле ответа**, не колонка БД — требует подтверждения |
| Таблицы BPH (`bph`, `bph_bc`) | `db-export/БД ИО.md` | Связки семейства/подтипа BPH | Не затрагиваются напрямую; доходность приходит из ОГ, не из БД |

> В коде и контрактах **нет** существующего поля `yield`/«доходность» ни в proto ОГ, ни в
> `history.yml`, ни во wrapper-моделях (поиск по `repositories/`).

## Интеграции и контракты, которые нужно учесть

- **ОГ = Order Gateway**, не BPH incoming-gateway. В логах интеграции: `exSystem="OG"`, `eventType="GET_TRADE_ORDERS"` (`OrderGrpcGateway.java`).
- gRPC-сервис: `OrdersService.GetTradeOrders(GetTradeOrdersRequest) → GetTradeOrdersResponse` (`order-gateway.proto:13–14, 59–61`).
- Ответ: `GetTradeOrdersResponse.orders[]` типа `TradeOrder`; DTO генерируются из proto.
- Источник правды proto — репозиторий `trade-operations-commons` (ссылка в комментарии proto); локальная копия в `history-ops/src/main/proto/order-gateway.proto`.
- **Приоритет источников:** заявки из `GetTradeOrders` (ОГ) приоритетнее BPH `GET_LINKED_EVENTS` и BC (`SIHIST-3502`, раздел «Насыщение торговых заявок»); критерий дедупликации — `exchangeOrderId` (ОГ) vs `lead.parentIds.selfIdTs` (BPH).
- Сделки по заявке ОГ запрашиваются отдельно через `GetDeals` (`DealGrpcGateway`); комиссии могут обогащаться из BPH/BC (`OgTradeOperationCreator.toReportDeal()`).
- Исходящий контракт `history.yml` (пакет `api.ws`) — без нового поля доходность не дойдёт до `history-ops-screen-api`/фронта.
- Сibling-фича `bph-linked-events-yield` добавляет доходность в BPH `OperationData` и, вероятно, в тот же исходящий `history.yml` — **имя и уровень поля нужно согласовать**, чтобы оба источника писали в одно место.
- Запрос ОГ управляется конфигом `app-config-dynamic.instrument-filter-requests-dynamic.ogGetTradeOrders` (`OriginalInstrumentWithItsVersionsRequestsConfigMapTest.java`).

## Ограничения и риски текущего состояния

- Изменение `order-gateway.proto` затрагивает сгенерированные gRPC-классы — нужен ребилд и синхронизация с upstream `trade-operations-commons` (поле должно появиться сначала в ОГ).
- Поле должно быть **опциональным** (`optional` в proto), чтобы не сломать обратную совместимость с текущими ответами ОГ без доходности.
- Сквозной проброс: `TradeOrder` → `OrderGrpcConverter` → `OrderGatewayOrderWrapper` → `OgTradeOperationCreator` → `history.yml` → screen-api composite; пропуск слоя = поле не дойдёт до фронта.
- Для заявок ОГ облигационные атрибуты уже лежат в `ReportOrderOperationDetails` (`value_per_instrument_item_pcnt`, `bond_denomination`), а не в `HistoryOperationLead` — доходность, вероятно, должна следовать той же схеме.
- `OrderMerger` при совпадении `exchangeOrderId` отдаёт приоритет ОГ; если доходность есть только в BPH linked events, но заявка пришла из ОГ — поведение нужно явно определить (обогащение vs игнорирование).
- Тестовые фикстуры ОГ (`json/response/order_gateway/order_gateway_get_orders_grpc_response*.json`) и интеграционные логи (`txt/**/expected_integration_log*.txt`) нужно обновить под новое поле.
- Путь **активных заявок** (`GetActiveOrders` / `ActiveOrderConverter`) использует отдельное proto-сообщение `ActiveOrder` без полей облигационной доходности — scope фичи нужно уточнить.

## Что учесть при написании фичи

- ОГ в доменной терминологии SIHIST = **Order Gateway** (`GetTradeOrders`), не BPH incoming-gateway.
- Добавлять поле через контракты (`order-gateway.proto`, `history.yml`), не хардкодить; gRPC/OpenAPI DTO регенерируются.
- Сквозной проброс по пути ОГ: `TradeOrder.<yield>` → `OrderGatewayOrderWrapper` → `OgTradeOperationCreator` → `ReportOrderOperationDetails` / `HistoryOperationLead` → `history.yml` → BDUI.
- Согласовать имя поля с sibling-фичей `bph-linked-events-yield` для единого исходящего контракта.
- Уточнить уровень размещения: для OG-заявок облигационные поля исторически в `ReportOrderOperationDetails`; для BPH-yield в черновике spec рассматривается `HistoryOperationLead`.
- Обновить тестовые фикстуры ОГ и интеграционные тесты (`HistoryOpsFeedScreenTest`, `OrderMergerTest`, `BphTradesIntegrationTest`).
- Проверить опциональность и поведение при отсутствии поля в ответе ОГ (заявка формируется как сейчас).

## Открытые вопросы / что проверить

| ID | Вопрос | Где искать ответ |
|---|---|---|
| Q-01 | Финальное имя поля «доходность» в proto ОГ, `history.yml` и BDUI — `yield`, `profitability` или иное? | Согласовать с владельцами контрактов ОГ и screen-api; см. также Q-01 в `bph-linked-events-yield` |
| Q-02 | Добавляет ли команда Order Gateway поле в upstream proto самостоятельно, или изменение координируется из НО? | Команда Order Gateway; `trade-operations-commons/.../order-gateway.proto` |
| Q-03 | Нужен ли параметр запроса `GetTradeOrdersRequest` для включения возврата доходности, или поле приходит безусловно? | Команда ОГ; `GetTradeOrdersRequest` в proto |
| Q-04 | На каком уровне исходящего контракта размещать доходность для OG-заявок: `ReportOrderOperationDetails` (как `value_per_instrument_item_pcnt`) или `HistoryOperationLead`? | `history.yml`; `OgTradeOperationCreator.java`; согласование с BPH-yield spec |
| Q-05 | Тип и формат: `google.type.Decimal`, процент (`number`), или структура с валютой (как `PriceData` в BPH-yield)? | Proto ОГ; команда ОГ |
| Q-06 | Для каких инструментов заполняется доходность (только облигации / `type_name == bond*`, или шире)? | Команда ОГ; аналитика композита `SIHIST-3373` |
| Q-07 | Нужна ли доходность на пути **активных заявок** (`GetActiveOrders`, `ActiveOrderConverter`)? | `ActiveOrder` в proto; product owner |
| Q-08 | Если заявка из ОГ без доходности, но BPH linked events её содержит — обогащать или игнорировать? | `OrderMerger.java`; `SIHIST-3502` (приоритет ОГ) |
| Q-09 | Нужно ли сохранять доходность в БД `history-ops` или это транзитное поле ответа? | `db-export/БД ИО.md`; модель `Operation` |
| Q-10 | Какой композит/секция BDUI отображает доходность и в каком формате? | `history-ops-screen-api/.../composite`; `SIHIST-3373` |

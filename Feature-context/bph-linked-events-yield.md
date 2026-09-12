# Контекст для фичи: новый параметр «доходность» в интеграции BPH GetLinkedEvents

## Задача (бриф)

> В интеграции `history-ops` ↔ BPH по `GetLinkedEvents` нужно: (1) добавить новый
> параметр в интеграцию, (2) читать из ответа BPH новый параметр «доходность»
> (рабочее имя поля — `yield`), (3) пробросить его на фронт и (4) учесть в
> композите BDUI (`history-ops-screen-api`).

> Имя `yield` выбрано как рабочее (бриф разрешает придумать имя). Финальное
> имя поля в каждом контракте нужно согласовать (см. «Открытые вопросы»).

## Затронутые области

| Область | Что затрагивается | Документы / код |
|---|---|---|
| Контракт BPH (вход/выход) | Новый параметр запроса + новое поле ответа | `history-ops/src/main/swagger/bph/bph.yml` |
| Gateway интеграции | Формирование запроса и вызов `getLinkedEvents` | `BphLinkedOperationsGateway.java` |
| Маппинг ответа BPH | Чтение нового поля и перенос в модель | `adapter/bph/linked_events/wrapper/*`, `.../converter/*` |
| Исходящий контракт history-ops | Проброс поля наружу (на фронт) | `history-ops/src/main/swagger/history/history.yml` |
| Композит BDUI | Учёт поля в экранном композите | `history-ops-screen-api/.../composite`, `.../services/screen/composite` |
| Конфигурация/фиче-флаг | Включение запроса linked events | `RpcNamesForRequestCondition.BPH_GET_LINKED_EVENTS`, `app-config-dynamic...bphGetLinkedEvents` |

## Релевантные документы базы знаний

| Документ (01–08) | Что описывает | Почему релевантно задаче |
|---|---|---|
| `06-UseCases/PROC-001-history-feed/04-source-requests.md` | Параметры запроса BPH (`agreements`, дата окончания, page size, date for filter) | Описывает текущий запрос, в который добавляется новый параметр |
| `06-UseCases/PROC-005-income-corporate-actions/02-response-mapping.md` | Маппинг ответа BPH/BC/DCA в операции | Образец того, как поле ответа превращается в операцию |
| `05-Data/entities/source-config.md`, `05-Data/db-model.md` | Связки BPH/BC, статусы, поля операции | Контекст модели операции, в которую ляжет новое поле |
| `05-Data/field-matrix/source-to-operation-fields.md` | Матрица «поле источника → поле операции» | Куда добавить строку для нового поля `yield` |
| `06-UseCases/PROC-002-operation-details/README.md` | Чтение сохранённого списка операций и детали | Где поле может отображаться на деталях |

## Релевантный код

| Файл | Компонент (класс / метод / контракт) | Текущее поведение | Почему важно для фичи |
|---|---|---|---|
| `history-ops/src/main/swagger/bph/bph.yml` | `paths./api/v1/incoming-gateway/operations/linked-events` (стр. 924); схемы `RequestLinkedData` (1053), `LinkedEventsData` (991), `OperationData` (1088) | OpenAPI-контракт BPH; из него генерируются DTO `RequestLinkedData`, `LinkedEventsDataLinkedEventsInner`, `OperationData` и др. | **Точка добавления**: новый параметр запроса в `RequestLinkedData` и новое поле ответа в `OperationData` |
| `.../adapter/bph/linked_events/BphLinkedOperationsGateway.java` | `BphLinkedOperationsGateway.createRequest()`, `getOperationsInternal()` | Строит `RequestLinkedData` (agreements, startSearchDate, endSearchDate, pageSize, dateForFilter) и вызывает `bphClient.getLinkedEvents(requestId, request)`; `exSystem="BPH"`, `eventType="GET_LINKED_EVENTS"` | Сюда добавляется установка нового параметра запроса |
| `.../adapter/bph/linked_events/wrapper/BphRawLinkedEventsWrapper.java` | `BphRawLinkedEventsWrapper.from(LinkedEventsDataLinkedEventsInner)` | Оборачивает `condTradeOrder`/`tradeOrder`/`dealsWithCommissions` из ответа | Если поле на уровне order/lead — пробрасывать через wrapper |
| `.../adapter/bph/linked_events/converter/BphLinkedEventsRawConverter.java` | `BphLinkedEventsRawConverter` (+ `GENERAL_STATUS_MAP`) | Первичная конвертация сырого ответа в wrapper | Точка чтения нового поля из `OperationData` |
| `.../adapter/bph/linked_events/converter/BphLinkedEventsConverterForTrades.java` (и `...ForCommissions`, leaf-конвертеры `BphLinkedConditional/Unconditional/Parent/Deal...`) | `convert(BphRawLinkedEventsWrapper, ExecutionProcess, ErrorCollector)` | Читают поля `OperationData` (`getStatus`, `getExternalSystemId`, price/quantity и т.д.) и строят внутренние wrapper-модели | **Точка маппинга** значения `yield` во внутреннюю модель операции |
| `.../service/conversion/operation/creator/BphLinkedTradeOperationCreator.java`, `.../merger/OperationMerger.java` | Создание/слияние операций | Сборка итоговой операции из связанных событий | Перенос `yield` в итоговую операцию |
| `history-ops/src/main/swagger/history/history.yml` | Исходящий контракт history-ops (пакет `api.ws`), схемы с `price`, `cancellation_price`, `total_deals_avg_price` | Контракт, который потребляет фронт/screen-api | **Точка добавления** поля `yield` в исходящий ответ |
| `history-ops-screen-api/.../composite`, `.../services/screen/composite`, `.../services/chevron/composite` | Сборка BDUI-композита | Формирует экран из данных history-ops | **Точка учёта** `yield` в композите BDUI |
| `.../OriginalInstrumentWithItsVersionsRequestsConfigMapTest.java` | конфиг `app-config-dynamic.instrument-filter-requests-dynamic.bphGetLinkedEvents.active` | Фиче-флаг активности запроса linked events | Управление включением запроса; учесть в тестах |

## Данные (БД, выгрузки)

| Таблица / поле / запрос | Где найдено | Текущее устройство | На что влияет фича |
|---|---|---|---|
| `history_ops.bph` (24), `bph_bc` (14) | `db-export/БД ИО.md` | Связки семейства/подтипа BPH | Само поле `yield` приходит из ответа BPH, не из БД; БД-маппинг определяет, какие операции участвуют |
| `history_ops.operation`, `status_to_operation`, `info` | `db-export/БД ИО.md` | Метаданные операций | Проверить, нужно ли БД-сопровождение для отображения `yield` (вероятно нет) |

> По текущим данным отдельной таблицы/колонки для «доходности» нет — это поле
> ответа внешней системы BPH, а не строка БД `history-ops` (требует подтверждения,
> см. «Открытые вопросы»).

## Интеграции и контракты, которые нужно учесть

- Эндпоинт BPH: `POST /api/v1/incoming-gateway/operations/linked-events` (bph.yml:924), вызов `bphClient.getLinkedEvents(...)`.
- Запрос `RequestLinkedData` (bph.yml:1053): `agreements` (required), `startSearchDate`, `endSearchDate`, `dateForFilter` (required), `page`, `pageSize` (required). Новый параметр добавляется сюда и заполняется в `createRequest()`.
- Ответ: `LinkedEventsData.linkedEvents[]` → `condTradeOrder` / `tradeOrder` / `dealsWithCommissions` → `lead`/`details` типа `OperationData` (bph.yml:1088). Поле `yield` логично добавить в `OperationData` (рядом с `price`, `totalPrice`, `quantity`).
- DTO BPH (`RequestLinkedData`, `OperationData`, `LinkedEventsDataLinkedEventsInner` и др.) генерируются из `bph.yml` — отдельных Java-классов в исходниках нет, правка идёт через контракт + ребилд.
- Исходящий контракт `history.yml` (пакет `api.ws`) — поле нужно добавить и здесь, иначе оно не дойдёт до screen-api/фронта.
- Композит BDUI собирается в `history-ops-screen-api` (`.../composite`) — там поле учитывается для экрана.

## Ограничения и риски текущего состояния

- Изменение контракта BPH (`bph.yml`) затрагивает генерируемые DTO — нужен ребилд; проверить, что новое поле `nullable`/опционально, чтобы не сломать обратную совместимость с текущими ответами BPH.
- Конвертеры устойчивы к ошибкам (`ErrorCollector`, `tryConvert`, дроп сущности при несоответствии статуса) — добавление поля не должно ломать существующую логику фильтрации (`EXECUTED`/`COMPLETED`).
- Поле проходит несколько слоёв: BPH `OperationData` → wrapper → leaf-конвертер → operation creator/merger → исходящий `history.yml` → screen-api composite. Пропуск любого слоя означает, что поле не дойдёт до фронта.
- Запрос управляется фиче-флагом `bphGetLinkedEvents.active` и `ExecutionProcess.isBphLinked...Enabled()` — учесть в конфигурации и тестах.
- Тестовые фикстуры BPH (`json/response/bph/*`, `json/response/feed/bph_linked_events/*`) нужно обновить под новое поле.

## Что учесть при написании фичи

- Добавлять поле в контракты (`bph.yml`, `history.yml`), а не хардкодить в коде; DTO регенерируются.
- Сквозной проброс: BPH `OperationData.yield` → wrapper/leaf-конвертер → внутренняя модель операции → `history.yml` → screen-api composite.
- Согласовать уровень поля: операция (`OperationData`) vs сделка/заявка (deal/order) — от этого зависит, в каких конвертерах его читать.
- Обновить матрицу полей (`05-Data/field-matrix/source-to-operation-fields.md`) и тестовые фикстуры BPH.
- Проверить опциональность поля и поведение при его отсутствии в ответе BPH.

## Открытые вопросы / что проверить

| ID | Вопрос | Где искать ответ |
|---|---|---|
| Q-01 | Финальное имя поля «доходность» в каждом контракте (BPH `bph.yml`, исходящий `history.yml`, BDUI) — `yield`, `profitability` или иное? | Согласовать с владельцами контрактов BPH и screen-api |
| Q-02 | Что именно «добавить в интеграцию» как параметр запроса: флаг включения возврата доходности (`withYield`) или иной фильтр? Возвращает ли BPH `yield` безусловно? | Команда BPH; `RequestLinkedData` в `bph.yml` |
| Q-03 | На каком уровне ответа лежит доходность: `OperationData` (lead) или `DetailData` / уровень сделки? | `bph.yml` схемы `OperationData`/`DetailData`; команда BPH |
| Q-04 | Какой композит/секция BDUI отображает поле и в каком формате (валюта, проценты)? | `history-ops-screen-api/.../composite`, `.../services/screen/composite` |
| Q-05 | Нужно ли сохранять/маппить `yield` в БД `history-ops` или это транзитное поле ответа? | `05-Data/entities/source-config.md`, `OperationDAO`/модель `Operation` |
| Q-06 | Тип и точность значения (`big_decimal`, как `PriceData`)? | `bph.yml` (`PriceData`, `format: big_decimal`) |

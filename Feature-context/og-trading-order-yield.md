# Контекст для фичи: og-trading-order-yield

## Задача (бриф)

> Доработать интеграцию `history-ops` ↔ **Order Gateway (ОГ)** так, чтобы в ответе
> `GetTradeOrders` для **торговой заявки** приходило значение **доходности**. Имя
> поля в контрактах команда выбирает сама (рабочее имя — `yield`).
> «Так же» — симметрия с параллельной доработкой по BPH (`GetLinkedEvents`, см.
> `Feature-writing/bph-linked-events-yield/bph-linked-events-yield.md`): доходность
> должна появиться и на пути заявок из ОГ, а не только из BPH linked events.

**Трактовка.** Нужно добавить показатель «доходность» в поток торговых заявок,
приходящих из Order Gateway: (1) новое поле в контракт OG `TradeOrder`
(`order-gateway.proto`), (2) чтение и маппинг поля в `history-ops` при обработке
`GetTradeOrders`, (3) проброс через исходящий контракт `history-ops`
(`history.yml` / gRPC `historyOperationDetails.proto`), (4) учёт в композите BDUI
(`history-ops-screen-api`). Рабочее имя поля — `yield`; финальное имя и формат
необходимо согласовать. Решение должно быть симметрично фиче
`bph-linked-events-yield` (тот же признак, но для заявок из ОГ).

Термины: **ОГ / OG** = Order Gateway — сервис торговых заявок и сделок
АС СберИнвестор 2; **HO / ИО** = `history-ops`; **BPH** — источник связанных
событий; **BDUI** — экранный сервис `history-ops-screen-api`.

## Затронутые области

| Область | Что затрагивается | Документы / код |
|---|---|---|
| Контракт OG (вход) | Новое поле в message `TradeOrder` (`order-gateway.proto`) | `repositories/ИО/history-ops/src/main/proto/order-gateway.proto` |
| Gateway OG | Вызов `GetTradeOrders` | `counter/adapter/GetTradeOrdersGateway.java`, `adapter/order_gateway/OrderGrpcGateway.java` |
| Маппинг ответа OG | Чтение `TradeOrder` → `OrderGatewayOrderWrapper` | `adapter/order_gateway/converter/OrderGrpcConverter.java` |
| Модель-обёртка OG | Поле в wrapper | `adapter/order_gateway/OrderGatewayOrderWrapper.java` |
| Создание операции из OG-заявки | Сборка `ReportOrderOperationDetails` | `service/conversion/operation/creator/OgTradeOperationCreator.java` |
| Слияние заявок OG/BPH | Приоритет OG, merge | `service/conversion/operation/merger/OrderMerger.java` |
| Исходящий REST-контракт HO | Новое поле в `history.yml` | `repositories/ИО/history-ops/src/main/swagger/history/history.yml` |
| Исходящий gRPC-контракт HO | Новое поле в `historyOperationDetails.proto` | `repositories/ИО/history-ops-grpc-client/.../historyOperationDetails.proto` |
| Композит BDUI | Учёт доходности на экране | `repositories/ИО/history-ops-screen-api/.../composite/screen/...` |
| Фиче-тоглы | Управление запросом к OG | `counter/CounterFeatureToggleName.java`, `analytics/.../integrations/feature-toggle.md` |

## Релевантная аналитика и спеки

| Документ | Что описывает | Почему релевантно задаче |
|---|---|---|
| `analytics/02-Modules/MOD-001-history-ops/integrations/order-gateway.md` | Интеграция HO ↔ OG: `GetTradeOrders`/`GetDeals`, полный список полей `TradeOrder`, маппинг в SEND_OPERATIONS, приоритет OG при слиянии, тоглы | Основной источник бизнес-контекста и AS IS по заявкам из ОГ; здесь перечислены все текущие поля ответа (доходности нет) |
| `analytics/02-Modules/MOD-001-history-ops/integrations/bph.md` | Интеграция HO ↔ BPH, второй приоритет заявок, комиссии | Объясняет, откуда берутся заявки, отсутствующие в OG, и как OG-заявка сливается с BPH |
| `analytics/02-Modules/MOD-001-history-ops/integrations/feature-toggle.md` | Каталог тоглов HO (в т.ч. `enableOrderGatewayRequestDates`, `enableOgNewActiveOrdersEndpoint`) | Механизм включения/выключения веток интеграции с OG, нужен для оценки влияния |
| `analytics/02-Modules/MOD-001-history-ops/behavior/bph-response-processing.md` | Обработка ответов BC/BPH (DB-aware mapping) | Образец маппинга источника в операцию; полезно для симметричного описания OG-пути |
| `analytics/02-Modules/MOD-001-history-ops/behavior/feed-orchestration.md` | Дедупликация и merge ответов источников | Контекст, в котором OG-заявки сливаются с BPH/BC |
| `analytics/02-Modules/MOD-001-history-ops/api/get-active-orders-number.md` | Использование `GetTradeOrders` для активных заявок | Дополнительный потребитель того же контракта |
| `Feature-writing/bph-linked-events-yield/bph-linked-events-yield.md` | **Образец симметричной фичи**: поле `yield` в `GetLinkedEvents` | Задаёт терминологию, имя поля, сквозной путь слоёв и структуру решения, которое нужно повторить для ОГ |
| `Feature-context/bph-linked-events-yield.md` | Контекст-документ BPH-фичи, перечень Q-01…Q-06 | Согласование имени поля и уровня (Q-01, Q-03) должно быть общим для обеих фич |

> В `analytics/` **нет** отдельного документа/требования про «доходность»
> (проверено grep по `доходност|yield` — совпадений нет). Фича проистекает из
> брифа; источник значения доходности в аналитике не описан.

## Релевантный код

| Файл | Компонент (класс / метод / proto) | Текущее поведение | Почему важно |
|---|---|---|---|
| `repositories/ИО/history-ops/src/main/proto/order-gateway.proto` | `service OrdersService.rpc GetTradeOrders` (стр. 14); `message TradeOrder` (стр. 71, поля 1–41); `message GetTradeOrdersResponse` (стр. 59) | Контракт OG. `TradeOrder` содержит 41 поле (id, agreement, direction, type, currency, created_time, instrument_count, value_per_instrument_item, total_deals_value, commission_value, total_deals_commission, total_sum, stop_loss_px, take_profit_px, initial_margin, brokerage_commission, exchange_commission, time_in_force, contra_broker, card_number и др.). **Поля доходности (`yield`) нет** | **Точка добавления №1**: новое поле доходности в `TradeOrder`. Источник — команда OG (proto лежит в `trade-operations-commons`) |
| `.../counter/adapter/GetTradeOrdersGateway.java` | `GetTradeOrdersGateway` (`rpcName()=OG_ORDERS`, `exSystem()="OG"`, `eventType()="GET_TRADE_ORDERS"`) | Вызывает `ReactorOrdersServiceStub::getTradeOrders`, возвращает `GetTradeOrdersResponse.getOrdersList()` | Точка вызова OG; поле проезжает «сквозь» без обработки |
| `.../adapter/order_gateway/converter/OrderGrpcConverter.java` | `OrderGrpcConverter.convert(TradeOrder, ExecutionProcess)` (строки ~105–145) | Читает поля `TradeOrder` (в т.ч. `getTotalSum()`, `getCommissionValue()`, `getInitialMargin()`) и собирает `OrderGatewayOrderWrapper` через конструктор | **Точка маппинга №2**: здесь новое proto-поле читается и попадает в wrapper |
| `.../adapter/order_gateway/OrderGatewayOrderWrapper.java` | `OrderGatewayOrderWrapper` (Lombok `@Builder`/`@AllArgsConstructor`) | Внутренняя модель OG-заявки: 41 поле без доходности (type, generalStatus, timeHappened, id, siId, agreementNumber, totalSum, commissionValue, initialMargin, timeInForce, contraBroker, cardNumber и др.) | **Точка добавления №3**: поле доходности в wrapper |
| `.../service/conversion/operation/creator/OgTradeOperationCreator.java` | `OgTradeOperationCreator.createTradeOperationByOg(...)` (стр. ~80–215) | Строит `HistoryOperationLead` и `ReportOrderOperationDetails` из `OrderGatewayOrderWrapper` + сделок OG; собирает комиссии, deals, expireDate | **Точка проброса №4**: доходность из wrapper → в исходящую модель операции |
| `.../service/conversion/operation/merger/OrderMerger.java` | `OrderMerger` | Слияние OG-заявок с BPH/BC (приоритет OG) | Учесть: при merge доходности из разных источников не должны конфликтовать (аналогично BPH-фиче) |
| `.../counter/conversion/operation/OgConverter.java` | `OgConverter.convert(TradeOrder)` | Для active-orders ветки строит `ActiveOperationWrapper(id, idForDeduplication, agreement, date, status)` — **без** доходности | Вторая ветка использования OG (active orders); проверить, нужна ли доходность и там |
| `repositories/ИО/history-ops/src/main/swagger/history/history.yml` | `components.schemas.ReportOrderOperationDetails` (стр. 376), `HistoryOperationLead` (стр. 461) | Исходящий REST-контракт HO. `ReportOrderOperationDetails` содержит order_type, commission_value, total_deals_commission, initial_margin, deals[], time_in_force и др.; `HistoryOperationLead` — id, type, general_status, total_sum, total_deals_volume. **Доходности нет** | **Точка добавления №5** (REST), иначе поле не дойдёт до screen-api/фронта |
| `repositories/ИО/history-ops-grpc-client/.../historyOperationDetails.proto` | message с полями-комментариями `// REPORT ORDER OPERATION` (поля 65–98), `ReportDeal` | Исходящий gRPC-контракт HO, который потребляет screen-api. Последние занятые номера: `auto_follow = 98`; `// REPORT ORDER OPERATION` содержит commission_value, total_deals_value, initial_margin, contra_broker_id и т.д. **Доходности нет** | **Точка добавления №5'** (gRPC): новое поле получит следующий свободный номер (>98) |
| `repositories/ИО/history-ops-screen-api/.../composite/screen/details/operation/sections/customizers/*` | Десятки `*Customizer` (OrderTypeCustomizer, CommissionCustomizer, BondAccruedInterestCustomizer, InitialMargin и др.) | Композит BDUI по заявкам/сделкам собирается из исходящих данных HO | **Точка учёта №6**: новый кастомайзер/секция для доходности |

## Данные (БД, выгрузки)

| Таблица / поле | Где найдено | Текущее устройство | На что влияет фича |
|---|---|---|---|
| ОГ-заявки/сделки (payload) | Приходят gRPC-ответом `GetTradeOrders`/`GetDeals`, не из БД HO | HO не хранит поля OG-заявки как таковые; операция формируется в рантайме | По аналогии с BPH-фичей доходность, вероятно, транзитное поле ответа, а не колонка БД (требует подтверждения — Q-05) |
| `history_ops.*` (общие таблицы) | `db-export/БД ИО.md` | Метаданные операций, связки типов BPH/BC/OG | Отдельной колонки/таблицы под «доходность» в выгрузке не найдено |

> По проверенным данным отдельной таблицы/колонки для доходности в `db-export/`
> нет. Это согласуется с BPH-контекстом. Требует подтверждения владельцем
> данных (Q-05).

## Интеграции и контракты, которые нужно учесть

- **Контракт OG**: `order-gateway.proto` — оригинал лежит в
  `trade-operations-commons/trade-operations-api/src/main/proto/order-gateway.proto`
  (см. комментарий в начале файла). Правка поля — на стороне команды OG, затем
  ребилд proto-стабов в HO. Рабочее имя `yield`; тип, вероятно,
  `optional google.type.Decimal` (по образцу `commission_value`,
  `value_per_instrument_item`). Свободный номер поля — 42+.
- **gRPC OG всегда включён**: `OrderGrpcGateway.enabled() = true`; отдельного
  тогла на сам вызов `GetTradeOrders` нет. Тоглы `enableOrderGatewayRequestDates`
  и `enableOgNewActiveOrdersEndpoint` меняют форму запроса (даты/активные), но не
  состав ответа.
- **Приоритет OG**: OG `GetTradeOrders` — приоритетный источник заявок; BPH
  `GetLinkedEvents` дозаполняет отсутствующие. Значит, доходность для OG-заявок
  должна приходить из OG, а не «подмешиваться» из BPH. Симметрия с BPH-фичей
  означает наличие **того же поля** в обоих источниках.
- **Исходящие контракты HO**: поле нужно добавить и в `history.yml` (REST), и в
  `historyOperationDetails.proto` (gRPC клиент для screen-api) — иначе не дойдёт
  до фронта.
- **Сквозной путь слоёв** (по образцу BPH-фичи): OG `TradeOrder` →
  `OrderGrpcConverter` → `OrderGatewayOrderWrapper` → `OgTradeOperationCreator` →
  исходящая модель (`ReportOrderOperationDetails`/`HistoryOperationLead`) →
  `history.yml` / proto → screen-api composite. Пропуск слоя = поле не дойдёт.
- **BDUI-композит**: учёт доходности на экране — в
  `history-ops-screen-api` (секции/кастомайзеры по заявкам). Композит/секция и
  формат (валюта/проценты) не подтверждены → Q-04.

## Ограничения и риски текущего состояния

- **Поле отсутствует на всех слоях**: ни в proto OG, ни в wrapper, ни в
  `OgTradeOperationCreator`, ни в `history.yml`, ни в `historyOperationDetails.proto`
  доходности нет (подтверждено чтением файлов). Значит нужны изменения во всех
  перечисленных точках, а также ребилд генерируемых DTO/стабов.
- **Proto OG — внешний контракт**: изменение делает команда OG в
  `trade-operations-commons`; HO лишь пересобирает стабы. Блокирующая зависимость
  от внешней команды.
- **Обратная совместимость**: новое поле должно быть `optional` — текущие ответы
  OG без доходности не должны ломать конвертацию и валидацию
  (`validateSimpleAttributes` требует непустые currency/ticker/classCode).
- **Две ветки OG**: история (`GetTradeOrders`) и активные заявки
  (`GetActiveOrders`/`OgConverter`, `ActiveOrderConverter`). Решение по
  доходности должно быть распространено осознанно (только история или обе ветки).
- **Слияние с BPH**: OG-заявка приоритетна; при merge нужно понять, что делать,
  если доходность есть и в BPH-linked-events (общий признак для симметрии).
- **Тестовые фикстуры**: обновить JSON-ответы OG
  (`json/response/feed/...`, тесты `OrderFilterServiceTest`,
  `OrderMergerTest`, `HistoryOpsGrpcServiceTest`) под новое поле.
- **Аналитика не описывает источник доходности**: не зафиксировано, кто/как
  вычисляет доходность для заявки OG (сам OG или HO) → ключевой открытый вопрос.

## Что учесть при написании фичи

- Добавлять поле через контракты (proto OG, `history.yml`,
  `historyOperationDetails.proto`), а не хардкодить в коде.
- Соблюдать сквозной путь: `TradeOrder` → `OrderGrpcConverter` →
  `OrderGatewayOrderWrapper` → `OgTradeOperationCreator` → исходящая модель →
  screen-api composite.
- Согласовать с BPH-фичей **единое имя и семантику** поля (`yield`), чтобы признак
  был консистентен на обоих путях (заявки из ОГ и связанные события BPH).
- Зафиксировать: кто вычисляет доходность (OG или HO), для каких типов заявок она
  применима (BUY/SELL, limit/market/stop*), в каком формате приходит
  (decimal/проценты/валюта) и что делать при отсутствии значения.
- Проверить опциональность поля и корректность обработки `null`.
- Обновить исходящий gRPC-контракт для screen-api и учесть новое поле в
  композите BDUI.
- Обновить тестовые фикстуры и тесты OG-пути.
- Проверить обе ветки OG (история и активные заявки).

### Актуализация после resolve (2026-09-13)

Решения из resolve, которые писатель и ревьюер должны считать актуальнее исходного current-state:

- Кластер: Затронутые § (при apply)
- ---------: --------------------------
- Формат/тип/имя поля (OG vs BPH `PriceData`): §1.1, §2 (CN/ASM), §4.1.1 (proto OG, REST, gRPC), §4.2.3, §4.2.4 (маппинг)
- Уровень размещения поля (lead vs детали) + BDUI: §4.1.1.3, §4.2.2, §4.2.3
- Источник значения (кто вычисляет) + транзитность: §1.2, §1.3, §2 (ASM-01), §4.2.2, §4.2.3
- Scope (активные заявки) + фиче-тогл: §1.2.1, §1.3.1, §2, §5.5
- Merge с BPH + отсутствующее/нулевое/отрицательное: §1.3.1, §2, §4.1.1, §4.2.2, §4.2.4
- SMART: метрика и срок/релиз: §1.1
- Готовность контракта ОГ + ребилд + перечень слоёв: §2 (CN-02, CN-04), §4.2.4, §4.1.1.2
- Контракт/ребилд (D-07): ## Сессия 2 (2026-06-18) — apply батча 1

Правило (skill `resolve-gaps`): Decision есть в `DECISIONS` для всех Relates —
применить ко **всем** GAP кластера, переписать §, удалить следы `[GAP-...]`.
Status → `applied`.
- D-01: Поле — объект `{value, currency}` (`PriceData`), имя `yield`; OG приведён к объекту; плоские `google.type.Decimal`/`number`/`double` заменены
- D-02: Уровень lead `HistoryOperationLead`; детали `ReportOrderOperationDetails` для доходности не используются; composite/BDUI секция не меняется
- D-03: ОГ отдаёт готовое значение; `history-ops` читает/пробрасывает; поле транзитное, схема БД без миграций
- D-04: Scope — только `GetTradeOrders` (история); активные заявки вне scope; отдельного фиче-тогла нет
- D-05: Приоритет ОГ; нет значения в ОГ → подмешивание из BPH linked events; иначе поле `null`/опускается; `0` отображается; отрицательные допускаются
- D-06: Релиз — как у симметричной BPH-фичи `bph-linked-events-yield`; отдельная количественная метрика не задаётся
- D-07: `history-ops` разрабатывает первыми, контракт задаётся этой аналитикой; OG реализует после; версии proto с полем нет; слои `history-ops` подтверждены
- GAP-OBS-01…GAP-OBS-09: ## Сессия 3 (2026-09-12) — apply батча 2

Правило (skill `resolve-gaps`): Decision есть в `DECISIONS` для всех Relates —
применить ко **всем** GAP кластера, переписать §, удалить следы `[GAP-...]`.
Status → `applied`.
- D-08: Контракт `GetTradeOrders` as-is: deadline `grpc.order_gateway.deadline` (тест 50000 ms), retry — стандартный gRPC-клиент, metadata без доп. заголовков, коды по факту кода; SLA/p85 — отдельным запросом эксплуатации
- D-09: Merge доходности: непустая ОГ побеждает; пустая → из BPH; `PriceData` без трансформации в исходящий контракт

**Якоря полей из актуальной SPEC:**

`yield`, `GetTradeOrders`, `TradeOrder`, `history.yml`, `historyOperationDetails.proto`, `HistoryOperationLead`, `null`, `optional`, `true`, `number`, `OrdersService`, `time_in_force`

См. также § «Закрытые вопросы» ниже — не переспрашивать закрытые Q.
## Открытые вопросы / что проверить

| ID | Вопрос | Где искать ответ |
|---|---|---|
| Q-01 | Финальное имя поля «доходность» в proto OG (`TradeOrder`), `history.yml` и gRPC-прото screen-api — `yield`, `profitability`, `yield_value` или иное? | Владельцы контрактов OG (`trade-operations-commons`) и screen-api; согласовать с Q-01 фичи `bph-linked-events-yield` |
| Q-02 | Кто вычисляет доходность для торговой заявки OG — сам Order Gateway возвращает готовое значение, или HO должен вычислять его (напр., из цены/количества/сделок)? | Команда OG; продуктовая постановка; `analytics/.../integrations/order-gateway.md` (источник значений не описан) |
| Q-03 | Тип/точность поля в proto OG: `optional google.type.Decimal` (как `commission_value`) или строка/иной формат? Единица: валюта, проценты, коэффициент? | Команда OG; образец — существующие decimal-поля `order-gateway.proto` |
| Q-04 | Какой композит/секция BDUI отображает доходность по заявке и в каком формате (валюта, %, знак)? | `repositories/ИО/history-ops-screen-api/.../composite/screen/details/operation/...`; владелец BDUI |
| Q-05 | Транзитное ли поле доходности (только ответ) или его нужно сохранять/маппить в БД HO? | `db-export/БД ИО.md`, `OperationDAO`/модель `Operation`; согласовать с Q-05 фичи `bph-linked-events-yield` |
| Q-06 | Нужна ли доходность для активных заявок (`GetActiveOrders`/`ActiveOrder`, `ActiveOrderConverter`, `OgConverter`) или только для истории (`GetTradeOrders`)? | Бриф; команда OG; `analytics/.../api/get-active-orders-number.md` |
| Q-07 | Что делать при отсутствии доходности в ответе OG: поле опускается/`null`/не отображается, и как это влияет на merge с BPH-linked-events? | Продуктовая постановка; `OrderMerger`; согласовать с BPH-фичей |
| Q-08 | Нужен ли отдельный фиче-тогл для возврата/отображения доходности (по аналогии с параметром интеграции в BPH-фиче)? | Команда OG; `counter/CounterFeatureToggleName.java`, `analytics/.../feature-toggle.md` |
| Q-09 | Точный перечень полей-слоёв, которые нужно править: подтвердить, что исходящий контракт для front — именно `historyOperationDetails.proto` (+ `history.yml`), и нет ли ещё одного потребителя OG-заявок | `repositories/ИО/history-ops-grpc-client/`, `history-ops-screen-api`; проверить при `/check-feature-code` |

## Закрытые вопросы

> Заполняется скиллами `/resolve-*`. Строки из «Открытые вопросы» не удаляются —
> история сохраняется. Ниже — решения по вопросам, отработанным `resolve-gaps`.
> **Сессия 1 (2026-06-18):** вопросы вынесены как `needs-answer` (D-01…D-07).
> **Сессия 2 (2026-06-18):** ответы пользователя получены, батч 1 **применён**
> (`Status = applied`) — решения ниже актуальны, SPEC переписан.
> **Сессия 3 (2026-09-12):** ответы по батчу 2 получены, батч 2 (D-08…D-18 —
> контрактные детали, NFR, OBS, BDUI, lineage) **применён** (`Status = applied`);
> SPEC переписан, следы `[GAP-...]` удалены. Открытых GAP в SPEC — 0.
> **Сессия 4 (2026-09-13):** шаг `resolve-code-alignment` (итерация 2). Ответы по
> батчу 4 (D-30…D-34 — находки код-аудита) **применены** (`Status = applied`);
> SPEC переписан, вердикт alignment пересчитает следующий `/check-feature-code`.

| ID | Дата | Решение | Где в spec | Источник |
|----|------|---------|------------|----------|
| Q-01 | 2026-06-18 | **Закрыт (applied, D-01 = B):** единое имя поля — `yield`, тип — сообщение `PriceData {value, currency}` везде (OG proto, `history.yml`, `historyOperationDetails.proto`); OG-спека приведена к объекту, симметрия с BPH сохранена | §1.3 (preconditions), §2 (CN/ASM), §4.2.4 (lineage/маппинг) | `DECISIONS` D-01 (applied); sibling `bph-linked-events-yield` |
| Q-02 | 2026-06-18 | **Закрыт (applied, D-03 = A):** доходность вычисляет ОГ и отдаёт готовое значение; `history-ops` только читает и пробрасывает | §1.3 (main scenario), §2 (ASM-01) | `DECISIONS` D-03 (applied) |
| Q-02 | 2026-09-12 | **Дополнено (applied, D-18 = A):** новых error/бизнес-метрик и фронтовых UI-событий по доходности не вводится; логирование — по существующей схеме; трассировка — существующий `traceId` | §5.3 | `DECISIONS` D-18 (applied) |
| Q-03 | 2026-06-18 | **Закрыт (applied, D-01 = B):** тип поля — `PriceData {value, currency}` (value = `google.type.Decimal`, currency — строка); плоские `Decimal`/`double`/`number` не используются | §2 (CN/ASM), §4.2.4 (маппинг), §4.1.1 | `DECISIONS` D-01 (applied) |
| Q-04 | 2026-06-18 | **Закрыт по уровню (applied, D-02 = A):** доходность — на уровне lead `HistoryOperationLead`; детали `ReportOrderOperationDetails` не используются | §1.3 (main scenario, «Изменения»), §4.2.4 (BDUI), §5.2 (NFR-09) | `DECISIONS` D-02 (applied) |
| Q-04 | 2026-09-12 | **Формат отображения BDUI закрыт (applied, D-10 = A):** отдельная секция карточки торговой заявки, формат «{value} {currency}», знак числа как есть; также закрыты §5.1-безопасность (D-14) и §5.2-нагрузка (D-15) | §1.3 (BDUI), §4.1.1.3, §4.2.4, §5.1, §5.2 | `DECISIONS` D-10, D-14, D-15 (applied) |
| Q-05 | 2026-06-18 | **Закрыт (applied, D-03 = A):** поле транзитное; схема БД `history-ops` не меняется, миграции не нужны | §1.3 (preconditions), §5.4 | `DECISIONS` D-03 (applied) |
| Q-06 | 2026-06-18 | **Закрыт (applied, D-04 = A):** scope — только `GetTradeOrders` (история); активные заявки (`GetActiveOrders`/`OgConverter`/`ActiveOrder`) вне scope | §1.3 (blockquote), §1.3.1 | `DECISIONS` D-04 (applied) |
| Q-07 | 2026-06-18 | **Закрыт (applied, D-05 = A):** приоритет ОГ; нет значения в ОГ → подмешивание доходности из BPH linked events; иначе поле опускается/`null`; `0` отображается; отрицательные допускаются | §1.3 (postconditions, alt 3a), §5.2 (graceful degradation) | `DECISIONS` D-05 (applied) |
| Q-07 | 2026-09-12 | **Правило мёржа закрыто (applied, D-09 = A):** непустая доходность ОГ побеждает; если пустая — берётся доходность BPH, `PriceData` переносится без трансформации. Доп.: ошибка чтения не влияет на отдачу заявки — WARN, поле опускается (D-13) | §4.1.1.2 (алгоритм), §1.3 (изменения), §2 | `DECISIONS` D-09, D-13 (applied) |
| Q-08 | 2026-06-18 | **Закрыт (applied, D-04 = A):** отдельного фиче-тогла на возврат/состав доходности нет — доходность часть ответа ОГ, возврат не гейтится | §1.3 (blockquote), §5.5 (NFR-20) | `DECISIONS` D-04 (applied) |
| Q-08 | 2026-09-12 | **Дополнено (applied, D-12 = D):** в аналитике не описываются классы/внутренние ДТО — только алгоритм; AS IS и §4.1.1.2 процессно, без имён методов и таймингов | §1.2 (AS IS), §4.1.1.2 | `DECISIONS` D-12 (applied) |
| Q-09 | 2026-06-18 | **Частично закрыт (applied, D-07):** перечень слоёв `history-ops` подтверждён (`history.yml` + `historyOperationDetails.proto` + тесты/фикстуры); `history-ops` разрабатывает первой, контракт задаётся этой аналитикой, ОГ реализует после; версии proto с полем ещё нет | §2 (CN-02/CN-04), §4.1.1.2, §4.2.4 | `DECISIONS` D-07 (applied) |
| Q-09 | 2026-09-12 | **Контрактные детали закрыты (applied, D-08 = A):** deadline `grpc.order_gateway.deadline` (тест 50000 ms), retry — стандартный gRPC-клиент, metadata без доп. заголовков, gRPC-коды по факту кода; числовой SLA/p85 — отдельный запрос эксплуатации. Контрактные имена закрыты (applied, D-11 = A): поле `yield` типа `PriceData`, номер 99, lead `HistoryOperationLead` | §4.1.1.1 (таблица вызова), §4.2 (lineage) | `DECISIONS` D-08, D-11 (applied) |
| F-01 / I-05 | 2026-09-13 | **Закрыт (applied, D-30 = A):** `ex_system`/`exSystem` для ОГ приведён к коду — `"OG"` (в коде `OrderGrpcGateway.exSystem()`/`GetTradeOrdersGateway.exSystem()` возвращают `"OG"`); значение `ORDER_GATEWAY` в §1.3/§5.1/§5.3 заменено; статус «Подтверждено кодом» корректен | §1.3, §5.1 (аудит-таблица), §5.3 (лог-события, структура полей, метрики) | `DECISIONS` D-30 (applied); `ALIGNMENT` F-01 |
| F-02 / T-06 | 2026-09-13 | **Закрыт (applied, D-31 = A):** `bphGetLinkedEvents.active` — ключ **динамического ConfigMap** (`app-config-dynamic.instrument-filter-requests-dynamic`), **не** Auth-тогл; убран из таблицы Auth-тоглов §5.5, описан в §5.4 (конфигурация) | §5.4 (таблица настроек), §5.5 | `DECISIONS` D-31 (applied); `ALIGNMENT` F-02 |
| F-05 / I-07 | 2026-09-13 | **Закрыт (applied, D-32 = A):** `serviceName` = `history_ops` (нижний регистр, `SessionServiceGateway.SERVICE_NAME`) во всех упоминаниях §5.5 (было `HISTORY_OPS`) | §5.5 (таблица тоглов, «Условия применения») | `DECISIONS` D-32 (applied); `ALIGNMENT` F-05 |
| F-03 / C-10 | 2026-09-13 | **Закрыт (applied, D-33 = A):** в §4.1.1.1/§4.1.1.3 добавлена ссылка — форма `PriceData {value, currency}` совпадает с существующим `PriceData` в `bph.yml` (стр. 1226–1240); при общем пакете переиспользовать тип; имя пакета — за владельцем контракта | §4.1.1.1 (примечание к proto), §4.1.1.3 (примечание о разделяемом типе) | `DECISIONS` D-33 (applied); `ALIGNMENT` F-03 |
| F-04 | 2026-09-13 | **Закрыт (applied, D-34 = B):** cross-refs `§4.2.3`/`§4.2.4` заменены на текстовые названия разделов «Модель данных» / «Маппинг данных»; нумерация заголовков не менялась | §2 (CN-17), §4.2 (связанные артефакты), §5.1/§5.4/§6/§7 | `DECISIONS` D-34 (applied); `ALIGNMENT` F-04 |

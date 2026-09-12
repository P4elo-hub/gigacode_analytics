# Контекст для фичи: composite-active-order-commission

## Задача (бриф)

На композите активной заявки (вкладка «Активные заявки» ленты операций ИО) для
карточек `transaction_buy` / `transaction_sell` в активных статусах
(`in_progress` / `cancelling`) показывать шильдик с **предрасчитанной** комиссией —
(`commission_value`), а **не** фактической комиссией по сделкам
(`total_deals_commission`). Предрасчёт приходит из Order Gateway; его нужно
пробросить до композита и отобразить. Для BPH linked events требуется новая
прекалька — параметр `precalc_commission`.

## Затронутые области

| Область | Что затрагивается | Документы / код |
|---|---|---|
| Интеграция ИО ↔ Order Gateway | проброс `commission_value` (OG) в `SEND_OPERATIONS` → `GetDetailsResponse` | `analytics/02-Modules/MOD-001-history-ops/integrations/order-gateway.md`; `repositories/ИО/history-ops-grpc-client/.../historyOperationDetails.proto` |
| История операций (history-ops) | поле `commission_value` в proto-модели деталей операции | `historyOperationDetails.proto:60` (`GetDetailsResponse`), поле 65 |
| Композит (screen-api) | рендер шильдика комиссии на feed-карточке активной заявки | `repositories/ИО/history-ops-screen-api/.../feed/section/customizers/TransactionChipsContentCustomizer.java`, `ChipsContent.java` |
| BPH linked events | новый параметр прекальки `precalc_commission` | `analytics/02-Modules/MOD-001-history-ops/integrations/bph.md` |
| Статусы операций | условие показа — `general_status ∈ {in_progress, cancelling}` | `analytics/05-Cross-Cutting/operation-status-catalog.md` |

## Релевантная аналитика и спеки

| Документ | Что описывает | Почему релевантно |
|---|---|---|
| `analytics/02-Modules/MOD-001-history-ops/integrations/order-gateway.md` | Контракт `GetTradeOrders`; строки 111–113: `orders.[].commission_value` = «Предрасчитанная комиссия», `total_deals_commission` = «Фактическая комиссия по сделкам». Строка 256: маппинг `GetTradeOrders commission_value → HO commission_value (decimal, предрасчёт из OG)` | Прямой источник значения: комиссия-прекалька приходит из OG и уже замаплена в HO |
| `analytics/05-Cross-Cutting/operation-status-catalog.md` | Единая агрегированная модель `general_status` для HO/композита/МП | Определяет, какие статусы считаются «активными» (`in_progress`, `cancelling`) — условие показа шильдика |
| `analytics/02-Modules/MOD-001-history-ops/behavior/operation-type-catalog.md` | Маппинг типов операций МП ↔ BPH/BC/OG | Типы `transaction_buy` / `transaction_sell` — целевые для фичи |
| `analytics/02-Modules/MOD-001-history-ops/integrations/bph.md` | Интеграция HO ↔ BPH, linked events | Контекст для новой прекальки `precalc_commission` в BPH linked events |
| `analytics/02-Modules/MOD-001-history-ops/behavior/bph-response-processing.md` | Обработка ответов BC и BPH (DB-aware mapping) | Как маппится ответ BPH в детали операции |
| `Feature-writing/bph-linked-events-yield/bph-linked-events-yield.md` | Соседняя фича: проброс нового параметра (yield) из BPH linked events до UI | Прецедент паттерна «новый параметр из источника → контракт → композит» |
| `Feature-writing/og-trading-order-yield/og-trading-order-yield.md` | Соседняя фича: проброс `yield` из ответа OG `GetTradeOrders` (с обогащением из BPH) | Прецедент проброса нового поля из OG до фичи, тот же источник `GetTradeOrders` |
| `analytics/03-UseCases/UC-006-conditional-and-futures-orders.md` | Use case условных и фьючерсных заявок; упоминает `commission_value` | Сценарий отображения комиссии по условным заявкам |

## Релевантный код

| Файл | Компонент | Текущее поведение | Важно для фичи |
|---|---|---|---|
| `repositories/ИО/history-ops-grpc-client/history-ops-grpc-client-api/src/main/proto/historyOperationDetails.proto` | `message GetDetailsResponse` (стр. 60), поля 65–72: `commission_value` (65), `commission_value_stop_loss` (66), `commission_value_take_profit` (67), `total_deals_commission` (72) | В gRPC-модели уже есть и `commission_value` (предрасчёт), и `total_deals_commission` (факт) | Значение прекальки доступно в контракте HO; проверить заполнение для активных заявок |
| `.../history-ops-screen-api/.../feed/section/customizers/TransactionChipsContentCustomizer.java` | `TransactionChipsContentCustomizer.customize`, `ACTIVE_STATUSES = {CANCELLING, IN_PROGRESS}`, `getSupportedTypes = {TRANSACTION_BUY, TRANSACTION_SELL}` | Для активных `transaction_buy`/`transaction_sell` строит `chipsContent` через `ChipsContent`; в JSON кладёт только чипы цены/срока | Точка подключения шильдика комиссии: именно здесь формируется `chipsContent` для активных заявок |
| `.../history-ops-screen-api/.../composite/sections/feed/ChipsContent.java` | `ChipsContent.enrich*`, `resolveValueByOrderType`, `resolvePostfix` | Формирует `params[]` из `logoIcon` (срок) и ценовых текстов (`Стоп-цена`, `Цена не выше/не ниже`, `Цена тейк-профит`); комиссию **не** рендерит | Текущее отсутствие шильдика комиссии — что нужно добавить |
| `.../history-ops-screen-api/.../sections/feed/section/creators/AbstractTransactionOperationSectionCreator.java` | `buildContext`, `getPrefixTotalSum`, абстрактные `resolveTitleText` / `getPrefixForExecutedStatus` | Строит контекст секции; определяет префикс суммы `~` для `cancelling`/`in_progress` | Логика активных статусов заявки на секции |
| `.../history-ops-screen-api/.../sections/feed/section/creators/TransactionBuyOperationSectionCreator.java` | `resolveTitleText` («Покупка …»), `getPrefixForExecutedStatus` («−»), `getType = TRANSACTION_BUY` | Реализация создателя секции покупки | Целевой тип карточки |
| `.../history-ops-screen-api/.../sections/feed/section/creators/AbstractSectionCreator.java` | `createSection`, `createContent`, `resolveType` | Тип секции `history.feed.operationActive` для активных статусов, иначе `history.feed.operation`; прогоняет кастомайзеры через `FeedSectionCustomizerRegistry` | Механика расширения content кастомайзерами |
| `.../history-ops-screen-api/.../customizers/CommissionSubtitleCustomizer.java` | `CommissionSubtitleCustomizer` (support: `SectionCreatorType.COMMISSION`), `resolveDirection` | Отдельная секция/подзаголовок для операций типа COMMISSION; использует `parentStopOrderType` → «Продажа»/«Покупка» | Прецедент рендера комиссии, но для типа COMMISSION, а не для торговых активных заявок |
| `.../history-ops-screen-api/.../customizers/TransactionCancellationButtonCustomizer.java` | feature-toggle проверки | Использует тоглы `enable_feed_cancellation_transaction_buy` / `..._sell` | Прецедент тоглов по типам BUY/SELL на feed-карточке (возможный шаблон фича-тогла для шильдика) |

## Данные (БД, выгрузки)

| Таблица / поле / запрос | Где найдено | Текущее устройство | На что влияет |
|---|---|---|---|
| `db-export/БД ИО.md` (раздел history-ops, источник BPH, «id, subtype, type_id, is_active») | `db-export/БД ИО.md` | Справочник по таблицам БД ИО; содержит конфигурацию источников/типов | Справочно: конфиг-строки скринов и типов операций; прямой таблицы под прекальку не найдено |
| Тестовые скрины `HISTORY_OPS_TRANSACTION_BUY_LIMIT_DETAILS_SCREEN` и др. | `.../history-ops-screen-api/src/test/resources/db/init-test-screens*.sql` | Заводят тестовые экраны для типов `transaction_buy`/`transaction_sell` | Затрагивается при добавлении нового элемента на скрин активной заявки |

## Интеграции и контракты, которые нужно учесть

- **Order Gateway → HO**: `GetTradeOrders.orders[].commission_value` — это
  **предрасчитанная** комиссия (не факт по сделкам). В HO маппится в
  `commission_value` (decimal). Якорь: `order-gateway.md` строки 111–113 и 256.
- **HO gRPC-контракт**: `historyOperationDetails.proto`, `message GetDetailsResponse`
  — поля `commission_value` (65), `total_deals_commission` (72),
  `commission_value_stop_loss` (66), `commission_value_take_profit` (67).
  Отдаётся через `rpc getOperationDetails` / `rpc getOperationsFeed`.
- **HO REST-контракт (history.yml)**: `ReportOrderOperationDetails` содержит
  `commission_value`, `total_deals_commission`, `total_brokerage_comission`,
  `total_exchange_comission`, `stop_px`, `take_profit_px`
  (`repositories/ИО/history-ops/src/main/swagger/history/history.yml`, ~стр. 370–460).
- **Композит (screen-api)**: выход — `chipsContent` JSON в content feed-секции
  (`TransactionChipsContentCustomizer` → `ChipsContent`); типа секции для активных
  заявок — `history.feed.operationActive`.
- **BPH linked events**: новый параметр `precalc_commission` — в коде **не
  найден** (см. Q-01); это изменение на стороне источника BPH + маппинг в HO.
- **Статусы**: показ только при `general_status ∈ {in_progress, cancelling}` —
  константы `ACTIVE_STATUSES` в `TransactionChipsContentCustomizer` и
  `AbstractSectionCreator`; каталог статусов — `operation-status-catalog.md`.

## Ограничения и риски текущего состояния

- В `ChipsContent` сейчас **нет** рендера комиссии — ни прекальки, ни факта. Весь
  `params[]` строится только из срока (`expire_date_details`) и ценовых полей
  (`stop_px`, `take_profit_px`, `value_by_instrument_item`). Новый шильдик —
  чистое добавление.
- `commission_value` и `total_deals_commission` присутствуют в контракте, но
  заполняются из OG (Report Order). Для карточек **активных** заявок в статусах
  `in_progress`/`cancelling` заполненность `commission_value` не подтверждена по
  коду — риск пустого значения (Q-02).
- `precalc_commission` в BPH linked events в репозиториях отсутствует —
  источниковая прекалька может быть ещё не реализована (Q-01).
- Риск смешения семантики: фича требует показывать именно предрасчёт
  (`commission_value`), а не `total_deals_commission`; путаница полей даёт неверную
  цифру на карточке.
- Форматирование значения (валюта/знак/округление) для чипа комиссии не
  подтверждено — есть `DecimalFormatter` и `CurrencyConverter`, но правило вывода
  для комиссии на активной карточке не задано (Q-03).
- Условные/стоп-заявки имеют несколько полей комиссии
  (`commission_value_stop_loss`, `commission_value_take_profit`) — нужен ли
  отдельный вывод для них, не определено (Q-04).

## Что учесть при написании фичи

- Целевые типы: `transaction_buy`, `transaction_sell`; целевые статусы:
  `in_progress`, `cancelling` — точка входа `TransactionChipsContentCustomizer`
  (`ACTIVE_STATUSES`, `getSupportedTypes`).
- Источник значения — `commission_value` из `GetDetailsResponse`
  (proto поле 65), а **не** `total_deals_commission` (поле 72).
- Место рендера — `chipsContent` (content feed-секции типа
  `history.feed.operationActive`); реализация `ChipsContent.enrich*` — добавляется
  новый `enrichWithCommission*`.
- Проброс в HO: убедиться, что `commission_value` из OG доходит до
  `SEND_OPERATIONS`/`GetDetailsResponse` для активных заявок (маппинг уже описан в
  `order-gateway.md:256`).
- Для BPH linked events — согласовать прекальку `precalc_commission` с
  источником (BPH) и её маппинг в HO (см. соседний паттерн
  `bph-linked-events-yield`).
- Возможен фича-тогл по аналогии с
  `enable_feed_cancellation_transaction_buy` / `..._sell`
  (`TransactionCancellationButtonCustomizer`).
- Формат вывода и подпись чипа (текст «Комиссия …», валюта, округление) —
  задать явно, использовать `DecimalFormatter`/`CurrencyConverter`.
- Соседние фичи `og-trading-order-yield` и `bph-linked-events-yield` — прецеденты
  согласования контракта между OG/BPH, HO и композитом.

### Актуализация после resolve (2026-09-12)

Решения из resolve, которые писатель и ревьюер должны считать актуальнее исходного current-state:

- GAP-GOAL-01: Административные сведения (инициатор): требуется ответ человека
- GAP-GOAL-02: Дата/версия постановки: требуется ответ человека
- GAP-GOAL-03: Продуктовая метрика/способ измерения: требуется ответ человека
- GAP-GOAL-04: Контракт BPH `precalc_commission`: требуется ответ человека
- GAP-GOAL-05: Целевое значение метрики: требуется ответ человека
- GAP-GOAL-06: Допущение заполненности `commission_value`: требуется подтверждение
- GAP-GOAL-07: Срок/релиз: требуется ответ человека
- GAP-GOAL-08: Поведение при пустом/нулевом прекальке: требуется ответ человека
- GAP-UCAS-01: Недоставка ленты (AS IS): требуется ответ человека
- GAP-UCAS-02: Минимальное содержимое `chipsContent`: требуется ответ человека
- GAP-UCAS-03: Версия/дата AS IS-снимка: требуется ответ человека
- GAP-UCAS-04: Точное имя операции запроса ленты в HO: требуется уточнение
- GAP-UCAS-05: Состав и порядок источников HO: требуется уточнение
- GAP-UCB-01: Заполненность `commission_value` (OG) для активных заявок: требуется подтверждение
- GAP-UCB-02: Поведение карточки при недоставке значения: требуется ответ человека
- GAP-UCB-03: Поведение при недоставке ленты (TO BE): требуется ответ человека
- GAP-UCB-04: Отображение при пустом/нулевом значении: требуется ответ человека
- GAP-UCB-05: Формат шильдика: требуется ответ человека
- GAP-UCB-06: Приоритет источников OG/BPH: требуется ответ человека
- GAP-UCB-07: Комиссия для условных/стоп-заявок: требуется ответ человека
- CH-03: —
- CH-06: —
- CH-13: —
- CH-15: —
- CH-21: —
- CH-26: —
- CH-30: —
- CH-07: —
- CH-08: —
- CH-12: B
- CH-14: —
- CH-17: —
- CH-18: —
- CH-19: —
- CH-22: —
- CH-23: —
- CH-24: —
- CH-28: —
- CH-29: —
- CH-01: PARTIAL

**Якоря полей из актуальной SPEC:**

`chipsContent`, `commission_value`, `precalc_commission`, `transaction_buy`, `transaction_sell`, `in_progress`, `cancelling`, `TransactionChipsContentCustomizer.java`, `total_deals_commission`, `history.feed.operationActive`, `TransactionChipsContentCustomizer`, `ChipsContent`

См. также § «Закрытые вопросы» ниже — не переспрашивать закрытые Q.
## Открытые вопросы / что проверить

| ID | Вопрос | Где искать ответ |
|---|---|---|
| Q-01 | Параметр `precalc_commission` (BPH linked events) отсутствует в репозиториях. Это новое поле источника BPH или переименование/маппинг существующего? Каким должен быть его контракт | `analytics/02-Modules/MOD-001-history-ops/integrations/bph.md`; `repositories/ИО/history-ops/src/main/java/.../service/conversion/` (`Bph*Converter`); proto `repositories/ИО/history-ops/src/main/proto/` |
| Q-02 | Заполнен ли `commission_value` для **активных** заявок (`in_progress`/`cancelling`) на момент ответа OG, или предрасчёт появляется только к моменту исполнения | `repositories/ИО/history-ops/src/test/resources/.../json/request/details/history-ops-request.json`; тесты `history-ops` по `commission_value`; `order-gateway.md` |
| Q-03 | Формат/подпись чипа комиссии: текст, валюта, знак, округление, позиция в `chipsContent` | `analytics/02-Modules/MOD-001-history-ops/` (feed/композит); макеты/Confluence; уточнить у аналитика |
| Q-04 | Нужен ли отдельный вывод комиссии для условных/стоп-заявок (`commission_value_stop_loss`, `commission_value_take_profit`) или только единый `commission_value` | `analytics/03-UseCases/UC-006-conditional-and-futures-orders.md`; `order-gateway.md` (поле 66–67 proto) |
| Q-05 | Требуется ли ограничение по инструменту/валютt (например, фьючерсы — `futuresTypes` в `AbstractTransactionOperationSectionCreator`) для показа комиссии | `.../AbstractTransactionOperationSectionCreator.java` (`futuresTypes`); `ChipsContent.resolvePostfix` |

## Закрытые вопросы

| ID | Дата | Решение | Где в spec | Источник |
|----|------|---------|------------|----------|
| Q-01 | 2026-09-12 | Контракт BPH `precalc_commission` — объект `tradeOrder.lead.precalc_commission: {value, currency}`, нормализуется в HO в `commission_value` (proto 65); если BPH не готов — релиз веткой OG + тогл BPH default OFF (D-01, D-05, D-11). Приоритет источников OG → BPH (D-05) | §1.1 CN-02; §1.3 шаг 3; §4.1.1.2; §4.2.3.2 | DECISIONS D-01/D-05; `/resolve-gaps` сессия 2 |
| Q-02 | 2026-09-12 | `commission_value` для активных заявок заполнен: активные заявки получаются через `GetTradeOrders`, `TradeOrder.commission_value` (proto 11) заполняется; `ActiveOrder` не используется (D-02) | §1.3 предусловие 4; §2 CN-03; §4.1.1.1 | DECISIONS D-02; `/resolve-gaps` сессия 2 |
| Q-03 | 2026-09-12 | Формат шильдика: `«Комиссия: 12,34 ₽»`, знак не выводится, округление 2 знака (`DecimalFormatter`), валюта `CurrencyConverter`, `key="commission"`, без `logoIcon`, элемент — последним в `params[]`; пустое/нулевое значение → шильдик скрывается целиком (D-03, D-04) | §1.3 шаги 7–8; §2 CN-12; §4.1.1.5; §4.2.3.1 | DECISIONS D-03/D-04; `/resolve-gaps` сессия 2 |
| Q-04 | 2026-09-12 | Отдельный вывод для условных/стоп-заявок не требуется: единый `commission_value` (proto 65) для всех заявок; поля 66–67 не выводятся (D-06) | §1.3 шаг 3; §2 CN-13; §4.1.1.3–4 | DECISIONS D-06; `/resolve-gaps` сессия 2 |
| Q-05 | 2026-09-12 | Ограничение по инструменту/валюте не вводится: формат через `CurrencyConverter`/`DecimalFormatter`; AS IS допущения подтверждены (D-04, D-11) | §4.1.1.5; §5.2 | DECISIONS D-04/D-11; `/resolve-gaps` сессия 2 |
| Q-06 | 2026-09-12 | Область действия D-09 (B) согласована (D-12 = C): D-09 (B) отменён в пользу D-03/D-07/D-08 — шильдик комиссии строго опционален, карточка всегда рендерится при наличии данных ленты; D-09 (B) применяется только к полной недоставке данных фида, когда карточку строить не из чего | §1.2 постусловие «Неуспех (техн.)», alt 2a; §1.3 постусловие «Неуспех (техн.)», alt 2a, «Обработка ошибок и недоставка данных»; §1.3.1 (11c); §4.2.3.6; §5.5 | DECISIONS D-12; `/resolve-gaps` сессия 4 (GAP-UCB-14) |

### Закрытия сессии `/resolve-challenges` (2026-09-12, CH-01…CH-35)

| ID | Дата | Решение | Где в spec | Источник |
|----|------|---------|------------|----------|
| Q-02 | 2026-09-12 | Ответ на CH-02 (неразличимость `hasField == false` и `0.0` в `optional double`) **не получен из источников**: поведение BPH-fallback [D-05] зависит от продуктового решения — строка `D-17` (`needs-answer`). Источник факта: `AbstractGrpcBuilderWrapper.enrichWithOptionalValue` (поле выставляется только при `value != null`), `DetailsResponseMapper.convertDouble` | §4.2.3.1; §4.1.1.2 (валидация) | DECISIONS D-17; `repositories/ИО/history-ops` (`AbstractGrpcBuilderWrapper`, `DetailsResponseMapper`) |
| Q-02 | 2026-09-12 | Заполненность `general_status` и типов секций уточнена по коду: маппинг OG → HO через `OrderGatewayOrderConverter.GENERAL_STATUS_MAP`; неизвестный статус OG → ошибка конвертации, заявка исключается из выборки; статус вне `ACTIVE_STATUSES` и вне терминальных → элемент не формируется (whitelist, fail-closed, уточнение BR-02) | §4.2.3.5 | `/resolve-challenges` (CH-29, CH-30); `OrderGrpcConverter.java`; `TransactionChipsContentCustomizer.java` |
| Q-03 | 2026-09-12 | Форматирование и конвертация уточнены по коду, вопрос закрыт: `"126.7"` → `BigDecimal` через `parseNullableDecimal` (`""` → `null`), нечисловая строка → `NumberFormatException` на OG-адаптере (заявка отсекается до HO); JSON → `double` через `convertDouble` (`DetailsResponseMapper.java:77`); формат `setScale(2, HALF_UP)` + `DecimalFormat("#,##0.##", ru_RU)`; валюта `CurrencyConverter.getCurrencyFrom`; ошибка форматирования → warn + `"—"` | §4.2.3.1; §1.3 шаг 8 | `/resolve-challenges` (CH-17, CH-18); `GrpcDecimalConverter.java`; `DetailsResponseMapper.java`; `DecimalFormatter.java`; `CurrencyConverter.java` |
| Q-04 | 2026-09-12 | Уточнение области условных/стоп-заявок: вне scope — только отдельные чипы полей 66/67 и фактические комиссии по сделкам; показ прекалька через единое поле 65 (proto) остаётся в scope [CN-13]/[D-06]; до активации значение отсутствует → шильдик скрыт по общему правилу [D-03]. Открытым остаётся факт заполненности поля 65 у условных до активации — `D-22`-соседний вопрос про расхождение источников и `D-11`-подобное подтверждение данных OG | §1.3.1 «Что не входит» | `/resolve-challenges` (CH-12, CH-11); `order-gateway.proto:82,106–109`; D-06, D-03 |
| Q-05 | 2026-09-12 | Rate limit / timeout / retry уточнены: фича не вводит новых значений; запросы батчируются на профиль (один `GetTradeOrders` на сборку ленты), число заявок не меняет число вызовов; timeout ограничен существующим HO→OG; retry — существующая политика | §4.1.1.1 | `/resolve-challenges` (CH-22); D-11 |
| Q-06 | 2026-09-12 | Наблюдаемость тогла и его применение закрыты: отсутствие тогла = OFF (`getOrDefault(name, false)`) → карточка без шильдика; гейт формирования элемента локализован в `TransactionChipsContentCustomizer.customize` (не в общем `ChipsContent.enrich`) — утечки на терминальные карточки нет; недоступность AUTH: ветка (а) обработки ответа → лента без шильдика, ветка (б) сетевой/статус ≠ OK → лента не отдаётся (AS IS); смена поведения ветки (б) — `D-24` (`needs-answer`) | §5.5; §5.3; §4.1.1.5 | `/resolve-challenges` (CH-13, CH-14, CH-19, CH-26, CH-27); `SessionService.getFeatureToggles`; `TransactionChipsContentCustomizer.java` |
| Q-01 | 2026-09-12 | Диаграмма TO BE приведена к фактическому маршруту: HO разрешает значение (OG — приоритет, BPH — fallback) и нормализует в `commission_value` (proto 65) до кэширования; композит читает `commission_value` из `GetDetailsResponse`. Диаграмма не является источником истины приёмки — источник истины SPEC. Нумерация шагов use case и alt-сценариев нормализована | §1.3.1 (caption + note, «Соответствие тексту»); §1.3 | `/resolve-challenges` (CH-24, CH-23, CH-21) |
| Q-02 | 2026-09-12 | Актуальность значения при дозагрузках ленты: прекальк может появиться/измениться между сборками → обновление на следующей сборке ленты, flicker допустим (источник истины — источник, не снапшот); признак «прекальк ещё не рассчитан» не вводится (такого состояния нет ни в proto 65, ни в UI); переход `in_progress` → терминальный между снапшотом и рендером: карточка отдаётся с типом секции `history.feed.operationActive`, шильдик `general_status` не перепроверяет — поведение HO AS IS, фичей не меняется. Приемлемость зафиксированного расхождения — `D-20` (`needs-answer`) | §4.2.3.7 (новый) | `/resolve-challenges` (CH-07, CH-08); D-03, D-12 |

### Повторный прогон `/resolve-challenges` (2026-09-12, CH-01…CH-35)

| ID | Дата | Решение | Где в spec | Источник |
|----|------|---------|------------|----------|
| Q-03 | 2026-09-12 | Округление/границы значения закрыты без правки SPEC: `DecimalFormatter` — `setScale(2, HALF_UP)` + `DecimalFormat("#,##0.##", ru_RU)`; `0.0` → шильдик скрыт, `0.004` → скрыт по правилу «≠ 0»; верхняя граница/санити-контроль значения не вводится (аудит показа не вводится [D-11]) | §4.2.3.1 (хоп 3); §4.2.3.6; §5.1 | `/resolve-challenges` повторно (CH-03 = COVERED/D-26; CH-06 = COVERED/D-27); `DecimalFormatter.java` |
| Q-06 | 2026-09-12 | Гейт формирования чипа подтверждён по коду: элемент формируется только в `TransactionChipsContentCustomizer.customize` для секции `history.feed.operationActive` при тогле ON; общий `ChipsContent.enrich` чип не добавляет — утечки на терминальные карточки нет | §4.1.1.5 («Гейт формирования элемента») | `/resolve-challenges` повторно (CH-26 = COVERED/D-31); `TransactionChipsContentCustomizer.java` |
| Q-02 | 2026-09-12 | Whitelist статусов подтверждён: `ACTIVE_STATUSES = {CANCELLING, IN_PROGRESS}`, fail-closed — новый/неожиданный `general_status` считается неактивным, элемент не формируется; отдельная обработка не требуется | §4.2.3.5 | `/resolve-challenges` повторно (CH-30 = COVERED/D-32); `TransactionChipsContentCustomizer.java` |
| Q-03 | 2026-09-12 | Конвертация значения подтверждена как нормативная (закрытие legacy-`answered`): `parseNullableDecimal` (пусто → `null`) → `BigDecimal`; нечисловая строка → `NumberFormatException` на OG-адаптере (заявка отсекается); JSON → `convertDouble`; формат `HALF_UP`; ошибка формата → warn + `"—"`. Подтверждение пользователем поведения — `D-14` (`needs-answer`) | §4.2.3.1; §1.3 шаг 8 | `/resolve-challenges` повторно (CH-17 = resolved/D-14, CH-18 = resolved); `GrpcDecimalConverter.java`, `DetailsResponseMapper.java` |
| Q-01 | 2026-09-12 | Требование письменной фиксации контракта BPH в SPEC нормативно (§4.1.1.2 «Фиксация контракта»); организационная форма фиксации — `D-15` (`needs-answer`) | §4.1.1.2 | `/resolve-challenges` повторно (CH-15; D-29/D-15) |
| Q-01 | 2026-09-12 | Нумерация §1.3 (шаги 6–10) признана нормативной; сводная таблица и «Соответствие тексту» приведены к ней; alt 5a/10a достижимы после нормализации; диаграмма TO BE приведена к фактическому маршруту и не является источником истины приёмки | §1.3; §1.3.1 («Соответствие тексту») | `/resolve-challenges` повторно (CH-23, CH-24 = resolved/D-33) |
| Q-04 | 2026-09-12 | §1.3.1 уточнён: вне scope — только чипы полей 66/67 и фактические комиссии; показ прекалька через поле 65 остаётся в scope (выбор B пользователя прошлого прогона) | §1.3.1 («Что не входит») | `/resolve-challenges` повторно (CH-12 = resolved) |
| Q-02 | 2026-09-12 | BR-01/CN-05 ограничивают показ шильдика, а не формирование карточки; формирование карточки — §1.2 BR-01/BR-02 | §1.1 BR-01/CN-05; §1.2; §1.3 | `/resolve-challenges` повторно (CH-28 = resolved/D-33) |
| Q-02 | 2026-09-12 | Маппинг OG `general_status` → HO через `OrderGatewayOrderConverter.GENERAL_STATUS_MAP`; неизвестный статус → ошибка конвертации, заявка исключается из выборки | §4.2.3.5 | `/resolve-challenges` повторно (CH-29 = resolved/D-33); `OrderGrpcConverter.java` |
| Q-06 | 2026-09-12 | Момент применения тогла — при сборке ленты/карточки; смена ON/OFF вступает в силу при следующей сборке (TTL снапшота); сбой `getSession`: ветка (а) → лента без шильдика, ветка (б) → лента не отдаётся (AS IS); смена ветки (б) — `D-24` | §5.5; §5.3 | `/resolve-challenges` повторно (CH-14, CH-19 = resolved/D-33); `SessionService.getFeatureToggles` |
| Q-05 | 2026-09-12 | Rate limit / timeout / retry фича не меняет; `GetTradeOrders` батчируется на профиль (один вызов на сборку ленты), число заявок не меняет число вызовов | §4.1.1.1; §5.2 | `/resolve-challenges` повторно (CH-22 = resolved/D-33) |
| Q-01 | 2026-09-12 | Измеримый критерий успеха — технические критерии (1)–(4) SMART (§1.1); продуктовая метрика — backlog [D-11]; чек-лист приёмки ветки ON — §1.1 SMART + §5.5 «Чек-лист верификации», входная точка включения — операционный трек [D-07] | §1.1 (SMART); §5.5 | `/resolve-challenges` повторно (CH-21 = COVERED/D-30; CH-13 = COVERED/D-28) |
| Q-05 | 2026-09-12 | **Открытые вопросы повторного прогона (нужны ответы пользователя, `needs-answer`):** валютный sanity-check `precalc_commission.currency` — `D-13` (CH-01); неразличимость OG `0.0` и отсутствия значения — `D-17` (CH-02); потребители `params[]` / совместимость старого фронта — `D-16` (CH-16); сбой `getSession` уровня (б) (лента не отдаётся вместо деградации) — `D-24` (CH-27); отрицательные значения (ребейт) — `D-18` (CH-04); порог показа — `D-19` (CH-05); статус `cancelling` — `D-21` (CH-09); заполненность поля 65 у условных до активации — `D-22` (CH-11); sanity-check валюты/инструмента BPH — `D-23` (CH-20); подтверждение поведения при нечисловой строке — `D-14` (CH-17); форма фиксации контракта BPH — `D-15` (CH-15) | SPEC до ответа не патчится (новых правок в этом прогоне не вносилось) | `/resolve-challenges` повторно; DECISIONS (D-13…D-25) |

### Применение решений `/resolve-challenges` (сессия 2, 2026-09-12, CH-01…CH-35)

Все 14 строк `pending-apply` (D-13…D-25) применены к SPEC; статусы банка обновлены — `open: 0`, `needs-answer: 0`. Запросов к человеку больше нет.

| ID | Дата | Решение | Где в spec | Источник |
|----|------|---------|------------|----------|
| Q-01 | 2026-09-12 | Валютный sanity-check BPH нормативен: `currency` отсутствует при непустом `value` или ≠ валюте инструмента → значение **отбрасывается**, шильдик не добавляется; валютный сигнал BPH к композиту не пробрасывается (proto 65 — `double` без валюты) — D-13 (CH-01) | §4.1.1.2 (таблица валидации) | DECISIONS D-13 (applied) |
| Q-01 | 2026-09-12 | Ограничение proto3 зафиксировано нормативно: OG `0.0` и «отсутствие» значения в `optional double` неразличимы, признак наличия HO не передаёт; BPH-fallback фактически срабатывает только при ненулевом значении OG; `0.0`/пусто → шильдик скрыт по [D-03] — D-17 (CH-02) | §4.1.1.2 (таблица валидации); §4.2.3.3 | DECISIONS D-17 (applied); `AbstractGrpcBuilderWrapper.enrichWithOptionalValue` |
| Q-06 | 2026-09-12 | Перечень потребителей `params[]` остаётся открытым риском (аналитика потребителей отсутствует, 0 совпадений); совместимость старой версии фронта с `key="commission"` проверяется тестом на стенде; требование «игнорировать неизвестные элементы» нормативно для всех потребителей — D-16 (CH-16) | §4.1.1.5 («Потребители элемента») | DECISIONS D-16 (applied) |
| Q-05 | 2026-09-12 | Сбой `getSession` уровня (б) (сеть/таймаут/статус ≠ OK) остаётся AS IS — лента/страница не отдаётся; переход к «лента без шильдика» не вводится; зафиксировано как унаследованное ограничение платформы, владелец риска SRE/`history_ops_screen_api`, верификация тестом — D-24 (CH-27) | §5.3 («Graceful Degradation», строки `getSession`) | DECISIONS D-24 (applied); `feature-toggles-catalog.md` |
| Q-04 | 2026-09-12 | Отрицательное значение (ребейт/корректировка) показывается **по модулю**; alt-сценарий «отрицательное трактуется как положительная комиссия» исправлен — D-18 (CH-04) | §1.3 alt 7a; §4.2.3.6 | DECISIONS D-18 (applied) |
| Q-04 | 2026-09-12 | Введён порог показа: значение < 0,01 после округления → шильдик скрыт (в дополнение к правилу «≠ 0») — D-19 (CH-05) | §4.2.3.6; §1.3 alt 7a | DECISIONS D-19 (applied) |
| Q-02 | 2026-09-12 | Статус `cancelling`: шильдик показывает значение, замороженное на момент старта отмены; пересчёт со стороны источников не выполняется, обновление — при следующей сборке ленты — D-21 (CH-09) | §4.2.3.5; §1.3 шаг 4 | DECISIONS D-21 (applied) |
| Q-02 | 2026-09-12 | Постулат для условных/стоп-заявок: до активации значение отсутствует → шильдик скрыт по [D-03]; fallback на поля 66/67 **не вводится** (согласовано с [D-06]) — D-22 (CH-11) | §4.2.3.5; §1.3 шаг 3 | DECISIONS D-22 (applied) |
| Q-01 | 2026-09-12 | Sanity-check на нормализации BPH нормативен: `currency` ≠ валюте инструмента или отсутствует → значение отбрасывается; значение иной валюты/инструмента не нормализуется в поле 65, при отсутствии валидного OG-значения шильдик скрыт — D-23 (CH-20) | §4.1.1.2; §4.2.3.2 | DECISIONS D-23 (applied) |
| Q-01 | 2026-09-12 | Контракт BPH `precalc_commission` (`{value, currency}`) фиксируется письменно **до** старта разработки BPH-ветки (аналог `bph-linked-events-yield`); до фиксации BPH-ветка поставляется с тоглом OFF (`enable_feed_precalc_commission`, default `false`) — D-15/D-29 (CH-15) | §4.1.1.2 («Фиксация контракта») | DECISIONS D-15, D-29 (applied) |
| Q-03 | 2026-09-12 | Поведение при нечисловой/неоднозначной строке подтверждено как нормативное: ошибка конвертации на стороне HO-адаптера, запись операции источника не формируется; распространяется на OG и BPH-ветку — D-14 (CH-17) | §4.1.1.2 (таблица валидации) | DECISIONS D-14 (applied); `GrpcDecimalConverter.parseNullableDecimal` |
| Q-05 | 2026-09-12 | Сводное решение D-25 (выбор B) закрыто без правки SPEC: вопросы CH-03…CH-35 закрываются индивидуальными решениями D-18…D-23; отдельное сводное решение не требуется | — (правка не требуется) | DECISIONS D-25 (applied) |

### Сессия 3 `/resolve-challenges` (2026-09-12, CH-36…CH-44)

Инкрементальный `challenge-feature` добавил 9 новых вопросов. Триаж: 5 RESOLVED (SPEC отредактирован), 4 NEEDS-ANSWER (SPEC не тронут).

| ID | Дата | Решение | Где в spec | Источник |
|----|------|---------|------------|----------|
| Q-02 | 2026-09-12 | Уровень отбраковки при нечисловом значении разведён: нечисловая строка (`"126,7"`, `"1 234,56"`, `"126.7 RUB"`) → `new BigDecimal` → `NumberFormatException` на адаптере HO OG/BPH → **запись операции источника не формируется** (операция отсекается до композита, карточка не строится) — отдельный случай alt 3a.4; «штатное отсутствие значения» (поле не задано/пустая строка) — только чип исчезает, карточка сохраняется | §1.3 alt 3a (пп. 3a.1, 3a.4); §4.2.3.1 (хоп 1/шаг 2) | DECISIONS D-14/D-38; `/resolve-challenges` сессия 3 (CH-38); `DetailsResponseMapper.java:77` + `convertDouble`; `GrpcDecimalConverter.parseNullableDecimal` |
| Q-05 | 2026-09-12 | BPH-fallback нормативно активируется только при **ненулевом** значении OG; для OG `0.0`/пусто не срабатывает (proto3 `optional double` неразличим: `0.0` и отсутствие читаются одинаково, [CN-14]/[D-17]) → чип скрыт по [D-03]; BPH-ветка работает только для заявок **вне OG**. §4.2.3.3 и §4.2.3.6 синхронизированы | §4.2.3.3 (BPH-строка); §4.2.3.6 (строка 4) | DECISIONS D-17/D-38; `/resolve-challenges` сессия 3 (CH-41); `AbstractGrpcBuilderWrapper.enrichWithOptionalValue` |
| Q-02 | 2026-09-12 | Для `cancelling` значение «заморожено на момент старта отмены» = значение из снапшота ленты, пересчёта у источника нет, обновление при следующей сборке ленты [D-21]. Дописано в §4.2.3.5 (строка `CANCELLING`) и §1.3 шаг 4 со ссылкой на §4.2.3.7 | §4.2.3.5 (строка `CANCELLING`); §1.3 шаг 4 | DECISIONS D-21/D-38; `/resolve-challenges` сессия 3 (CH-42) |
| Q-06 | 2026-09-12 | Дублирование строк `getSession` в §5.3 устранено: две строки объединены в одну. Нормативна AS IS ветка **(б)** — сетевой/таймаут-сбой или статус ≠ `OK` → client error, лента не продолжается; ветка (а) — частный случай деградации (исключение в `SessionService` → пустая карта тоглов → чип скрыт, лента продолжается); «лента без шильдика» для (б) не вводится; владелец риска — SRE/`history_ops_screen_api` | §5.3 (Graceful Degradation) | DECISIONS D-24/D-38; `/resolve-challenges` сессия 3 (CH-43); `SessionService.getFeatureToggles`; `feature-toggles-catalog.md` |
| Q-06 | 2026-09-12 | Чек-лист §5.5 дополнен моментом проверки тогла: ON↔OFF проверяется **после перезагрузки ленты / истечения TTL снапшота** (§5.2.7); расхождение в пределах неистёкшего TTL (старый чип при ON→OFF, отсутствие при OFF→ON) — ожидаемое поведение кэша, а не провал приёмки | §5.5 (чек-лист верификации + «Момент применения тогла») | DECISIONS D-38; `/resolve-challenges` сессия 3 (CH-44); §5.2.7 |
| Q-01 | 2026-09-12 | **Открытые вопросы сессии 3 (нужны ответы пользователя, `needs-answer`):** порядок «модуль / округление / порог `< 0,01`» — `D-34` (CH-36); достижимость/нормативность ветки `"—"` при ошибке конвертации валюты — `D-35` (CH-37); нормативная ветка при пересечении условия показа (шаг 7 vs alt 7a) — `D-36` (CH-39); нормативный якорь «валюта инструмента» для sanity-check — `D-37` (CH-40). SPEC по этим пунктам **не тронут** | SPEC до ответа не патчится | DECISIONS (D-34…D-37); `/resolve-challenges` сессия 3 |

### Сессия 3 `/resolve-challenges` — применение решений D-34…D-37 (2026-09-12)

Пользователь ответил на 4 вопроса (`needs-answer` D-34…D-37, все — **выбор A**); строки применены к SPEC, статусы банка → `resolved`. Банк: **open 0 · resolved 31 · covered 6 · deferred 7**; `pending-apply` — 0, `needs-answer` — 0.

| ID | Дата | Решение | Где в spec | Источник |
|----|------|---------|------------|----------|
| Q-04 | 2026-09-12 | Порядок нормативен: «взять модуль `\|v\|` → округлить `HALF_UP` до 2 знаков → сравнить с `0,01`». В §4.2.3.6 внесены обе нормативные строки («Порог» `< 0,01` → скрыт; «Модуль» — отрицательное показывается по модулю). Кейсы: `0.004`→`0.00`→скрыт; `-0.005`→`0.01`→«Комиссия: 0,01 ₽»; `-0.00`→`0.00`→скрыт | §4.2.3.6 (норм. порядок + строки Порог/Модуль + таблица кейсов) | DECISIONS D-34 (applied); `/resolve-challenges` сессия 3 apply (CH-36); [D-18], [D-19] |
| Q-03 | 2026-09-12 | Ветка «ошибка конвертации валюты → warn + `"—"`» **удалена** из §4.2.3.1: при невозможности получить валюту чип **скрывается** по §4.2.3.6 (нечисловой текст «—» не выводится). Реальные исходы `CurrencyConverter.getCurrencyFrom`: `!hasCurrency()` → `""`; `IllegalArgumentException` (`Currency.getInstance`) → `warn` + empty `Optional` → `orElseGet(operation::getCurrency)` → сырой код. Желаемый UX валюты-заглушки заведён гэпом `GAP-CHAINS-01` | §4.2.3.1 (хоп 3 + нормативные следствия); §4.2.3.3 («Гэпы цепочки 2») | DECISIONS D-35 (applied); `/resolve-challenges` сессия 3 apply (CH-37); `CurrencyConverter.java:19–29` |
| Q-04 | 2026-09-12 | Единое условие показа: §1.3 шаг 7 переписан через нормализованное значение — `показать ⇔ тогл ON ∧ значение присутствует ∧ \|v\| ≥ 0,01 ∧ v ≠ 0` (после округления `HALF_UP`); alt 7a — иначе; порядок операций — из D-34. Противоречия с §4.2.3.6 нет | §1.3 шаг 7 / alt 7a; §4.2.3.1 (`chipsContent.params[]`) | DECISIONS D-36 (applied); `/resolve-challenges` сессия 3 apply (CH-39); D-34 |
| Q-01 | 2026-09-12 | Введён нормативный якорь валюты инструмента: поле `currency` (proto `optional string currency = 23`) в HO-модели деталей операции — носитель `ReportOrderOperationDetails.currency` (`history.yml` — `currency: type: string`); единая точка получения — `GetDetailsResponse.getCurrency()`, согласована с валютой форматирования чипа (§4.2.3.1 хоп 3, [CN-12]); расхождение → значение отбрасывается [D-13]. Поле существует — гэп не заводится (требование якоря закрыто выбором A) | §4.2.3.2 (новая таблица «Нормативный якорь валюты инструмента»); §4.2.3.1 (следствие 3) | DECISIONS D-37 (applied); `/resolve-challenges` сессия 3 apply (CH-40); `history.yml:338`; `historyOperationDetails.proto:89`; `DetailsResponseMapper` |
| — | 2026-09-12 | **Вопросов к человеку после сессии 3 (apply) — 0**; `open` в банке — 0; `pending-apply` — 0 | — | DECISIONS D-34…D-37 (applied) |
| Q-03 | 2026-09-12 | UX валюты-заглушки закрыт (последний открытый `GAP-CHAINS-01`): разветвление исходов `CurrencyConverter.getCurrencyFrom` — (а) `!hasCurrency()` → `""` → элемент в `params[]` **не добавляется**, чип **скрыт целиком**, подстановка `₽`/прочерка/дефолтной валюты не выполняется; (б) `IllegalArgumentException` → `warn` → сырой код валюты → чип **показывается** со значением и сырым кодом как есть (например, «Комиссия: 12,50 RUR»), символ валюты не подставляется. Блок «Гэпы цепочки 2» удалён из §4.2.3.3 | §4.2.3.1 (хоп 3 + нормативные следствия); §4.2.3.3; §4.2.3.6; §1.3 шаг 8 + alt 8a; §4.1.1.5; §2 CN-12 | DECISIONS D-39 (applied); `/resolve-gaps` сессия 5; `CurrencyConverter.java:19–29`; `DecimalFormatter.java` |
| — | 2026-09-12 | **Вопросов к человеку после сессии 5 (`/resolve-gaps`) — 0**; открытых `[GAP-` в SPEC — 0; `pending-apply` — 0; `needs-answer` — 0 | — | DECISIONS D-39 (applied) |

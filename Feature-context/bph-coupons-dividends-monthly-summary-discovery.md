# INTERNAL: discovery-пакет контекста фичи (не отдавать как есть)

## Бриф
Новая ручка BPH для суммирования купонов и дивидендов за месяц, параллельный source-запрос в history-ops, композит BDUI history-ops-screen-api, новая секция на экране ленты, карточка инструмента, coupons dividends corporate actions GetLinkedEvents

## Поисковые термины (вес = приоритет)
`bdui`(×3), `bph`(×3), `getlinkedevents`(×3), `events`(×2), `get`(×2), `linked`(×2), `actions`(×1), `api`(×1), `corporate`(×1), `coupons`(×1), `dividends`(×1), `history`(×1), `ops`(×1), `screen`(×1), `source`(×1), `дивидендов`(×1), `запрос`(×1), `инструмента`(×1), `карточка`(×1), `композит`(×1), `купонов`(×1), `ленты`(×1), `месяц`(×1), `новая`(×1), `параллельный`(×1)

Области поиска: аналитика `analytics/`, спецификации `Feature-writing/`, код `repositories/`, данные `db-export/`, доп. материалы `auxiliary/`.

## Кандидаты (ранжированы по score)

## Фокус поиска

Тип фичи: `general`.
Сначала открой: `*.proto` и RPC, если есть в выдаче; DDL / liquibase, если есть в выдаче.
Обязательные якоря в CONTEXT_DOC: контракт: service / rpc / message, данные: таблица / колонка.
Мало якорей в выдаче → перезапусти с `--terms "proto rpc grpc"` и доменными именами сервисов/полей.
Нет файла с якорем → `Q-XX`, не выдумывай контракт или схему.

### Спецификации фич (Feature-writing/)

| Файл | Score | Совпавшие термины | Фрагмент |
|---|---|---|---|
| `Feature-writing/bph-linked-events-yield/bph-linked-events-yield.md` | 507 | `bph`, `linked`, `getlinkedevents`, `events`, `get`, `bdui` | \| Команда `history-ops-screen-api` (BDUI) \| Владелец экранного сервиса \| Учесть доходность в композите экрана \| Формирует экран из данных `history-ops` \| |
| `Feature-writing/og-trading-order-yield/og-trading-order-yield.md` | 348 | `bph`, `get`, `linked`, `bdui`, `events`, `запрос` | \| Команда `history-ops-screen-api` (BDUI) \| Владелец экранного сервиса \| Учесть доходность в композите экрана \| Формирует экран из данных `history-ops` \| |
| `Feature-writing/bph-portfolio-size-tax/bph-portfolio-size-tax.md` | 279 | `bph`, `get`, `запрос`, `ops`, `history`, `новая` | \| CN-02 \| Архитектурное \| МП и композит BDUI не изменяются — тот же `operation_type=tax`, та же деталка `HISTORY_OPS_TAX_DETAILS_SCREEN` \| Контекст: `History... |
| `Feature-writing/bph-moex-tax/bph-moex-tax.md` | 218 | `bph`, `запрос`, `ops`, `history`, `get`, `новая` | \| CN-02 \| Ограничение \| МП и композит BDUI не изменяются — уже запрашивают `operationTypes: tax` \| Контекст-документ \| |
| `Feature-writing/bph-portfolio-size-tax/bph-portfolio-size-tax-code-alignment.md` | 148 | `bph`, `get`, `history`, `ops`, `api`, `source` | slug: bph-portfolio-size-tax |
| `Feature-writing/bph-moex-tax/bph-moex-tax-code-alignment.md` | 133 | `bph`, `get`, `history`, `bdui`, `source`, `ops` | \| B-06 \| §2 NG-02 \| Mobile / BDUI unchanged; tax detail screen exists \| `HistoryOperationTaxDetailsHeaderSection.java:30` — `defaultTitleName("Удержание нало... |
| `Feature-writing/bph-portfolio-size-tax/bph-portfolio-size-tax-challenges.md` | 122 | `bph`, `history`, `запрос`, `get`, `bdui`, `ленты` | \| CH-17 \| CN-02, CN-03, §1.3 \| CN-02/CN-03 фиксируют «МП и композит BDUI не изменяются», «тот же `type=tax`, та же деталка `HISTORY_OPS_TAX_DETAILS_SCREEN`».... |
| `Feature-writing/og-trading-order-yield/og-trading-order-yield-code-alignment.md` | 110 | `bph`, `get`, `history`, `bdui`, `linked`, `ops` | 4. BDUI формат «N %» (SIHIST-3373) — проверить при наличии `history-ops-screen-api` в workspace. |
| `Feature-writing/og-trading-order-yield/og-trading-order-yield-challenges.md` | 106 | `bph`, `linked`, `history`, `events`, `get`, `screen` | \| CH-01 \| §1.1 BR-05, §1.3 alt 4a \| ОГ и BPH **оба** возвращают `yield`, но значения **различаются** (value или currency). BR-05 задаёт приоритет только при ... |
| `Feature-writing/bph-portfolio-size-tax/bph-portfolio-size-tax-code-alignment-resolved.md` | 100 | `bph`, `source` | slug: bph-portfolio-size-tax |
| `Feature-writing/bph-portfolio-size-tax/bph-portfolio-size-tax-challenges-resolved.md` | 85 | `bph`, `запрос`, `ленты`, `source` | slug: bph-portfolio-size-tax |
| `Feature-writing/bph-portfolio-size-tax/bph-portfolio-size-tax-gaps-resolved.md` | 81 | `bph`, `get`, `history`, `source` | slug: bph-portfolio-size-tax |
| `Feature-writing/og-trading-order-yield/og-trading-order-yield-challenges-resolved.md` | 35 | `bph`, `history`, `bdui`, `ops`, `linked`, `events` | \| CH-24 \| MISSING → resolved \| a \| BDUI формат «N %» как value_per_instrument_item_pcnt \| §1.3 шаг 6 \| SIHIST-3373 \| |
| `Feature-writing/og-trading-order-yield/og-trading-order-yield-gaps-resolved.md` | 14 | `get`, `bph`, `bdui`, `history`, `запрос`, `source` | \| GAP-UCTB-03 / Q-10 \| a \| BDUI: деталка торговой заявки SIHIST-3373, рядом с облигационными полями \| §1.3 шаг 6 \| |

### Аналитика (analytics/)

| Файл | Score | Совпавшие термины | Фрагмент |
|---|---|---|---|
| `analytics/02-Modules/MOD-001-history-ops/integrations/bph.md` | 293 | `bph`, `linked`, `get`, `events`, `ops`, `history` | # Интеграция history-ops с BPH |
| `analytics/02-Modules/MOD-001-history-ops/behavior/feed-orchestration.md` | 221 | `bph`, `get`, `history`, `ops`, `запрос`, `source` | \| Дедупликация и merge ответов \| Детали маппинга BC↔BPH (bph-response-processing) \| |
| `analytics/02-Modules/MOD-001-history-ops/behavior/bph-response-processing.md` | 199 | `bph`, `get`, `history`, `ops`, `запрос`, `linked` | # Обработка ответов BC и BPH (DB-aware mapping) |
| `analytics/02-Modules/MOD-001-history-ops/integrations/corp-actions.md` | 196 | `bph`, `get`, `history`, `ops`, `actions`, `corporate` | 2. **BPH типовые КД** — операции из **GET_OPERATIONS_WITH_DETAILS** по маппингу БД HO (3131): погашения, выплаты по паям, ликвидация, depo_transfer. |
| `analytics/02-Modules/MOD-001-history-ops/integrations/bc.md` | 193 | `bph`, `get`, `history`, `ops`, `запрос`, `api` | **BC** (Brokerage Controller, Brokerage Controller AS) — исторический мастер-источник брокерских операций. **history-ops** обращался к BC за торговыми заявка... |
| `analytics/02-Modules/MOD-001-history-ops/behavior/operation-type-catalog.md` | 182 | `bph`, `get`, `history`, `ops`, `api`, `source` | Поведение **history-ops** для маппинга типов операций МП ↔ BPH/BC/OG: торговые **фьючерсы**, **вариационная маржа**, **удержание налогов** и отчёт о **недост... |
| `analytics/02-Modules/MOD-001-history-ops/api/grpc-to-screen-api.md` | 153 | `api`, `screen`, `history`, `get`, `ops`, `композит` | \| operations_details[].itemtype \| string \| [1-1] \| Источник (OG, BPH, BC, …) \| |
| `analytics/02-Modules/MOD-002-history-ops-screen-api/behavior/composite-feed-backend.md` | 152 | `get`, `history`, `screen`, `api`, `ops`, `композит` | Backend-процесс **history-ops-screen-api**: принимает REST **GET_OPERATIONS_FEED**, запрашивает операции у **history-ops** (gRPC GET_OPERATIONS), получает **... |
| `analytics/02-Modules/MOD-001-history-ops/integrations/order-gateway.md` | 144 | `get`, `bph`, `history`, `ops`, `запрос`, `linked` | **order-gateway (OG)** — сервис торговых заявок и сделок в АС СберИнвестор 2. **history-ops** запрашивает у OG актуальные торговые операции (`transaction_buy... |
| `analytics/02-Modules/MOD-001-history-ops/integrations/feature-toggle.md` | 143 | `get`, `ops`, `history`, `bph`, `actions`, `linked` | \| enableServiceBPH \| Вызов BPH \| |
| `analytics/02-Modules/MOD-001-history-ops/behavior/instrument-enrichment.md` | 139 | `bph`, `ops`, `инструмента`, `get`, `history`, `запрос` | Plan-cluster **C026** (991, 1332, 1370, 882, 3754, 2048): ключи match, minStep, ISIN expansion, parallel DG orchestration, BPH coupon/dividend instrument blo... |
| `analytics/02-Modules/MOD-001-history-ops/integrations/dictionary-gateway.md` | 135 | `get`, `bph`, `инструмента`, `ops`, `history`, `запрос` | - формирования `instrument_filter` в запросах к OG, BPH, DCA, DCM, ECM. |
| `analytics/02-Modules/MOD-002-history-ops-screen-api/api/get-operations-feed.md` | 135 | `api`, `get`, `screen`, `history`, `ops`, `запрос` | REST-эндпоинт **history-ops-screen-api** (композит) принимает запрос от МП/web на формирование экрана «История операций». Screen-api авторизует клиента, прео... |
| `analytics/02-Modules/MOD-002-history-ops-screen-api/README.md` | 133 | `api`, `ops`, `history`, `get`, `screen`, `композит` | \| Формирование JSON секций для UI \| Запросы в BPH, BC, OG, DG, AG \| |
| `analytics/02-Modules/MOD-001-history-ops/data/bc-bph-mapping-db.md` | 130 | `bph`, `ops`, `history`, `get`, `source`, `запрос` | # BC↔BPH mapping — PostgreSQL schema |

### Код и контракты (repositories/)

| Файл | Score | Совпавшие термины | Фрагмент |
|---|---|---|---|
| `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/adapter/bph/linked_events/converter/BphLinkedEventsConverterForTrades.java` | 326 | `bph`, `linked`, `events`, `get`, `ops`, `history` | package com.sberbank.si20.history.ops.adapter.bph.linked_events.converter; |
| `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/adapter/bph/linked_events/BphLinkedOperationsGateway.java` | 320 | `bph`, `linked`, `events`, `ops`, `history`, `get` | package com.sberbank.si20.history.ops.adapter.bph.linked_events; |
| `repositories/ИО/history-ops/src/test/java/com/sberbank/si20/history/ops/service/HistoryOpsGrpcServiceTest.java` | 317 | `bph`, `get`, `ops`, `history`, `source`, `linked` | mockBphGateway("com/sberbank/si20/history/ops/json/response/feed/bph/bph-response.json"); |
| `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/service/conversion/operation/creator/BphLinkedTradeOperationCreator.java` | 310 | `bph`, `linked`, `get`, `ops`, `history`, `api` | import com.sberbank.si20.history.ops.adapter.bph.enums.CurrencyEnum; |
| `repositories/ИО/history-ops/src/test/java/com/sberbank/si20/history/ops/IntegrationTestPath.java` | 307 | `bph`, `linked`, `get`, `ops`, `history`, `screen` | BPH_INSTRUMENT( |
| `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/adapter/bph/linked_events/converter/BphLinkedTradeOrderBaseConverterForTrades.java` | 306 | `bph`, `linked`, `get`, `events`, `ops`, `history` | package com.sberbank.si20.history.ops.adapter.bph.linked_events.converter; |
| `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/service/InstrumentService.java` | 306 | `bph`, `linked`, `get`, `events`, `ops`, `history` | import com.sberbank.si20.history.ops.adapter.bph.BphOperationWrapper; |
| `repositories/ИО/history-ops/src/test/java/com/sberbank/si20/history/ops/HistoryOpsFeedScreenTest.java` | 304 | `bph`, `linked`, `screen`, `ops`, `history`, `source` | import static com.sberbank.si20.history.ops.IntegrationTestPath.BPH_COMMON_COMMISSIONS; |
| `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/adapter/bph/linked_events/converter/BphLinkedEventsConverterForCommissions.java` | 295 | `bph`, `linked`, `events`, `get`, `ops`, `history` | package com.sberbank.si20.history.ops.adapter.bph.linked_events.converter; |
| `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/adapter/bph/linked_events/converter/BphLinkedTradeOrderConverterForCommissions.java` | 293 | `bph`, `linked`, `get`, `events`, `ops`, `history` | package com.sberbank.si20.history.ops.adapter.bph.linked_events.converter; |
| `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/service/conversion/operation/BphLinkedCommissionsListBuilder.java` | 292 | `bph`, `linked`, `get`, `history`, `ops`, `events` | import com.sberbank.si20.history.ops.adapter.bph.BphDynamicConfig; |
| `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/service/conversion/operation/merger/OperationMerger.java` | 291 | `bph`, `linked`, `ops`, `history`, `events`, `actions` | import com.sberbank.si20.history.ops.adapter.bph.BphDynamicConfig; |
| `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/service/conversion/operation/creator/OgTradeOperationCreator.java` | 279 | `bph`, `linked`, `get`, `ops`, `history`, `events` | import com.sberbank.si20.history.ops.adapter.bph.linked_events.wrapper.BphLinkedCommissionWrapper; |
| `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/service/operation/SourceOperationService.java` | 269 | `bph`, `get`, `ops`, `history`, `linked`, `actions` | import com.sberbank.si20.history.ops.adapter.bph.BphDynamicConfig; |
| `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/adapter/bph/linked_events/converter/BphLinkedDealConverterForTrades.java` | 261 | `bph`, `linked`, `get`, `events`, `ops`, `history` | package com.sberbank.si20.history.ops.adapter.bph.linked_events.converter; |
| `repositories/ИО/history-ops/src/test/java/com/sberbank/si20/history/ops/HistoryOpsFeedScreenWithIgniteTest.java` | 244 | `bph`, `get`, `ops`, `history`, `screen`, `source` | import static com.sberbank.si20.history.ops.IntegrationTestPath.BPH_FEED; |
| `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/service/conversion/operation/merger/OrderMerger.java` | 243 | `bph`, `linked`, `get`, `history`, `ops`, `actions` | import com.sberbank.si20.history.ops.adapter.bph.BphDynamicConfig; |
| `repositories/ИО/history-ops/src/test/java/com/sberbank/si20/history/ops/OriginalInstrumentWithItsVersionsRequestsConfigMapTest.java` | 234 | `bph`, `get`, `history`, `ops`, `corporate`, `linked` | "app-config-dynamic.instrument-filter-requests-dynamic.bphGetLinkedEvents.active=false", |
| `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/service/conversion/BphOrdersAndDealsProcessor.java` | 230 | `bph`, `get`, `linked`, `ops`, `history`, `events` | import com.sberbank.si20.history.ops.adapter.bph.linked_events.wrapper.BphLinkedCommissionWrapper; |
| `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/service/conversion/operation/merger/TradeMerger.java` | 230 | `bph`, `get`, `ops`, `history`, `linked`, `api` | import com.sberbank.si20.history.ops.adapter.bph.linked_events.converter.ErrorCollector; |
| `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/service/conversion/BphCommonClientConverter.java` | 225 | `bph`, `get`, `history`, `ops`, `api`, `source` | import com.sberbank.si20.history.ops.adapter.bph.common.BphCommonWrapper; |
| `repositories/ИО/history-ops/src/test/resources/com/sberbank/si20/history/ops/txt/feed-screen/expected_integration_log_feed_screen_v3_futures.txt` | 225 | `bph`, `get`, `history`, `api`, `ops`, `дивидендов` | {"timestamp":"test-ts","level":"INFO","message":"Integration log entry","logger":"IntegrationLogger","system":"SI","callid":"request-id-1","duration":"-","ex... |
| `repositories/ИО/history-ops/src/test/resources/application-test.yml` | 219 | `bph`, `get`, `history`, `ops`, `linked`, `source` | bph-dynamic: |
| `repositories/ИО/history-ops/src/test/resources/com/sberbank/si20/history/ops/txt/instrument-screen/expected_integration_log_new_instrument_filter_by_isin.txt` | 218 | `bph`, `get`, `history`, `ops`, `дивидендов`, `source` | {"timestamp":"test-ts","level":"INFO","message":"Integration log entry","logger":"IntegrationLogger","system":"SI","callid":"request-id-1","duration":"-","ex... |
| `repositories/ИО/history-ops/src/test/resources/com/sberbank/si20/history/ops/txt/instrument-screen/expected_integration_log_new_instrument_filter_by_ticker.txt` | 217 | `bph`, `get`, `history`, `ops`, `дивидендов`, `source` | {"timestamp":"test-ts","level":"INFO","message":"Integration log entry","logger":"IntegrationLogger","system":"SI","callid":"request-id-1","duration":"-","ex... |

### Данные (db-export/)

| Файл | Score | Совпавшие термины | Фрагмент |
|---|---|---|---|
| `db-export/БД ИО.md` | 365 | `bph`, `get`, `секция`, `купонов`, `дивидендов`, `screen` | \| history-ops \| bph                      \| 24   \| id, subtype, type_id, is_active                                                                            ... |

### Доп. материалы (auxiliary/)

Совпадений в auxiliary не найдено.

## Инструкция для агента
1. Сначала открой файлы из § «Фокус поиска», затем топ по score. При необходимости расширь поиск Grep по тем же терминам и якорям фокуса.
2. Не подтверждай факты по одному имени файла — открой файл и проверь содержимое (класс, метод, endpoint, proto-сообщение, таблицу, поле).
3. `analytics/` — актуальная аналитика и выгрузка Confluence по фичам: используй для бизнес-контекста, AS IS / TO BE, требований. Технические факты (контракты, поля, код) подтверждай по `repositories/` и `db-export/`.
4. Заполни **Скелет документа-контекста** ниже: для каждого факта дай ссылку на конкретный файл (и якорь: класс/метод/таблица/endpoint).
5. Неизвестное и непроверенное помечай в разделе «Открытые вопросы», не выдумывай поведение.
6. Это контекст для будущего написания фичи, а не сама фича: не проектируй решение, опиши то, что уже есть и что нужно учесть.
7. В финальном документе не оставляй «INTERNAL», score-таблиц и этой инструкции.

## Скелет документа-контекста (заполни и верни)

# Контекст для фичи: bph-coupons-dividends-monthly-summary

## Задача (бриф)

> Кратко перескажи бриф своими словами: что меняем и зачем.

## Затронутые области

| Область | Что затрагивается | Документы / код |
|---|---|---|
| | | |

## Релевантная аналитика и спеки

| Документ (analytics/, Feature-writing/) | Что описывает | Почему релевантно задаче |
|---|---|---|
| | | |

## Релевантный код

| Файл | Компонент (класс / метод / endpoint / proto) | Текущее поведение | Почему важно для фичи |
|---|---|---|---|
| | | | |

## Данные (БД, выгрузки)

| Таблица / поле / запрос | Где найдено | Текущее устройство | На что влияет фича |
|---|---|---|---|
| | | | |

## Интеграции и контракты, которые нужно учесть

- 

## Ограничения и риски текущего состояния

- 

## Что учесть при написании фичи

- 

## Открытые вопросы / что проверить

| ID | Вопрос | Где искать ответ |
|---|---|---|
| Q-01 | | |

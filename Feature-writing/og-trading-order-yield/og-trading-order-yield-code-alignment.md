---
report_type: code-alignment
slug: og-trading-order-yield
source_document: Feature-writing/og-trading-order-yield/og-trading-order-yield.md
generated_at: 2026-08-28
alignment_iteration: 3
scope: repositories/ only
language: ru
verdict: PASS WITH GAPS
---

# Отчёт о соответствии коду: og-trading-order-yield

**Документ:** `Feature-writing/og-trading-order-yield/og-trading-order-yield.md`  
**Отчёт:** `Feature-writing/og-trading-order-yield/og-trading-order-yield-code-alignment.md`  
**Область проверки:** только код в `repositories/`  
**Итерация:** 3 / 3

## Сводка

- CONFIRMED: 32 · MISMATCH: 0 · PARTIAL: 1 · NOT FOUND: 8 · UNVERIFIABLE: 3
- **Вердикт:** PASS WITH GAPS

Major MISMATCH **нет**. Spec после `/resolve-gaps` и `/resolve-challenges` согласован с AS IS кодом. NOT FOUND — ожидаемые TO BE (поле `yield`, маппинг в `HistoryOperationLead`, BR-05 enrichment, unit-тесты). PARTIAL: инфраструктура `TradeOperationCreationContext.bphOrderEnrichDto` есть, но в OG-path не подключена.

## Приоритетные находки

Пользователь указал `@Feature-context/og-trading-order-yield.md` — проверен slug `og-trading-order-yield` по актуальной spec. Контекст-док подтверждает якоря; расхождений с обновлённой spec (HistoryOperationLead, BR-05) нет — контекст устарел по уровню поля, spec — источник TO BE.

## Находки по категориям

### Контракты

| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|----|------------------|-------------|----------------------|--------|-------------|
| C-01 | §4.1.1 | `OrdersService.GetTradeOrders` | `order-gateway.proto:13–14` | CONFIRMED | Info |
| C-02 | §4.1.1 AS IS | `TradeOrder` поля 1–41; доходности нет | `order-gateway.proto:71–112`, последнее `card_number = 41` | CONFIRMED | Info |
| C-03 | §4.1.1 | `GetTradeOrdersResponse.orders` | `order-gateway.proto:59–61` | CONFIRMED | Info |
| C-04 | §4.1.1 | Decimal → `google.type.Decimal` | `order-gateway.proto:9, 79–112` | CONFIRMED | Info |
| C-05 | §4.1.1 TO BE | `TradeOrder.yield` / `YieldData` | Поле отсутствует в proto; grep `yield` в `history-ops` — 0 | NOT FOUND | Major (TO BE) |
| C-06 | §4.1.1.1 AS IS | `ReportOrderOperationDetails` — bond-поля без yield | `history.yml:376–455`; `OgTradeOperationCreator.java:198–232` | CONFIRMED | Info |
| C-07 | §4.1.1.1 TO BE | `HistoryOperationLead.yield` inline object | `history.yml:456–505` — свойства `yield` нет | NOT FOUND | Major (TO BE) |
| C-08 | §4.1.1.1 | `required`: orderType, deals, agreementNumber | `history.yml:380–383` | CONFIRMED | Info |
| C-09 | §4.1.1 | Пример ответа с `yield` — TO BE | AS IS proto без yield; пример помечен «после добавления поля» | CONFIRMED | Info |
| C-10 | §4.1.1 | Upstream field number — ожидание после 41 | `order-gateway.proto:112`; upstream `trade-operations-commons` вне workspace | UNVERIFIABLE | Minor |

### БД и миграции

| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|----|------------------|-------------|----------------------|--------|-------------|
| D-01 | §2, §4.2.3, CN-09 | Доходность транзитная; колонки в БД нет | `db-export/БД ИО.md`; grep yield в repo — 0 | CONFIRMED | Info |
| D-02 | §4.2.3 | DDL не требуется | Нет миграций/changeset с yield | CONFIRMED | Info |
| D-03 | §2 CN-09 | Ignite: yield как часть `HistoryOperationBase` | `OperationsIgniteProxyService.java:267–268` — кэшируется `operation.getLead()` целиком | CONFIRMED | Info |

### Интеграции

| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|----|------------------|-------------|----------------------|--------|-------------|
| I-01 | §4.1.1 | `exSystem="OG"`, `eventType="GET_TRADE_ORDERS"` | `OrderGrpcGateway.java:82–88` | CONFIRMED | Info |
| I-02 | §1.2 | Триггер `transaction_buy` / `transaction_sell` | `OrderGrpcGateway.java:45–48` | CONFIRMED | Info |
| I-03 | §4.1.1 | `limit` ← `maxRecords` | `OrderGatewayOrderConverter.java:86` | CONFIRMED | Info |
| I-04 | §4.1.1 | `order_filter`, `order_by` всегда в запросе | `OrderGatewayOrderConverter.java:68–90` | CONFIRMED | Info |
| I-05 | §4.1.1 | Metadata `rqTm`, `rqUid`, `operUid` | `GrpcRequestUtil.java:25–27, 49–54` | CONFIRMED | Info |
| I-06 | §4.1.1 | Timeout `grpc.order_gateway.deadline`; retry нет | `application-test.yml:58–60`; `GrpcRequestUtil.java:45` | CONFIRMED | Info |
| I-07 | §4.1.1 | Upstream `trade-operations-commons` | `order-gateway.proto:1–2` | CONFIRMED | Info |
| I-08 | §4.1.1 TO BE | BPH `yield` для sibling-path | `bph.yml` — grep `yield` — 0 | NOT FOUND | Major (TO BE, sibling) |

### Конфигурация

| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|----|------------------|-------------|----------------------|--------|-------------|
| K-01 | §5.4 | Ключ `ogGetTradeOrders` | `RpcNamesForRequestCondition.java:9` | CONFIRMED | Info |
| K-02 | §5.4 | Test-default active/inactive = true | `application-test.yml:71–73` | CONFIRMED | Info |
| K-03 | §5.4 | Test `maxRecords = 100` | `application-test.yml:138` | CONFIRMED | Info |
| K-04 | §5.4 | Test `grpc.order_gateway.deadline = 50000` | `application-test.yml:58–60` | CONFIRMED | Info |
| K-05 | §5.4 | Prod-defaults «как в test» | Prod ConfigMap в репозитории отсутствует | UNVERIFIABLE | Minor |

### Feature toggles

| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|----|------------------|-------------|----------------------|--------|-------------|
| T-01 | §CN-02, §5.4, §5.5 | `active`/`inactive` — группы статусов; оба false → запрос не выполняется | `SplitStatusFilter.java:28–38`; `AbstractOperationGateway.java:69–70` | CONFIRMED | Info |
| T-02 | §CN-02, §5.5 | Правило только при instrument-filter | `AbstractSplitStatusGrpcGateway.java:47–53`; `AbstractOperationGateway.java:164–166` | CONFIRMED | Info |
| T-03 | §5.5 | Оба false → GetTradeOrders не вызывается | `OriginalInstrumentWithItsVersionsRequestsConfigMapTest.java:30–31, 72` | CONFIRMED | Info |
| T-04 | §5.5 | Отдельного toggle для доходности нет | grep yield в конфигах — 0 | CONFIRMED | Info |

### Поведение и алгоритмы

| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|----|------------------|-------------|----------------------|--------|-------------|
| B-01 | §BR-04 | Приоритет ОГ над BPH/BC для заявки | `OrderMerger.java:212–226` | CONFIRMED | Info |
| B-02 | §CN-06 | Счётчик OgConverter — минимальный маппинг | `OgConverter.java:23–30` | CONFIRMED | Info |
| B-03 | §4.2.3.1 | `value_per_instrument_item_pcnt` → details | `OgTradeOperationCreator.java:191, 219` | CONFIRMED | Info |
| B-04 | §2, §4.1.1.1 | OG bond-поля в `ReportOrderOperationDetails`, lead без yield | `OgTradeOperationCreator.java:88–102, 198–232` | CONFIRMED | Info |
| B-05 | §4.2.3 TO BE | Чтение yield в `OrderGrpcConverter` | `OrderGrpcConverter.java` — yield не маппится | NOT FOUND | Major (TO BE) |
| B-06 | §4.2.3 TO BE | `HistoryOperationLead.yield` в `OgTradeOperationCreator` | `HistoryOperationLead.builder()` — yield не задаётся (`:88–102`) | NOT FOUND | Major (TO BE) |
| B-07 | §BR-05 TO BE | BR-05: обогащение yield из BPH в OG-path | `getOgTradeOperation()` не передаёт `bphOrderEnrichDto` (`:258–273`); `OgTradeOperationCreator` не использует BPH yield | NOT FOUND | Major (TO BE) |
| B-08 | §2 TO BE | `OrderMerger` передаёт BPH в OG creator | `TradeOperationCreationContext.bphOrderEnrichDto` есть (`:33`), но в OG-path не заполняется | PARTIAL | Major (TO BE) |
| B-09 | §1.3 alt 5a | `UNEXPECTED_ERROR` → `buildBphLinkedTradeOperation` | `OrderMerger.java:207–214` | CONFIRMED | Info |
| B-10 | §CN-12 | Матчинг `exchangeOrderId` ↔ `selfIdTs` | OG map: `exchangeOrderId` (`:83–84`); BPH map: `selfIdTs` (`:111–114`); merge по общему ключу (`:168–177`) | CONFIRMED | Info |
| B-11 | §1.3 alt 6a, §CN-08 | gRPC error / `GetActiveOrders` без yield | `ActiveOrderConverter.java` — yield нет; OG error — gateway AS IS | CONFIRMED | Info |
| B-12 | §1.3 alt 4b TO BE | Warn-log при конфликте OG/BPH yield | grep warn+yield — 0 | NOT FOUND | Major (TO BE) |

### Тесты и фикстуры

| ID | Раздел документа | Утверждение | Доказательство в коде | Статус | Критичность |
|----|------------------|-------------|----------------------|--------|-------------|
| F-01 | §2 | Фикстуры `order_gateway/*.json` | `src/test/resources/.../order_gateway/` — 11+ response JSON | CONFIRMED | Info |
| F-02 | §2 TO BE | Фикстуры с yield | Текущие JSON без yield | NOT FOUND | Major (TO BE) |
| F-03 | §2 приёмка | `OrderMergerTest` + `OgTradeOperationCreator` tests | `OrderMergerTest.java` есть; отдельного `OgTradeOperationCreatorTest` — нет | NOT FOUND | Major (TO BE) |

## Изменения vs итерация 2

| Тема | Итерация 2 | Итерация 3 |
|------|------------|------------|
| Уровень yield | `ReportOrderOperationDetails` (GAP) | `HistoryOperationLead` — spec обновлён; код без yield (TO BE) |
| BPH enrichment | B-07 CONFIRMED «не подмешивается» | BR-05 TO BE — NOT FOUND (ожидаемо) |
| B-08 | `getOgTradeOperation` без BPH | PARTIAL: поле контекста есть, wiring TO BE |
| Alt 5a/6a | Не проверялись | CONFIRMED UNEXPECTED_ERROR path |
| CN-09 Ignite | Не детализировалось | CONFIRMED cache lead целиком |

## Рекомендуемые действия

1. **Spec ready для разработки** — AS IS согласован; TO BE gaps ожидаемы до merge.
2. Реализация (порядок): upstream proto `YieldData` → `OrderGrpcConverter` → wrapper → `OrderMerger.getOgTradeOperation` (+ `bphOrderEnrichDto`) → `OgTradeOperationCreator` (`HistoryOperationLead.yield`) → `history.yml` → warn-log BR-05 → unit-тесты.
3. Sibling `bph-linked-events-yield`: `bph.yml` yield + та же inline-схема в `HistoryOperationLead`.
4. BDUI формат «N %» (SIHIST-3373) — проверить при наличии `history-ops-screen-api` в workspace.

## Пропущено

- `history-ops-screen-api` — не в `repositories/` (BDUI, ACL)
- Upstream `trade-operations-commons` — вне workspace
- Prod Helm/ConfigMap

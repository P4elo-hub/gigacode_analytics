---
report_type: feature-challenges
slug: og-trading-order-yield
source_document: Feature-writing/og-trading-order-yield/og-trading-order-yield.md
generated_at: 2026-08-28
challenge_iteration: 1
language: ru
---

# Критический разбор: og-trading-order-yield

**Спецификация:** `Feature-writing/og-trading-order-yield/og-trading-order-yield.md`  
**Банк вопросов:** `Feature-writing/og-trading-order-yield/og-trading-order-yield-challenges.md`

## Сводка

- Вопросов: 26 (Critical: 4 · Major: 14 · Minor: 8) — все resolved
- Фокус прогона: полный проход после `/resolve-gaps` (BR-05, HistoryOperationLead, PriceData)

---

## Бизнес-логика и use case

| ID | § spec | Вопрос | Тип | Severity | Статус |
|----|--------|--------|-----|----------|--------|
| CH-01 | §1.1 BR-05, §1.3 alt 4a | ОГ и BPH **оба** возвращают `yield`, но значения **различаются** (value или currency). BR-05 задаёт приоритет только при *отсутствии* в ОГ. Какое значение показывать пользователю — строго ОГ, логировать расхождение, или merge по правилу? | corner-case | Critical | resolved |
| CH-02 | §1.3 alt 3a/4a, §4.2.3.1 | Что считается «yield отсутствует в ОГ» для перехода к BR-05: только `optional` unset, или также `value=0`, пустая строка, `value` без `currency`, `null` в JSON? | contract-edge | Critical | resolved |
| CH-03 | §1.1 BR-05, §1.3 alt 4a | При совпадении заявки по `exchangeOrderId` в BPH linked events может быть **несколько** узлов (main order, deal, commission). Из какого узла брать `yield` для обогащения — только main trade order или любой дочерний? | scope-ambiguity | Major | resolved |
| CH-04 | §1.3 alt 4a.3 | Ключ матчинга BPH в коде — `selfIdTs` / `externalSystemId` (`OrderMerger`); spec ссылается на `exchangeOrderId`. Гарантировано ли равенство этих идентификаторов для всех заявок, где срабатывает BR-05? | contradiction | Major | resolved |
| CH-05 | §1.3 (отсутствует) | Заявка ОГ в статусе `UNEXPECTED_ERROR`: `OrderMerger` переключается на **полный** BPH-path (`buildBphLinkedTradeOperation`), а не на OG+c enrichment. Должен ли `yield` в этом случае браться из BPH целиком, и входит ли сценарий в BR-05 или в sibling `bph-linked-events-yield`? | missing-flow | Major | resolved |
| CH-06 | §1.2 alt 4a AS IS, §1.3 | Заявки ОГ **без** `exchangeOrderId` обрабатываются отдельным потоком (`ogOrdersWithoutExchangeOrderId`). Применяется ли BR-05 к ним, и по какому ключу искать yield в BPH? | corner-case | Major | resolved |
| CH-07 | §1.3 alt 2a, §5.5 | На instrument screen при обоих `ogGetTradeOrders.*=false` `GetTradeOrders` не вызывается. Если заявка видна только через BPH-path — доходность должна приходить из sibling-фичи; если заявка «пропала» из-за отсутствия ОГ — это ожидаемая деградация или дефект UX? | scope-ambiguity | Major | resolved |
| CH-08 | §1.1 таблица «Противоречия» | Таблица заявляет «противоречия не выявлены», но BR-05 (обогащение из BPH) меняет поведение относительно `SIHIST-3502` («приоритет ОГ» для атрибутов заявки). Нужно ли явно зафиксировать исключение «yield — единственный атрибут, обогащаемый из BPH»? | contradiction | Minor | resolved |

---

## Контракты и интеграции

| ID | § spec | Вопрос | Тип | Severity | Статус |
|----|--------|--------|-----|----------|--------|
| CH-09 | §4.1.1 `YieldData`, §4.1.1.1 | В `history.yml` **нет** схемы `PriceData` (grep по репозиторию). Как описывается `HistoryOperationLead.yield` в OpenAPI — inline object, новая схема `PriceData`, или `$ref` из другого файла? Согласовано ли это с черновиком `bph-linked-events-yield` (там `<поле доходности>` типа `number`)? | contract-edge | Major | resolved |
| CH-10 | §4.1.1 примечание | Допускаются два формата upstream: полный `YieldData` или «только Decimal + currency из `TradeOrder.currency`». Как consumer отличит их в runtime и что делать, если `yield.currency` ≠ `TradeOrder.currency`? | contract-edge | Major | resolved |
| CH-11 | §4.1.1, §4.1.1.1 | `HistoryOperationLead` уже содержит поле `currency` (валюта операции). При заполнении `yield.currency` — должны ли они **всегда** совпадать, или допускается расхождение (например, доходность в % пунктах с валютой номинала)? | data-edge | Major | resolved |
| CH-12 | §4.1.1 ошибки | При gRPC error ОГ весь источник OG недоступен; spec не описывает, сохраняется ли BR-05 для заявок, которые **были** бы из ОГ, но попали только из BPH/BC. Нужен ли отдельный alt-сценарий «ОГ упал, yield только из BPH»? | integration-edge | Major | resolved |
| CH-13 | §4.1.1 примечание INT-04 | Spec ожидает field number «следующий после 41», но не фиксирует номер. Что делать при расхождении с upstream `trade-operations-commons` (wire incompatibility) — блокер релиза или adapter-слой? | contract-edge | Minor | resolved |
| CH-14 | §4.1.1 CN-01 | Поэтапный rollout: новый `history-ops` + старый ОГ без `yield` — покрыто. А **новый ОГ с yield + старый history-ops** — поле игнорируется proto3; нужно ли явное требование минимальной версии ОГ для фичи? | contract-edge | Minor | resolved |

---

## Данные и маппинг

| ID | § spec | Вопрос | Тип | Severity | Статус |
|----|--------|--------|-----|----------|--------|
| CH-15 | §1.1 BR-05, §4.2.3.1 | `OrderMerger.getOgTradeOperation()` **не передаёт** `BphOrderEnrichDto` в `OgTradeOperationCreator` (только OG deals + BPH commissions). Где именно в архитектуре должен выполняться BR-05 — merger, creator, post-processor — и это TO BE изменение `OrderMerger`? | missing-flow | Critical | resolved |
| CH-16 | §2 CN-09, §4.2.3 | При включённом Ignite операция кэшируется (`OperationsIgniteProxyService`). Если `yield` транзитный и не в PostgreSQL — попадает ли он в cache entry, и не отдаётся ли **устаревший** yield после обновления данных в ОГ/BPH? | data-edge | Major | resolved |
| CH-17 | §4.2.3.1 | Округление и scale: `google.type.Decimal` → `number` в JSON. Сколько знаков после запятой допустимо для доходности на UI и нужно ли нормализовать (как для `total_sum` с `@JsonFormat STRING`)? | data-edge | Minor | resolved |
| CH-18 | §4.2.3 | Отрицательная или аномально большая доходность от ОГ — валидировать на стороне НО или пробрасывать as-is? | data-edge | Minor | resolved |

---

## NFR, toggles, конфигурация

| ID | § spec | Вопрос | Тип | Severity | Статус |
|----|--------|--------|-----|----------|--------|
| CH-19 | §5.4, `maxRecords` | Лимит `app-config.reporting.maxRecords` (100 в test) может отсечь заявки с yield за пределами окна. Это acceptable degradation или нужен критерий «доходность видна только для заявок в первых N записях»? | nfr-hole | Minor | resolved |
| CH-20 | §5.4 prod-defaults | Prod = test «до уточнения эксплуатацией» — при изменении toggles mid-flight пользователь может потерять yield на instrument screen без явного сигнала. Нужен ли мониторинг/алерт на systematic empty yield? | nfr-hole | Minor | resolved |

---

## Ошибки и observability

| ID | § spec | Вопрос | Тип | Severity | Статус |
|----|--------|--------|-----|----------|--------|
| CH-21 | §4.1.1 ошибки, BR-05 | При systematic отсутствии `yield` (ОГ не отдаёт, BPH тоже) — достаточно silent skip, или нужны метрики `yield_missing_total` / лог с `exchangeOrderId` для PO? | nfr-hole | Minor | resolved |

---

## Безопасность и compliance

| ID | § spec | Вопрос | Тип | Severity | Статус |
|----|--------|--------|-----|----------|--------|
| CH-22 | §1.3 шаг 6, SIHIST-3373 | Доходность — чувствительный финансовый показатель. Ограничена ли видимость тем же ACL, что и остальные поля деталки заявки, или нужны отдельные правила маскирования/отображения? | scope-ambiguity | Major | resolved |

---

## Тесты и приёмка

| ID | § spec | Вопрос | Тип | Severity | Статус |
|----|--------|--------|-----|----------|--------|
| CH-23 | §1.3, §2 «Обновление фикстур» | Нет явных acceptance criteria / матрицы тестов для BR-05 (OG empty + BPH filled, оба filled conflict, OG error → BPH path). Какие интеграционные тесты (`OrderMergerTest`, `HistoryOpsFeedScreenTest`) обязательны для приёмки? | test-gap | Critical | resolved |
| CH-24 | §1.3 шаг 6 | SIHIST-3373 referenced, но не зафиксирован формат отображения: абсолютное значение vs процент, локаль, подпись поля. Как проверить «корректное отображение» в measurable-критерии §1.1? | test-gap | Major | resolved |
| CH-25 | §4.1.1.1 `OgTradeOperationCreator` | Рефactoring: yield переносится в `HistoryOperationLead.builder()` (сейчас bond-поля — в details). Нужен ли регрессионный тест, что **существующие** поля details не затронуты при добавлении `lead.yield`? | test-gap | Major | resolved |

---

## Связь с sibling-фичей

| ID | § spec | Вопрос | Тип | Severity | Статус |
|----|--------|--------|-----|----------|--------|
| CH-26 | §1.1 CN-03, CN-07 | `bph-linked-events-yield.md` всё ещё содержит открытые GAP по типу/уровню `yield` (`number` vs PriceData). При параллельной реализации двух фич — кто владелец единой схемы `HistoryOperationLead.yield` и порядок merge в `history.yml`? | contradiction | Major | resolved |

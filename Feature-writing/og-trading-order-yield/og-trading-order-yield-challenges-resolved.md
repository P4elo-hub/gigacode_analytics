---
report_type: challenges-resolved
slug: og-trading-order-yield
source_document: Feature-writing/og-trading-order-yield/og-trading-order-yield.md
challenges_document: Feature-writing/og-trading-order-yield/og-trading-order-yield-challenges.md
generated_at: 2026-08-28
session: 1
language: ru
---

# Карта закрытых вопросов: og-trading-order-yield

## Сводка

- Resolved: 26 · Covered: 0 · Deferred: 0

## Сессия 1 (2026-08-28)

| ID | Verdict | Выбор | Решение | Затронутые § | Источник |
|----|---------|-------|---------|--------------|----------|
| CH-01 | MISSING → resolved | b | При конфликте ОГ vs BPH — значение ОГ + warn-лог | §1.1 BR-05, alt 4b | PO |
| CH-02 | MISSING → resolved | b | Absent: unset/null/пустой value/нет currency; value=0 валидно → CN-11 | §1.1 CN-11, alt 3a | PO |
| CH-03 | MISSING → resolved | b | yield из любого узла BPH linked events с заполненным yield | alt 4a.3 | PO |
| CH-04 | MISSING → resolved | a | Матчинг exchangeOrderId = selfIdTs → CN-12 | §1.1 CN-12, §4.2.3.1 | SIHIST-3502 |
| CH-05 | MISSING → resolved | a | UNEXPECTED_ERROR → полный BPH-path; BR-05 не применяется → alt 5a | alt 5a | OrderMerger.java |
| CH-06 | MISSING → resolved | a | Без exchangeOrderId BR-05 не выполняется | CN-12 | PO |
| CH-07 | MISSING → resolved | a | toggles OFF → yield из BPH-path (sibling); не дефект OG-фичи | alt 2a.3 | PO |
| CH-08 | MISSING → resolved | a | CN-10: yield — единственный обогащаемый атрибут | §1.1 CN-10, противоречия | PO |
| CH-09 | MISSING → resolved | b | Inline object {value, currency} в history.yml | §4.1.1.1, CN-03 | PO |
| CH-10 | MISSING → resolved | b | yield.currency всегда из TradeOrder.currency | §4.1.1, §4.2.3.1 | PO |
| CH-11 | MISSING → resolved | a | lead.currency и yield.currency независимы | §4.1.1 примечание | PO |
| CH-12 | MISSING → resolved | a | gRPC error → yield через BPH-path (sibling) → alt 6a | §4.1.1 ошибки | PO |
| CH-13 | MISSING → resolved | b | Upstream dependency; номер field не фиксируем | §4.1.1 примечание | PO |
| CH-14 | MISSING → resolved | b | Старый history-ops + новый ОГ — out of scope | — | PO |
| CH-15 | MISSING → resolved | a | BR-05 в OrderMerger → передача BPH в OgTradeOperationCreator | §2, alt 4a.4 | PO |
| CH-16 | MISSING → resolved | a | Yield в Ignite cache с TTL операции | CN-09, §2 | PO |
| CH-17 | MISSING → resolved | a | number as-is, scale от ОГ | §2 | PO |
| CH-18 | MISSING → resolved | a | As-is pass-through | §2 | PO |
| CH-19 | MISSING → resolved | a | maxRecords — acceptable degradation | §5.4 | PO |
| CH-20 | MISSING → resolved | a | Мониторинг — out of scope dev-spec | — | PO |
| CH-21 | MISSING → resolved | a | Silent skip без метрик | §4.1.1 пограничные | PO |
| CH-22 | MISSING → resolved | a | ACL как bond_denomination / value_per_instrument_item_pcnt | §4.1.1.1 | SIHIST-3373 |
| CH-23 | MISSING → resolved | b | Unit: OrderMergerTest + OgTradeOperationCreator | §2 приёмка | PO |
| CH-24 | MISSING → resolved | a | BDUI формат «N %» как value_per_instrument_item_pcnt | §1.3 шаг 6 | SIHIST-3373 |
| CH-25 | MISSING → resolved | a | Регрессия ReportOrderOperationDetails в unit-тестах | §2 приёмка | PO |
| CH-26 | MISSING → resolved | a | history-ops владелец history.yml; bph-yield подстраивается | CN-03, CN-07 | PO |

## Отложено

| ID | Причина |
|----|---------|
| — | — |

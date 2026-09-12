---
report_type: gaps-resolved
slug: og-trading-order-yield
source_document: Feature-writing/og-trading-order-yield/og-trading-order-yield.md
generated_at: 2026-08-28
session: 1
---

# Карта закрытых gaps: og-trading-order-yield

**Спецификация:** `Feature-writing/og-trading-order-yield/og-trading-order-yield.md`  
**Карта:** `Feature-writing/og-trading-order-yield/og-trading-order-yield-gaps-resolved.md`

## Сводка

- Закрыто: 22 · Отложено: 0

## Сессия 1 (2026-08-28)

| ID | Выбор | Решение | Затронутые § |
|----|-------|---------|--------------|
| GAP-GOAL-01 | a | Метрики: placeholder TBD — согласовать с PO | §1.1 Цель |
| GAP-GOAL-02 | a | Релиз: placeholder TBD — уточнить у PO | §1.1 SMART |
| GAP-GOAL-03 / Q-01 | a | Единое имя поля `yield` во всех контрактах | §1.1, §4.1.1, §4.1.1.1, §4.2.3 |
| GAP-UCAS-01 | a | Стоимость проблемы: «Не оценена (TBD PO)» | §1.2 Таблица проблем |
| GAP-CONS-02 / GAP-INT-05 / GAP-MAP-01 / Q-04 | b | `yield` в `HistoryOperationLead`, не в `ReportOrderOperationDetails` | §1.1 CN-03, §2, §4.1.1.1, §4.2.3, маппинг |
| GAP-UCTB-02 / GAP-DM-02 / Q-05 | b | Структура PriceData (`value` + `currency`) в proto (`YieldData`) и history.yml | §4.1.1, §4.1.1.1, §4.2.3 |
| GAP-UCTB-01 / Q-08 | b | Обогащение yield из BPH, если в ОГ поле пустое → BR-05, alt 3a/4a | §1.1 BR-05, §1.3 TO BE |
| GAP-UCTB-04 / Q-07 | a | Вне scope: только `GetTradeOrders`; `GetActiveOrders` не затрагивается → CN-08 | §1.1 CN-08, §5.5 |
| GAP-CONS-01 / GAP-DM-01 / Q-09 | a | Транзит: без PostgreSQL; Ignite как часть операции → CN-09 | §2, §4.2.3 |
| GAP-INT-03 / Q-03 | a | Параметра запроса нет; yield безусловно в `TradeOrder` | §4.1.1 |
| GAP-DM-03 / Q-06 | b | Все инструменты, где ОГ вернул yield; фильтра на стороне НО нет | §2 |
| GAP-UCTB-03 / Q-10 | a | BDUI: деталка торговой заявки SIHIST-3373, рядом с облигационными полями | §1.3 шаг 6 |
| GAP-INT-04 | b | Ожидание: следующий field после `card_number=41`; финальный номер не фиксируется | §4.1.1 TradeOrder |
| GAP-NFR-01 | b | Prod toggles = как в test до уточнения эксплуатацией | §5.4 |
| GAP-NFR-02 | b | Prod maxRecords = как в test до уточнения эксплуатацией | §5.4 |
| GAP-NFR-03 | b | Процедура изменения: стандартный ConfigMap / деплой | §5.4 Процедура изменения |
| GAP-NFR-04 | b | Prod deadline = как в test (`50000` ms) до уточнения эксплуатацией | §5.4, §4.1.1 |

## Отложено

| ID | Причина |
|----|---------|
| — | — |

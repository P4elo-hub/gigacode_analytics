---
report_type: gaps-resolved
slug: bph-linked-events-yield
source_document: Feature-writing/bph-linked-events-yield/bph-linked-events-yield.md
context_document: Feature-context/bph-linked-events-yield.md
generated_at: 2026-09-20
session: 2
---

# Карта закрытых gaps: bph-linked-events-yield

**Спецификация:** `Feature-writing/bph-linked-events-yield/bph-linked-events-yield.md`
**Карта:** `Feature-writing/bph-linked-events-yield/bph-linked-events-yield-gaps-resolved.md`

## Сводка
- Закрыто фактом: 1 (GAP-UCAS-01, сессия 1)
- Закрыто решением пользователя: 58 (D-01…D-12, сессия 2)
- Всего закрыто: 59

## Сессия 1 (2026-09-20)

| ID | Выбор | Решение | Затронутые § | Связанный Q |
|----|-------|---------|--------------|-------------|
| GAP-UCAS-01 | fact | Таймаут/retry вызова BPH `GET_LINKED_EVENTS` задаётся runtime-конфигом HO (`WebClientBphConfiguration`), в analytics не описан; фича новых значений timeout/retry/fallback не вводит. Источник: `analytics/02-Modules/MOD-001-history-ops/integrations/bph.md` § «Таймауты, retry и fallback» | §1.2 (таблица gaps удалена), §4.1.1 (Timeout/Retry Policy, «Ошибки и исключения», «Таймауты, retry и fallback») | — |

## Сессия 2 (2026-09-20)

| ID | Выбор | Решение | Затронутые § | Связанный Q |
|----|-------|---------|--------------|-------------|
| GAP-UCTB-01, GAP-CONS-01, GAP-INT-01, GAP-ALG-01, GAP-MAP-01 | D-01 (a) | Входящий контракт BPH: поле `yield` — объект `PriceData {value, currency}` | §1.3 (предусловие 5, постусловие, BR-05, шаг 5, диаграмма TO BE), §2 (CN-01), §4.1.1.1, §4.2.2, §4.2.3-mapping | Q-01 |
| GAP-UCTB-02, GAP-CONS-02, GAP-INT-02, GAP-ALG-02, GAP-MAP-02 | D-02 (A) | REST `history.yml` `HistoryOperationLead`: `yield` = `PriceData {value, currency}`; схема `PriceData` вводится в `components.schemas` | §2 (CN-02, CN-06), §4.1.1.3, §4.2.2, §4.2.3-mapping | Q-02 |
| GAP-UCTB-03, GAP-CONS-03, GAP-INT-03, GAP-ALG-03, GAP-MAP-03 | D-03 (A) | gRPC `historyOperationDetails.proto` `GetDetailsResponse`: `optional PriceData yield = 99`; тип `PriceData` — инлайн `message` | §2 (CN-02, CN-06), §4.1.1.2, §4.2.2, §4.2.3-mapping | Q-03 |
| GAP-UCTB-04, GAP-CONS-04, GAP-INT-04, GAP-ALG-04, GAP-MAP-04 | D-04 (A) | Композит BDUI: «Доходность» (формат `{value} {currency}`), только в деталке | §2 (CN-11), §4.1.1.4, §4.2.2, §4.2.3-mapping | Q-04 |
| GAP-UCTB-05, GAP-CONS-05, GAP-INT-05, GAP-ALG-05, GAP-MAP-05 | D-05 (A) | В BPH-ответе поле приходит в `OperationData` (lead), читается напрямую | §1.3 (предусловие 5), §2 (CN-01), §4.1.1.1, §4.2.2 (шаг 4), §4.2.3-mapping | Q-05 |
| GAP-UCTB-06, GAP-CONS-06, GAP-INT-06, GAP-ALG-06, GAP-MAP-06 | D-06 (A) | Доходность несёт только `tradeOrder` (безусловная заявка) | §2 (CN-01), §4.1.1.1, §4.2.2, §4.2.3-mapping | Q-06 |
| GAP-UCTB-07, GAP-INT-09, GAP-ALG-07, GAP-MAP-07 | D-07 (A) | Уровень размещения в HO — `HistoryOperationLead` (lead) | §2 (CN-07), §4.1.1.2, §4.2.2, §4.2.3-mapping | Q-07 |
| GAP-UCTB-08, GAP-INT-10, GAP-ALG-08, GAP-MAP-08 | D-08 (A) | Пустой `value` = «нет значения» (поле не заполняется/не отображается); `0` и отрицательные допустимы и отображаются «как есть» | §2 (CN-08), §4.1.1.1 (валидация), §4.2.2, §4.2.3-mapping | Q-08 |
| GAP-UCTB-09, GAP-CONS-07, GAP-INT-07, GAP-ALG-09, GAP-MAP-09 | D-09 (A) | Поле приходит безусловно; новый параметр запроса не нужен | §2 (CN-01), §4.1.1.1 (request body), §4.2.2, §4.2.3-mapping | Q-09 |
| GAP-UCTB-10, GAP-CONS-08, GAP-INT-08, GAP-ALG-10, GAP-MAP-10 | D-10 (пересмотрено) | Фича-тогл для BPH-ветки доходности (OFF до готовности BPH, kill-switch); при OFF поле `yield` не читается и не пробрасывается | §2 (CN-14), §1.3 (предусловие 6), §4.1.1.1 (request body), §4.2.2 (предусловие 5) | Q-10 |
| GAP-UCTB-11, GAP-CONS-09, GAP-INT-11, GAP-ALG-11, GAP-MAP-11 | D-11 (A) | Готовое значение от BPH (passthrough, без пересчёта); нечитаемый формат → `null`, поток не прерывается | §2 (CN-10), §4.1.1 (данные и маппинг), §4.2.2, §4.2.3-mapping | Q-11 |
| GAP-UCTB-12, GAP-CONS-10, GAP-INT-12, GAP-ALG-12, GAP-MAP-12 | D-12 (A) | Привести BPH к единому `PriceData {value, currency}` optional (выравнивание с OG) | §2 (CN-03), §4.1.1.1, §4.2.2, §4.2.3-mapping | Q-12 |

---
report_type: gaps-resolved
slug: bph-moex-tax
source_document: Feature-writing/bph-moex-tax/bph-moex-tax.md
context_document: Feature-context/bph-moex-tax.md
generated_at: 2026-10-05
session: 4
---

# Карта закрытых gaps: bph-moex-tax

**Спецификация:** `Feature-writing/bph-moex-tax/bph-moex-tax.md`
**Карта:** `Feature-writing/bph-moex-tax/bph-moex-tax-gaps-resolved.md`

## Сводка

- Сессия 1 — закрыто **фактом** (без опроса): 10
- Сессия 2 — закрыто **по ответам пользователя** (D-01…D-05, батч 1 blockers): 38
- Сессия 3 — закрыто **фактом** (Q-06, `operation.name` / `info.displayed_name`): 6
- Сессия 4 — закрыто **по ответам пользователя** (D-06…D-08, цель/метрики/инициатор): 4

## Сессия 1 (2026-10-05)

Закрыто **фактом** из `CONTEXT_DOC` / `analytics/` (без опроса пользователя):

| ID | Выбор | Решение | Затронутые § | Связанный Q |
|----|-------|---------|--------------|-------------|
| GAP-UCTB-03 | факт | `info.additional_type = NULL` (одна info-строка) — по брифу/трактовке | §1.3 | Q-03 |
| GAP-CONS-03 | факт | `info.additional_type = NULL` | §2 | Q-03 |
| GAP-INT-03 | факт | `info.additional_type = NULL` → `additionalTypes[]` не передаётся в запросе | §4.1.1 | Q-03 |
| GAP-ALG-03 | факт | `info.additional_type = NULL` (одна строка), матчинг NULL ↔ `""` | §4.2.2 | Q-03 |
| GAP-DM-03 | факт | `info.additional_type = NULL` | §4.2.3 | Q-03 |
| GAP-MAP-03 | факт | source path `info.additional_type = NULL` | §4.2.4 | Q-03 |
| GAP-MIG-03 | факт | `info.additional_type = NULL` (по брифу) | §4.3 | Q-03 |
| GAP-UCAS-01 | факт | Триггер синхронизации — по запросу клиента МП (в ходе `SEND_OPERATIONS` / `GET_OPERATIONS`); отдельной cron-синхронизации нет (cron — только обновление кэша маппинга) | §1.2, §1.3 | — |
| GAP-UCAS-02 | факт | Недоступность BPH → partial failure (возвращаются операции OG/BC с признаком неполноты); timeout/retry — конфигурация WebClient HO (`WebClientBphConfiguration`) | §1.2, §1.3, §4.2.2 | — |
| GAP-UCAS-03 | факт | Исходящий канал — gRPC `SEND_OPERATIONS` (`HistoryOpsGrpcService`) | §1.2, §1.3, §4.2.2 | — |

**Источники фактов:** `CONTEXT_DOC` (бриф/трактовка «additional_type — отсутствует (NULL)»); `analytics/02-Modules/MOD-001-history-ops/README.md` (HistoryOpsGrpcService → gRPC SEND_OPERATIONS); `analytics/02-Modules/MOD-001-history-ops/integrations/bph.md` (§«Таймауты, retry и fallback», §«Ошибки» — partial failure, WebClientBphConfiguration).

## Сессия 2 (2026-10-05)

Закрыто **по ответам пользователя** из `DECISIONS` (D-01…D-05, все `applied`):

| ID | Выбор | Решение | Затронутые § | Связанный Q |
|----|-------|---------|--------------|-------------|
| GAP-GOAL-04 | a | `MOEX_TAX` подтверждено (как в брифе); `comment` = «Удержание суммы налога» | §1.1 | Q-01, Q-02 |
| GAP-UCTB-01 | a | Написание `MOEX_TAX` подтверждено | §1.3 | Q-01 |
| GAP-CONS-01 | a | Написание `MOEX_TAX` подтверждено | §2 | Q-01 |
| GAP-INT-01 | a | Написание `MOEX_TAX` подтверждено | §4.1.1 | Q-01 |
| GAP-ALG-01 | a | Написание `MOEX_TAX` подтверждено | §4.2.2 | Q-01 |
| GAP-DM-01 | a | Написание `MOEX_TAX` подтверждено | §4.2.3 | Q-01 |
| GAP-MAP-01 | a | Написание `MOEX_TAX` подтверждено | §4.2.4 | Q-01 |
| GAP-MIG-01 | a | Написание `MOEX_TAX` подтверждено | §4.3 | Q-01 |
| GAP-OBS-01 | a | Написание `MOEX_TAX` подтверждено | §5.3 | Q-01 |
| GAP-UCTB-02 | b | `comment` = «Удержание суммы налога» (переиспользована формулировка `TAX_RETAIN`) | §1.3 | Q-02 |
| GAP-CONS-02 | b | `comment` = «Удержание суммы налога» | §2 | Q-02 |
| GAP-INT-02 | b | `comment` = «Удержание суммы налога» | §4.1.1 | Q-02 |
| GAP-ALG-02 | b | `comment` = «Удержание суммы налога» | §4.2.2 | Q-02 |
| GAP-DM-02 | b | `comment` = «Удержание суммы налога» | §4.2.3 | Q-02 |
| GAP-MAP-02 | b | `comment` = «Удержание суммы налога» | §4.2.4 | Q-02 |
| GAP-MIG-02 | b | `comment` = «Удержание суммы налога» | §4.3 | Q-02 |
| GAP-UCTB-04 | a | `operation.bc_id` = NULL (BPH-only, паттерн `TAX_REFUND_BROK_ACCOUNT`) | §1.3 | Q-04 |
| GAP-CONS-04 | a | `operation.bc_id` = NULL | §2 | Q-04 |
| GAP-ALG-04 | a | `operation.bc_id` = NULL | §4.2.2 | Q-04 |
| GAP-DM-04 | a | `operation.bc_id` = NULL | §4.2.3, §4.2.4 | Q-04 |
| GAP-MAP-07 | a | `operation.bc_id` = NULL | §4.2.4 | Q-04 |
| GAP-MIG-04 | a | `operation.bc_id` = NULL | §4.3 | Q-04 |
| GAP-OBS-02 | a | `bc_id` = NULL → системный лог «Unexpected additional type…» и метрика `unexpected_additional_type_for_common_operation` не срабатывают | §5.3 | Q-04 |
| GAP-UCTB-05 | a | BPH-статус `COMPLETE` (id=19 → `executed`) + связка `status_to_operation(operation↔19)` | §1.3 | Q-05 |
| GAP-CONS-05 | a | BPH-статус `COMPLETE` + связка `status_to_operation` | §2 | Q-05 |
| GAP-INT-05 | a | BPH-статус `COMPLETE` + связка `status_to_operation` | §4.1.1 | Q-05 |
| GAP-ALG-05 | a | BPH-статус `COMPLETE` + связка `status_to_operation` | §4.2.2 | Q-05 |
| GAP-DM-05 | a | `status_to_operation.status_id` = 19 (`COMPLETE`) | §4.2.3 | Q-05 |
| GAP-MAP-05 | a | BPH-статус `COMPLETE` (id 19 → `executed`) | §4.2.4 | Q-05 |
| GAP-MIG-05 | a | `status_to_operation.status_id` = 19 (`COMPLETE`) | §4.3 | Q-05 |
| GAP-UCTB-07 | a | `lead.additionalType` в ответе BPH = null/отсутствует → матчинг срабатывает, `comment` подставляется | §1.3 | Q-07 |
| GAP-CONS-07 | a | `lead.additionalType` = null/отсутствует | §2 | Q-07 |
| GAP-INT-04 | a | `lead.additionalType` = null/отсутствует | §4.1.1 | Q-07 |
| GAP-ALG-06 | a | `lead.additionalType` = null/отсутствует | §4.2.2 | Q-07 |
| GAP-DM-07 | a | `lead.additionalType` = null/отсутствует | §4.2.3 | Q-07 |
| GAP-MAP-04 | a | `lead.additionalType` = null/отсутствует | §4.2.4 | Q-07 |
| GAP-MIG-07 | a | `lead.additionalType` = null/отсутствует | §4.3 | Q-07 |
| GAP-OBS-03 | a | `lead.additionalType` = null/отсутствует | §5.3 | Q-07 |

**Источник решений:** `Feature-writing/bph-moex-tax/bph-moex-tax-decisions.md` — D-01 (Q-01), D-02 (Q-02), D-03 (Q-04), D-04 (Q-05), D-05 (Q-07); ответы пользователя, статус `applied`.

## Сессия 3 (2026-10-05)

Закрыто **фактом** из `db-export/БД ИО.md` / `repositories/` (без опроса пользователя) — кластер Q-06 (`operation.name` / `info.displayed_name`):

| ID | Выбор | Решение | Затронутые § | Связанный Q |
|----|-------|---------|--------------|-------------|
| GAP-UCTB-06 | факт | `operation.name` = «Удержание суммы налога» (переиспользована формулировка `TAX_RETAIN`, согласуется с D-02); `info.displayed_name` = NULL (универсальный паттерн) | §1.3 | Q-06 |
| GAP-CONS-06 | факт | `operation.name` = «Удержание суммы налога»; `info.displayed_name` = NULL | §2 | Q-06 |
| GAP-ALG-07 | факт | `operation.name` = «Удержание суммы налога»; `info.displayed_name` = NULL | §4.2.2 | Q-06 |
| GAP-DM-06 | факт | `operation.name` = «Удержание суммы налога»; `info.displayed_name` = NULL | §4.2.3 | Q-06 |
| GAP-MAP-06 | факт | `operationDisplayName` = `info.displayed_name` = NULL (у всех существующих операций `displayed_name` = NULL) | §4.2.4 | Q-06 |
| GAP-MIG-06 | факт | `operation.name` = «Удержание суммы налога»; `info.displayed_name` = NULL | §4.3 | Q-06 |

**Источники фактов:** `db-export/БД ИО.md:476,1692,2923` (`operation` id 2 = `tax`, `name` = «Удержание суммы налога»); `db-export/БД ИО.md:1726,1760-1763,2952,2986-2989` и кэш-строки (`"displayed_name": null` повсюду) — `info.displayed_name` = NULL у всех существующих операций; `repositories/ИО/history-ops/.../conversion/BphCommonClientConverter.java:127,216-217` (`enrichOperationDisplayName` = `info.displayed_name`), `model/Operation.java:13` + `model/AdditionalInfo.java:16-17`.

**В этой же сессии** зафиксированы `needs-answer` (D-06…D-08: `GAP-GOAL-01`, `GAP-GOAL-02`, `GAP-GOAL-03`, `GAP-OBS-05`) и `deferred` (D-09…D-12: `GAP-CONS-08`, `GAP-DM-08`, `GAP-MIG-08`, `GAP-DM-09`, `GAP-MIG-09`, `GAP-MIG-10`, `GAP-OBS-04`) — см. `DECISIONS`.

## Сессия 4 (2026-10-05)

Закрыто **по ответам пользователя** из `DECISIONS` (D-06…D-08, все `applied`) — кластер «цель фичи / инициатор / метрики»:

| ID | Выбор | Решение | Затронутые § | Связанный Q |
|----|-------|---------|--------------|-------------|
| GAP-GOAL-01 | b | Инициатор = Команда history-ops (ИО) | §1.1 | — |
| GAP-GOAL-02 | b | Non-SMART: количественная метрика не задаётся, полноту обеспечивает `history_ops_integration_total`; отдельные бизнес-метрики/алерты не вводятся | §1.1, §5.3.2 | — |
| GAP-GOAL-03 | b | Draft — релиз/срок не зафиксирован; срок задаётся общим планом релизов ИО | §1.1 | — |
| GAP-OBS-05 | b | Отдельные бизнес-метрики/алерты Prometheus не вводятся; полнота обеспечивается `history_ops_integration_total` | §5.3.2 | — |

**Источник решений:** `Feature-writing/bph-moex-tax/bph-moex-tax-decisions.md` — D-06 (`GAP-GOAL-01`), D-07 (`GAP-GOAL-02`, `GAP-OBS-05`), D-08 (`GAP-GOAL-03`); ответы пользователя, статус `applied`.

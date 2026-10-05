---
report_type: gaps-resolved
slug: bph-moex-tax
source_document: Feature-writing/bph-moex-tax/bph-moex-tax.md
context_document: Feature-context/bph-moex-tax.md
generated_at: 2026-10-05
session: 2
---

# Карта закрытых gaps: bph-moex-tax

**Спецификация:** `Feature-writing/bph-moex-tax/bph-moex-tax.md`
**Карта:** `Feature-writing/bph-moex-tax/bph-moex-tax-gaps-resolved.md`

## Сводка
- Закрыто: 62
- Осталось открытыми: 0

## Сессия 1 (2026-10-05)

| ID | Выбор | Решение | Затронутые § | Связанный Q |
|----|-------|---------|--------------|-------------|
| GAP-GOAL-02 | a | subtype = `MOEX_TAX` (подтверждено контрактом BPH) | §1.1 (BR-01, CN-01) | Q-01 |
| GAP-UCTB-01 | a | subtype = `MOEX_TAX` | §1.3 (предусловие, happy path) | Q-01 |
| GAP-CONS-01 | a | subtype = `MOEX_TAX` (допущение AS-01 → подтверждено) | §2 (CN-01) | Q-01 |
| GAP-INT-01 | a | subtype = `MOEX_TAX` в request/response | §4.1.1 | Q-01 |
| GAP-ALG-06 | a | subtype = `MOEX_TAX` | §4.2.2 | Q-01 |
| GAP-DM-01 | a | `bph.subtype` = `MOEX_TAX` | §4.2.3 | Q-01 |
| GAP-MAP-01 | a | Source `subtype` = `MOEX_TAX` | §4.2.4 (маппинг) | Q-01 |
| GAP-MIG-01 | a | INSERT `subtype='MOEX_TAX'` | §4.2.5 (миграция) | Q-01 |
| GAP-ACC-04 | a | `subtype = MOEX_TAX` | §6 (test data) | Q-01 |
| GAP-GOAL-03 | b | `additionalType` = `NULL` (одна строка `info` с `additional_type=NULL`) | §1.1 («Противоречия») | Q-02 |
| GAP-UCTB-02 | b | `additionalType` = `NULL` | §1.3 (happy path) | Q-02 |
| GAP-CONS-02 | b | `additionalType` = `NULL` | §2 (CN-08) | Q-02 |
| GAP-INT-02 | b | `additionalType` = `NULL`; `additionalTypes[]` не заполняется | §4.1.1 | Q-02 |
| GAP-ALG-02 | b | `additionalType` = `NULL` | §4.2.2 | Q-02 |
| GAP-DM-02 | b | `info.additional_type` = `NULL` | §4.2.3 | Q-02 |
| GAP-MAP-02 | b | Source `additionalType` = `NULL` | §4.2.4 (маппинг) | Q-02 |
| GAP-MIG-02 | b | `info.additional_type = NULL`, одна строка | §4.2.5 (миграция) | Q-02 |
| GAP-ACC-02 | b | `additionalType = NULL` | §6 (сценарии ACC-E01) | Q-02 |
| GAP-GOAL-04 | b | `bc_id` = `NULL` (только BPH, ранний return) | §1.1 (BR-04) | Q-03 |
| GAP-UCTB-03 | b | `bc_id` = `NULL` | §1.3 (happy path, фильтры пропускаются) | Q-03 |
| GAP-CONS-03 | b | `bc_id` = `NULL` (допущение AS-02 → CN-09) | §2 (CN-09) | Q-03 |
| GAP-ALG-01 | b | `bc_id` = `NULL` | §4.2.2 (BR-13) | Q-03 |
| GAP-DM-03 | b | `operation.bc_id` = `NULL` | §4.2.3 | Q-03 |
| GAP-MAP-03 | b | watershed/`additionalType`-фильтр не применяются | §4.2.4 (маппинг) | Q-03 |
| GAP-MIG-03 | b | `bc_id = NULL` | §4.2.5 (миграция) | Q-03 |
| GAP-ACC-03 | b | `bc_id = NULL` | §6 (сценарии ACC-E02, N01) | Q-03 |
| GAP-GOAL-05 | a | `operation.name`=«Удержание налога MOEX», `info.comment`=«НАЛОГ МОСКОВСКОЙ БИРЖИ» | §1.1 (BR-03) | Q-04 |
| GAP-UCTB-04 | a | comment = «НАЛОГ МОСКОВСКОЙ БИРЖИ» | §1.3 (happy path) | Q-04 |
| GAP-CONS-04 | a | comment/name зафиксированы | §2 | Q-04 |
| GAP-INT-05 | a | comment = «НАЛОГ МОСКОВСКОЙ БИРЖИ» | §4.1.1 (маппинг) | Q-04 |
| GAP-ALG-03 | a | comment = «НАЛОГ МОСКОВСКОЙ БИРЖИ» | §4.2.2 | Q-04 |
| GAP-DM-04 | a | `operation.name`=«Удержание налога MOEX», `info.comment`=«НАЛОГ МОСКОВСКОЙ БИРЖИ», `displayed_name`=NULL | §4.2.3 | Q-04 |
| GAP-MAP-04 | a | comment = «НАЛОГ МОСКОВСКОЙ БИРЖИ», operationDisplayName = NULL | §4.2.4 (маппинг) | Q-04 |
| GAP-MIG-04 | a | comment/name зафиксированы | §4.2.5 (миграция) | Q-04 |
| GAP-ACC-01 | a | comment = «НАЛОГ МОСКОВСКОЙ БИРЖИ» | §6 (ACC-002) | Q-04 |
| GAP-CONS-05 | b | без watershed (ключ `TAXES\|MOEX_TAX` не добавляется) | §2 (CN-10) | Q-05 |
| GAP-ALG-05 | b | watershed не задаётся | §4.2.2 | Q-05 |
| GAP-MAP-06 | b | watershed не применяется | §4.2.4 (маппинг) | Q-05 |
| GAP-MIG-06 | b | watershed не задаётся | §4.2.5 (миграция) | Q-05 |
| GAP-ACC-07 | b | watershed не применяется (ACC-E03 → не применимо) | §6 | Q-05 |
| GAP-DM-05 | a | id строк: test 22/24/52/37, prod 25/27/79/57 | §4.2.3, §2 (CN-03) | Q-06 |
| GAP-MIG-05 | a | id строк зафиксированы | §4.2.5 (миграция) | Q-06 |
| GAP-UCTB-05 | a | статус `COMPLETE` (id=19), переиспользовать `status_to_operation` | §1.3 | Q-07 |
| GAP-CONS-06 | a | статус `COMPLETE` (допущение AS-03 → CN-11) | §2 (CN-11) | Q-07 |
| GAP-INT-03 | a | статус `COMPLETE` | §4.1.1 | Q-07 |
| GAP-ALG-04 | a | статус `COMPLETE` | §4.2.2 | Q-07 |
| GAP-DM-06 | a | `status_to_operation.status_id` = 19 | §4.2.3 | Q-07 |
| GAP-MAP-05 | a | enum status `COMPLETE` → `executed` | §4.2.4 (маппинг) | Q-07 |
| GAP-MIG-07 | a | статус `COMPLETE` | §4.2.5 (миграция) | Q-07 |
| GAP-ACC-05 | a | статус `COMPLETE` | §6 | Q-07 |
| GAP-UCAS-01 | a | диаграмма: один участник «МП / композит (screen-api)» (принято) | §1.2 (диаграмма) | — |
| GAP-UCAS-02 | a | имя сообщения описательное (принято) | §1.2 (диаграмма) | — |
| GAP-UCTB-06 | a | диаграмма: участник/имя сообщения (принято) | §1.3 (диаграмма), §2 (CN-13) | — |
| GAP-UCAS-03 | a | degraded `bcDataComplete=false`; timeout/retry вне scope | §1.2 (постусловие) | — |
| GAP-UCTB-07 | a | degraded `bcDataComplete=false` | §1.3 (постусловие) | — |
| GAP-INT-04 | a | degraded `bcDataComplete=false`; timeout/retry вне scope (CN-12) | §4.1.1 | — |

## Сессия 2 (2026-10-05)

| ID | Выбор | Решение | Затронутые § | Связанный Q |
|----|-------|---------|--------------|-------------|
| GAP-GOAL-01 | b | Источник = бриф (Product request); инициатор и дата/версия не указаны («—») | §1.1 «Источник требования» | — |
| GAP-GOAL-06 | b | non-SMART: метрики и срок не заданы в брифе («не задано в брифе») | §1.1 «Цель фичи», SMART | — |
| GAP-MIG-08 | b | Версия PostgreSQL не фиксируется | §4.2.4 «Контекст миграции» | — |
| GAP-MIG-09 | b | Downtime не требуется (additive DML) | §4.2.4 «Контекст миграции» | — |
| GAP-MIG-10 | b | Объём — единичные строки (по одной в 4 таблицах) | §4.2.4 «Контекст миграции» | — |
| GAP-ACC-06 | b | Владелец приёмки и стенды не определены в брифе («—»), задаются на этапе релиза | §6 «Контекст тестирования» | — |

---
report_type: gaps-resolved
slug: bph-portfolio-size-tax
source_document: Feature-writing/bph-portfolio-size-tax/bph-portfolio-size-tax.md
context_document: Feature-context/bph-portfolio-size-tax.md
generated_at: 2026-08-29
session: 1
---

# Карта закрытых gaps: bph-portfolio-size-tax

**Спецификация:** `Feature-writing/bph-portfolio-size-tax/bph-portfolio-size-tax.md`
**Карта:** `Feature-writing/bph-portfolio-size-tax/bph-portfolio-size-tax-gaps-resolved.md`

## Сводка

- Закрыто: 15 · Отложено: 0

## Сессия 1 (2026-08-29)

| ID | Выбор | Решение | Затронутые § | Связанный Q |
|----|-------|---------|--------------|-------------|
| GAP-GOAL-01 | subtype | BPH subtype = `PORTFOLIO_SIZE_TAX` | §1.1, §1.2, §1.3, §4.1.1, §4.2.3 | Q-01 |
| GAP-GOAL-02 | comment | `comment`/`name` = «Налог за размер портфеля» | §1.1, §4.1.1, §4.2.3 | Q-05 |
| GAP-GOAL-03 | релиз | Time-bound = релиз 7.15.0 | §1.1 | — |
| GAP-UCAS-01 | subtype | `PORTFOLIO_SIZE_TAX` в alt-сценарии AS IS | §1.2 | Q-01 |
| GAP-UCTB-01 | operation_type | `tax` (id=2) | §1.3, §4.1.1, §4.2.3 | Q-03 |
| GAP-UCTB-02 | additionalType | `PORTFOLIO_AMOUNT_TAX` (одно непустое значение) | §1.3, §4.1.1, §4.2.3, §4.2.4 | Q-04 |
| GAP-UCTB-03 | watershed | `historyStart` из ответа BPH `GET_OPERATION_TYPES` | §1.3, §4.2.2, §5.4 | Q-08 |
| GAP-C-01 | family/bc/status | `TAXES` (type_id=7), `bc_id=NULL`, `COMPLETE` (id=19) | §2, §4.1.1, §4.2.3 | Q-02, Q-06, Q-07 |
| GAP-C-02 | watershed | `historyStart` из ответа BPH `GET_OPERATION_TYPES` | §2, §5.4 | Q-08 |
| GAP-INT-01 | additionalType | `PORTFOLIO_AMOUNT_TAX` в ответе BPH | §4.1.1 | Q-04 |
| GAP-ALG-01 | watershed | watershed по кэшу BPH `GET_OPERATION_TYPES` | §4.2.2 | Q-08 |
| GAP-DM-01 | INSERT-значения | subtype/op_type/bc_id/comment подтверждены (22/24/52/37) | §4.2.3 | Q-01, Q-03, Q-05, Q-06 |
| GAP-DM-02 | id строк | Паттерн MOEX_TAX: test 22/24/52/37; prod `SELECT max(id)+1` (черновик 25/27/79/57) | §4.2.3 | — |
| GAP-TEST-01 | тест | Dedicated integration test — добавить при apply | §4.2.4 | — |
| GAP-NFR-01 | watershed | `historyStart` из ответа BPH `GET_OPERATION_TYPES`, без ручной настройки HO | §5.4 | Q-08 |

## Отложено

| ID | Причина |
|----|---------|
| — | — |

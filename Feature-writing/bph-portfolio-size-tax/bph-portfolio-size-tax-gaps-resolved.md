---
report_type: gaps-resolved
slug: bph-portfolio-size-tax
source_document: Feature-writing/bph-portfolio-size-tax/bph-portfolio-size-tax.md
context_document: Feature-context/bph-portfolio-size-tax.md
generated_at: 2026-10-06
session: 2
---

# Карта закрытых gaps: bph-portfolio-size-tax

**Спецификация:** `Feature-writing/bph-portfolio-size-tax/bph-portfolio-size-tax.md`
**Карта:** `Feature-writing/bph-portfolio-size-tax/bph-portfolio-size-tax-gaps-resolved.md`

## Сводка
- Закрыто: 67

## Сессия 1 (2026-10-06)

| ID | Выбор | Решение | Затронутые § | Связанный Q |
|----|-------|---------|--------------|-------------|
| GAP-GOAL-03, GAP-UCAS-01, GAP-UCTB-01, GAP-CONS-01, GAP-INT-01, GAP-ALG-01, GAP-DM-01, GAP-MAP-01, GAP-OBS-01 | a | Написание подтипа — `PORTFOLIO_SIZE_TAX` | §1.1, §1.2, §1.3, §2, §4.1.1, §4.2.2, §4.2.3, §4.2.4, §5.3.1 | Q-01 |
| GAP-GOAL-04, GAP-UCTB-02, GAP-CONS-07, GAP-INT-02, GAP-ALG-02, GAP-DM-02, GAP-MAP-02 | b | `comment` для UI — «Налог за размер портфеля» | §1.1, §1.3, §2, §4.1.1, §4.2.2, §4.2.3, §4.2.4 | Q-02 |
| GAP-GOAL-05, GAP-UCTB-03, GAP-CONS-02, GAP-INT-03, GAP-ALG-03, GAP-DM-03, GAP-MAP-03 | a | `operation_type` = `tax` (id=2) | §1.1, §1.3, §2, §4.1.1, §4.2.2, §4.2.3, §4.2.4 | Q-03 |
| GAP-CONS-03, GAP-UCTB-05, GAP-ALG-04, GAP-DM-04, GAP-MAP-04, GAP-OBS-03 | a | `operation.bc_id` = `NULL` (BPH-only) | §2, §4.1.1, §4.2.2, §4.2.3, §4.2.4, §5.3.1, §5.3.2 | Q-04 |
| GAP-CONS-04, GAP-UCTB-06, GAP-INT-04, GAP-ALG-05, GAP-DM-05, GAP-MAP-05 | a | BPH-статус `COMPLETE` (id=19) + `status_to_operation(operation↔19)` | §2, §4.1.1, §4.2.2, §4.2.3, §4.2.4 | Q-05 |
| GAP-CONS-05, GAP-UCTB-04, GAP-INT-05, GAP-ALG-06, GAP-DM-06, GAP-MAP-06 | a | `info.additional_type` = `NULL` (одна info-строка) | §2, §4.1.1, §4.2.2, §4.2.3, §4.2.4 | Q-06 |
| GAP-GOAL-06, GAP-CONS-06, GAP-UCTB-07, GAP-ALG-07 | a | Порог «от 5 000 000 ₽» — BPH-side правило (CN-04), HO не фильтрует | §1.1, §1.3, §2, §4.2.2 | Q-07 |
| GAP-CONS-08, GAP-ALG-08, GAP-DM-08, GAP-MAP-08 | c | `operation.name` = «Налог за размер портфеля», `info.displayed_name` = NULL | §2, §4.2.2, §4.2.3, §4.2.4 | Q-09 |
| GAP-DM-07, GAP-MAP-07 | факт | id новых строк — sequence автоматически (INSERT без явного id), непересечение через pre-check (CN-06) | §4.2.3, §4.2.4 | — |

## Сессия 2 (2026-10-06)

| ID | Выбор | Решение | Затронутые § | Связанный Q |
|----|-------|---------|--------------|-------------|
| GAP-GOAL-01, GAP-GOAL-02, GAP-GOAL-07, GAP-OBS-02 | b | Non-SMART: полнота налоговой ленты через `history_ops_integration_total` + SQL-сверка + интеграционный тест; инициатор/тикет не критичны | §1.1, §5.3.2 | Q-08 |
| GAP-NFR-01, GAP-NFR-04 | b | Производительность и SLO/SLA наследуются без новых target'ов (CN-14) | §7.1.1–7.1.5, §7.2, §2 | — |
| GAP-UCAS-02, GAP-NFR-02, GAP-NFR-03, GAP-NFR-06, GAP-NFR-07 | b | Значения timeout/retry/deadline/page-size задаются внешним конфигом; partial failure без retry (CN-15) | §1.2, §7.1.3, §7.1.5, §7.2, §Конфигурация, §2 | — |
| GAP-NFR-05, GAP-NFR-09, GAP-OBS-04 | b | Аутентификация/хранение/маскирование — детали внешние (Vault/SOWA, `log_masking_rules.yml`); новые классы чувствительных данных не вводятся (CN-16) | §Безопасность, §5.3.1, §2 | — |
| GAP-NFR-08 | a | Отдельный toggle не вводится; раскатка data-driven (`bph.is_active` + кэш), лаг = `update-delay-ms` (CN-17) | §Тогглы, §2 | — |
| GAP-OBS-05 | a | Вне scope — новых UI-метрик нет | §5.3.2 | — |

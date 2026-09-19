---
report_type: challenges-resolved
slug: bph-coupons-dividends-monthly-summary
source_document: Feature-writing/bph-coupons-dividends-monthly-summary/bph-coupons-dividends-monthly-summary.md
challenges_document: Feature-writing/bph-coupons-dividends-monthly-summary/bph-coupons-dividends-monthly-summary-challenges.md
context_document: Feature-context/bph-coupons-dividends-monthly-summary.md
generated_at: 2026-09-16
session: 1
language: ru
---

# Карта закрытых вопросов: bph-coupons-dividends-monthly-summary

## Сводка
- Resolved: 19 · Covered: 2 · Needs-answer: 0 · Deferred: 0

## Сессия 1 (2026-09-16)

| ID | Verdict | Выбор | Решение | Затронутые § | Источник | Связанный Q |
|----|---------|-------|---------|--------------|----------|-------------|
| CH-01 | MISSING → resolved | A (D-17) | Окно UTC, полуинтервал `[start, start+1мес)`, `eventDate` в UTC | §4.1.1, §4.2.2.1 шаг 3 | выбор пользователя | — |
| CH-02 | MISSING → resolved | A (D-18) | `dateForFilter=EVENT_DATE` (обязательное) | §4.1.1 | выбор пользователя | Q-04 |
| CH-03 | MISSING → resolved | A (D-19) | Отдельный deadline `app-config.bph.monthlySummary.deadline` (1500–3000 мс) | §5.2 7.1.3, §4.2.2.1 шаг 4, §5.4 | выбор пользователя | — |
| CH-04 | MISSING → resolved | C (D-20) | Одна секция со сводной таблицей; screen-api разворачивает `data[]` | §4.1.1.2, §4.2.2.4 | выбор пользователя | Q-05 |
| CH-05 | MISSING → resolved | B (D-21) | null/пустые суммы → пустой агрегат → секция скрыта | §4.2.2.2 шаг 2, §4.2.2.4 шаг 3 | выбор пользователя | — |
| CH-06 | MISSING → resolved | A (D-22) | Дубликат валюты недопустим (контрактное требование BPH) | §4.1.1, маппинг «Validation и rejection» | выбор пользователя | — |
| CH-07 | MISSING → resolved | A (D-23) | Метрика только `SectionHidden` (без `SectionError`) | §5.3.2 | выбор пользователя | — |
| CH-10 | MISSING → resolved | A (D-24) | Сводка только при явном `periodFilter` календарного месяца, иначе скрыть | §4.2.2.1 шаг 2 | выбор пользователя | Q-04 |
| CH-11 | MISSING → resolved | C (D-25) | Без `maxItems`, риск размера тела задокументирован | §4.1.1 | выбор пользователя | — |
| CH-12 | MISSING → resolved | A (D-26) | Согласование access-политики (allow-list `systemName=history_ops`) — предусловие go-live | §5.1, §2 CN-07 | выбор пользователя | — |
| CH-14 | MISSING → resolved | A (D-27) | Единый `date-time` для `period.startDate`/`period.endDate` | §4.1.1 | выбор пользователя | — |
| CH-15 | MISSING → resolved | A (D-28) | Таблица приёмочных сценариев (Given/When/Then) | §5.3 | выбор пользователя | — |
| CH-13 | COVERED | — | `systemName=history_ops` уже зафиксирован (D-05) | §4.1.1, §2 CN-01 | spec | Q-10 |
| CH-18 | COVERED | — | HTTP 200 + `status.code≠0` = бизнес-ошибка (§4.2.2.2 шаг 1) | §4.1.1, §4.2.2.2 | spec | — |

## Needs-answer (батч 2, Minor) → закрыты в Сессии 2

| ID | D-XX | Severity | Тип | Статус в банке |
|----|------|----------|-----|----------------|
| CH-08 | D-29 | Minor | nfr-hole | resolved |
| CH-09 | D-30 | Minor | contract-edge | resolved |
| CH-16 | D-31 | Minor | scope-ambiguity | resolved |
| CH-17 | D-32 | Minor | corner-case | resolved |
| CH-19 | D-33 | Minor | corner-case | resolved |
| CH-20 | D-34 | Minor | nfr-hole | resolved |
| CH-21 | D-35 | Minor | data-edge | resolved |

## Сессия 2 (2026-09-16)

| ID | Verdict | Выбор | Решение | Затронутые § | Источник | Связанный Q |
|----|---------|-------|---------|--------------|----------|-------------|
| CH-08 | MISSING → resolved | A (D-29) | `enabled()` = `enableServiceBPH && enableBphCouponsDividendsMonthlySummary` (AND с `ENABLE_BPH`) | §2 CN-04, §4.1.1, §4.2.2.1 шаг 1, §5.5 | выбор пользователя | — |
| CH-09 | MISSING → resolved | A (D-30) | `types` обязательный (history-ops всегда передаёт 4 значения) | §4.1.1, §4.2.2.1 шаг 3 | выбор пользователя | — |
| CH-16 | MISSING → resolved | A (D-31) | Сводка всегда по всем инструментам клиента (не зависит от фильтра/таба ленты) | §4.1.1, §4.2.2.1 шаг 3 | выбор пользователя | — |
| CH-17 | MISSING → resolved | B (D-32) | Без дедупликации в запросе; контрактное требование BPH — один `data[]` на уникальный `isin` | §4.1.1, §4.2.2.1 шаг 3, маппинг «Validation и rejection» | выбор пользователя | — |
| CH-19 | MISSING → resolved | A (D-33) | Сверка ответа с запросом: отсутствующий `isin` → WARN + метрика `missing_isin`, источник failed, секция скрыта | §4.2.2.2 шаг 3, маппинг «Validation и rejection», §5.3.2 | выбор пользователя | — |
| CH-20 | MISSING → resolved | C (D-34) | Логировать число `isin` вместо полного списка (суммы без изменений) | §5.3.1 | выбор пользователя | — |
| CH-21 | MISSING → resolved | A (D-35) | Округление по minor units ISO-4217 (RUB 2, JPY 0, KWD 3), банковское | маппинг «Хоп 3» | выбор пользователя | — |

## Отложено

| ID | Причина |
|----|---------|
| — | — |

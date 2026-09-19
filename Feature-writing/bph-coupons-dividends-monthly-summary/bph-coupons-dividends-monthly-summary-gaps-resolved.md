---
report_type: gaps-resolved
slug: bph-coupons-dividends-monthly-summary
source_document: Feature-writing/bph-coupons-dividends-monthly-summary/bph-coupons-dividends-monthly-summary.md
context_document: Feature-context/bph-coupons-dividends-monthly-summary.md
generated_at: 2026-09-16
session: 5
---

# Карта закрытых gaps: bph-coupons-dividends-monthly-summary

**Спецификация:** `Feature-writing/bph-coupons-dividends-monthly-summary/bph-coupons-dividends-monthly-summary.md`
**Карта:** `Feature-writing/bph-coupons-dividends-monthly-summary/bph-coupons-dividends-monthly-summary-gaps-resolved.md`

## Сводка

| Метрика | Значение |
|---------|----------|
| Всего уникальных GAP в SPEC | 75 |
| Закрыто решениями пользователя (батч 1, сессия 2) | 30 |
| Закрыто решениями пользователя (батч 2, сессия 3) | 39 |
| Отложено (deferred, non-blocker) | 6 (GAP-NFR-05, GAP-NFR-08, GAP-NFR-10, GAP-NFR-11, GAP-NFR-13, GAP-DM-07) |
| Осталось открытыми к разрешению | 0 |

## Сессия 1 (2026-09-16)

Этап `needs-answer`: закрытий фактом нет — все гэпы батча 1 — подлинные
TO BE-решения по контракту новой ручки BPH (контракта в `bph.yml` нет, ручку
проектируем мы). Строки записаны в `DECISIONS`, spec **не** правился.

| Кластер | D-* | Relates (GAP-id) | Суть | Статус |
|---------|-----|------------------|------|--------|
| Q-01 контракт ручки | D-01 | GAP-GOAL-01, GAP-UCTB-01, GAP-INT-01, GAP-ALG-01, GAP-DM-01, GAP-MAP-01, GAP-NFR-01 | path/метод/имена схем | needs-answer |
| Q-02 объём агрегата | D-02 | GAP-GOAL-02, GAP-UCTB-02, GAP-INT-02, GAP-ALG-02, GAP-DM-02, GAP-MAP-02 | портфель vs инструмент, валюта, пустой результат | needs-answer |
| Q-03 состав типов | D-03 | GAP-GOAL-03, GAP-UCTB-03, GAP-INT-03, GAP-ALG-03, GAP-DM-03 | какие `CA_CASH_MOVEMENT` входят | needs-answer |
| Q-04 период | D-04 | GAP-GOAL-04, GAP-UCTB-04, GAP-INT-04, GAP-ALG-04, GAP-DM-04, GAP-MAP-06 | календарный месяц vs окно, дата, форма `period` | needs-answer |
| Q-10 systemName | D-05 | GAP-GOAL-07, GAP-UCTB-10, GAP-CONS-04, GAP-INT-06, GAP-ALG-10, GAP-NFR-03 | `si2-ops` vs `history_ops` | needs-answer |

## Сессия 2 (2026-09-16)

Применены решения батча 1 (D-01…D-05, статус `applied`). Переписаны §1.1
(цель), §1.3 (TO BE use cases + диаграмма), §2 (CN-01/CN-02), §4.1.1 (контракт
ручки), §4.2.2 (алгоритм), §4.2.3 (модель данных), маппинг, §5.1/§5.4 (NFR).
Закрытые GAP удалены из SPEC целиком.

| ID | Выбор | Решение | Затронутые § | Связанный Q |
|----|-------|---------|--------------|-------------|
| GAP-GOAL-01, GAP-UCTB-01, GAP-INT-01, GAP-ALG-01, GAP-DM-01, GAP-MAP-01, GAP-NFR-01 | a | Контракт `POST /api/v1/incoming-gateway/operations/coupons-dividends-monthly-summary`, схемы `RequestCouponsDividendsMonthlySummaryData`/`CouponsDividendsMonthlySummaryData` | §1.1, §1.3, §4.1.1, §4.2.2, §4.2.3, маппинг, §5.4 | Q-01 |
| GAP-GOAL-02, GAP-UCTB-02, GAP-INT-02, GAP-ALG-02, GAP-DM-02, GAP-MAP-02 | b | Агрегат по инструменту (`isin`), раздельно купоны/дивиденды, мультивалютный массив | §1.1, §1.3, §4.1.1, §4.2.2, §4.2.3, маппинг | Q-02 |
| GAP-GOAL-03, GAP-UCTB-03, GAP-INT-03, GAP-ALG-03, GAP-DM-03 | a | Только `coupon`/`coupon_output`/`dividend_input`/`dividend_output` | §1.1, §1.3, §4.1.1, §4.2.2, §4.2.3 | Q-03 |
| GAP-GOAL-04, GAP-UCTB-04, GAP-INT-04, GAP-ALG-04, GAP-DM-04, GAP-MAP-06 | a | Календарный месяц по `eventDate`, `period.startDate`/`period.endDate` | §1.1, §1.3, §4.1.1, §4.2.2, §4.2.3, маппинг | Q-04 |
| GAP-GOAL-07, GAP-UCTB-10, GAP-CONS-04, GAP-INT-06, GAP-ALG-10, GAP-NFR-03 | b | `systemName` = `history_ops` | §1.1, §1.3, §2, §4.1.1, §4.2.2, §5.1, §5.4 | Q-10 |

Батч 2 — закрытий фактом нет: оставшиеся 45 GAP — TO BE-решения
(секция/канал/флаг/UX) и prod-конфиг/SLO, требующие команд BPH/history-ops/
screen-api или владельца продукта. Записаны как `needs-answer` D-06…D-16.

## Сессия 3 (2026-09-16)

Применены решения батча 2 (D-06…D-16). Переписаны §1.1 (цель/SMART),
§1.3 (TO BE use cases + диаграмма), §2 (CN-03/CN-04/CN-05), §4.1.1/§4.1.1.1/
§4.1.1.2 (контракт/канал/секция), §4.2.2.1–4.2.2.4 (алгоритм), §4.2.3
(модель данных), маппинг (Хоп 1–3), §5.1/§5.2/§5.3.1/§5.3.2/§5.4/§5.5 (NFR).
Закрытые GAP удалены из SPEC целиком. GAP-NFR-05/08/10/11/13 (prod/SLO/Web
Vitals/раскатка) оставлены открытыми по решению D-13; GAP-DM-07 (DDL-типы)
отложен по решению D-15.

| ID | Выбор | Решение | Затронутые § | Связанный Q |
|----|-------|---------|--------------|-------------|
| GAP-UCTB-05, GAP-INT-07, GAP-ALG-05, GAP-DM-05, GAP-MAP-03 | a | Секция: `type`=`history.feed.couponsDividendsMonthlySummary`, `code`=`HISTORY_OPS_COUPONS_DIVIDENDS_MONTHLY_SUMMARY_SECTION`, `content.data`={period, couponTotals[], dividendTotals[], isin}; на ленте вверху, на карточке в «Истории» | §1.3, §4.1.1.2, §4.2.2.4, §4.2.3, маппинг Хоп 3 | Q-05 |
| GAP-UCTB-06, GAP-INT-08, GAP-ALG-06, GAP-NFR-09, GAP-UCAS-01, GAP-OBS-01 | b | Gateway: `eventType()`=`GET_COUPONS_DIVIDENDS_MONTHLY_SUMMARY`, `ruleKey()`=`bphGetCouponsDividendsMonthlySummary`, `exSystem()="BPH"`; не в RqCoordinator/пагинации, не кэшируется, запрашивается на каждой странице ленты | §1.3, §4.1.1, §4.2.2.1, §5.3.1, §5.3.2 | Q-06 |
| GAP-UCAS-02, GAP-UCTB-07, GAP-CONS-01, GAP-INT-09, GAP-ALG-07, GAP-MAP-05, GAP-NFR-07, GAP-OBS-02, GAP-OBS-05 | a | При недоступности/пустом: секция скрывается, лента не неполна (bcDataComplete/failOperationTypes не меняются), лог WARN | §2 CN-03, §4.2.2, §5.2-reliability, §5.3.1, §5.3.2 | Q-07 |
| GAP-UCTB-08, GAP-CONS-02, GAP-ALG-08, GAP-NFR-02 | a | Feature-флаг `enableBphCouponsDividendsMonthlySummary` (+ enum FeatureToggleName), default false | §2 CN-04, §5.4, §5.5 | Q-08 |
| GAP-UCTB-09, GAP-CONS-03, GAP-INT-05, GAP-ALG-09, GAP-DM-06, GAP-MAP-04, GAP-NFR-12, GAP-OBS-04 | a | Канал: расширение `OperationHistoryResponse` полем `couponsDividendsMonthlySummary` (агрегат целиком) | §2 CN-05, §4.1.1.1, §4.2.2.3, §4.2.3, маппинг Хоп 2, §5.5 | Q-09 |
| (residual D-02) | b | Лента: сводка по всем инструментам из соглашений клиента (запрос списком isin), секция = перечень инструментов с суммами | §1.3, §4.1.1, §4.2.2.1 | Q-11 |
| GAP-GOAL-05, GAP-GOAL-06 | b | Non-SMART: метрики/срок не заданы в брифе (улучшение UX) | §1.1 | — |
| GAP-INT-10, GAP-NFR-04, GAP-NFR-06 | a | test-default как AS IS: `deadline=50000ms`, без rate-limit/retry; auth scheme не объявлена (как у существующих) | §4.1.1, §5.1, §5.2 | — |
| GAP-OBS-03 | — | Не маскировать: правила маскирования для нового endpoint не добавляются | §5.1, §5.3.1 | — |
| GAP-MAP-07 | — | Округление на бэке композита; для некомпозитного фронта функционал не добавляется | маппинг Хоп 1/Хоп 3 | — |

## Отложено

| ID | Причина |
|----|---------|
| GAP-NFR-05 | D-13 (applied): test-default как AS IS; prod-значения `app-config.bph.deadline`/`url`/`cacheRefreshMs` — оставлены GAP для эксплуатации |
| GAP-NFR-08 | D-13 (applied): целевые perf-метрики (p85 / RPS штатный и пиковый / CCU / поведение при перегрузке) — оставлены GAP для эксплуатации / нагрузочного тестирования |
| GAP-NFR-10 | D-13 (applied): SLO (availability / error rate) новой ручки — оставлены GAP для эксплуатации / SRE |
| GAP-NFR-11 | D-13 (applied): Web Vitals (LCP/FID/CLS/TTI) новой секции — оставлены GAP для эксплуатации / фронтенд-бюджета |
| GAP-NFR-13 | D-13 (applied): даты создания/удаления флага, сроки раскатки, согласование изменений — оставлены GAP для эксплуатации / релиз-плана |
| GAP-DM-07 | D-15 (deferred): отложено — справочники фичей не меняются, точные DDL-типы не blocker |

## Сессия 4 (2026-09-16)

Применены 12 точечных правок SPEC из решений по challenge-вопросам (D-17…D-28,
статус `applied` в `DECISIONS`). Это не закрытие GAP-маркеров, а устранение
противоречий/edge-сценариев, зафиксированных в `CHALLENGES` (CH-01…CH-07,
CH-10…CH-15). Открытых GAP-маркеров эта сессия не закрывала и новых не создавала.

| ID (D-*) | CH | Суть правки | Затронутые § SPEC |
|-----------|----|-------------|-------------------|
| D-17 | CH-01 | Таймзона окна — UTC, `eventDate` в UTC; включение — полуинтервал `[start, start+1мес)` (без `<= end`) | §4.1.1 (параметры/пример запроса), §4.2.2.1 шаг 3 |
| D-18 | CH-02 | Обязательное поле `dateForFilter=EVENT_DATE` (`FilterDateEnum`) в запросе | §4.1.1 (параметры, ENUM, пример запроса), §4.2.2.1 шаг 3 |
| D-19 | CH-03 | Отдельный меньший deadline `app-config.bph.monthlySummary.deadline` (1500–3000 мс) | §4.1.1 (Timeout), §4.2.2.1 шаг 4, §5.2 (7.1.3, нагрузка), §5.4 |
| D-20 | CH-04 | На ленте — одна секция со сводной таблицей (screen-api разворачивает `data[]`); скалярный `isin` — только для карточки | §4.1.1.2, §4.2.2.4, маппинг Хоп 3 |
| D-21 | CH-05 | Пустой агрегат (`data:[]` либо все элементы с null/пустыми массивами) → скрыть секцию | §4.2.2.2 шаг 2, §4.2.2.4 шаг 3, маппинг Validation |
| D-22 | CH-06 | Дубликат валюты в `couponTotals`/`dividendTotals` недопустим — контрактное требование BPH | §4.1.1 (структура ответа), маппинг Validation |
| D-23 | CH-07 | Метрика только `SectionHidden` (без `SectionError`) | §5.3.2 (фронтовые метрики) |
| D-24 | CH-10 | Сводка только при явном `periodFilter` календарного месяца; иначе секция скрыта | §4.2.2.1 шаг 2, §4.2.2.4 шаг 3 |
| D-25 | CH-11 | Без `maxItems` для `isin` — риск задокументирован | §4.1.1 (параметры/примечание), §4.2.2.1 шаг 3 |
| D-26 | CH-12 | Согласование с BPH (allow-list `systemName=history_ops`) — предусловие go-live | §2 (CN-07), §5.1 (авторизация) |
| D-27 | CH-14 | Единый `date-time` для `period.startDate`/`period.endDate` | §4.1.1 (структура ответа, пример), §4.2.3 (модель данных) |
| D-28 | CH-15 | Таблица приёмочных сценариев (Given/When/Then) | §5.3 (новая подсекция «Приёмочные сценарии») |

### Deferred GAP — состояние без изменений

Шесть открытых GAP-маркеров оставлены в SPEC как есть (скилл `resolve-gaps`
предписывает не трогать SPEC для отложенных gaps; фиксация — только в этой карте):

| ID | Источник | Причина |
|----|----------|---------|
| GAP-NFR-05 | D-13 (applied) | prod-значения `app-config.bph.deadline`/`url`/`cacheRefreshMs` — GAP для эксплуатации |
| GAP-NFR-08 | D-13 (applied) | целевые perf-метрики (p85/RPS/CCU) — GAP для эксплуатации / нагрузочного тестирования |
| GAP-NFR-10 | D-13 (applied) | SLO (availability / error rate) — GAP для эксплуатации / SRE |
| GAP-NFR-11 | D-13 (applied) | Web Vitals (LCP/FID/CLS/TTI) — GAP для эксплуатации / фронтенд-бюджета |
| GAP-NFR-13 | D-13 (applied) | даты создания/удаления флага, сроки раскатки — GAP для эксплуатации / релиз-плана |
| GAP-DM-07 | D-15 (deferred) | точные DDL-типы справочников — не blocker (справочники фичей не меняются) |

## Сессия 5 (2026-09-16)

Техническая пометка статуса (не закрытие фактом). В SPEC в строках таблиц гэпов
шести отложенных гэпов проставлен маркер «отложено» в колонке «Как закрыть» —
чтобы маршрутизатор пайплайна (`open_gaps` в `routing_conditions.yaml`) не считал
их открытыми и не зацикливал шаг `/resolve-gaps`. Решения D-13/D-15, формулировки
гэпов и значения **не** менялись; гэпы оставлены в SPEC видимыми для ручной проверки.

| ID | Маркер в SPEC | Источник решения |
|----|---------------|------------------|
| GAP-NFR-05 | `(отложено — D-13)` | D-13 (applied) |
| GAP-NFR-08 | `(отложено — D-13)` | D-13 (applied) |
| GAP-NFR-10 | `(отложено — D-13)` | D-13 (applied) |
| GAP-NFR-11 | `(отложено — D-13)` | D-13 (applied) |
| GAP-NFR-13 | `(отложено — D-13)` | D-13 (applied) |
| GAP-DM-07 | `(отложено — D-15)` | D-15 (deferred) |

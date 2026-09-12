---
report_type: gaps-resolved
slug: bph-coupons-dividends-monthly-summary
source_document: Feature-writing/bph-coupons-dividends-monthly-summary/bph-coupons-dividends-monthly-summary.md
context_document: Feature-context/bph-coupons-dividends-monthly-summary.md
generated_at: 2026-08-30
session: 1
---

# Карта закрытых gaps: bph-coupons-dividends-monthly-summary

**Спецификация:** `Feature-writing/bph-coupons-dividends-monthly-summary/bph-coupons-dividends-monthly-summary.md`
**Карта:** `Feature-writing/bph-coupons-dividends-monthly-summary/bph-coupons-dividends-monthly-summary-gaps-resolved.md`

## Сводка
- Закрыто: 76 · Отложено: 0

## Сессия 1 (2026-08-30)

Все открытые `[GAP-...]` закрыты решением пользователя через AskQuestion (2 батча: контракты/UC/BR → goal/NFR/prod-defaults). Отложенных нет.

### Проектные решения Q-01…Q-11 (контракт и use case)

| ID | Выбор | Решение | Затронутые § | Связанный Q |
|----|-------|---------|--------------|-------------|
| GAP-UCTB-01, GAP-INT-01, GAP-ALG-01, GAP-MAP-01, GAP-OBS-01, GAP-CONS-01 | Зафиксировать как в черновике | `POST /api/v1/incoming-gateway/operations/coupons-dividends-monthly-summary`; `eventType=GET_COUPONS_DIVIDENDS_MONTHLY_SUMMARY`; RPC-ключ `bphGetCouponsDividendsMonthlySummary` | §1.3 (предусловия, шаг 5.4, изменения, seq-диаграмма), §2, §4.1.1, §4.1.1.1, §4.2.2, маппинг, §5.3 | Q-01 |
| GAP-UCTB-02, GAP-INT-02, GAP-ALG-02, GAP-MAP-02 | Один объект: купоны/дивиденды/итог | `data` = один объект `{period, totalCouponsSum, totalDividendsSum, totalCouponsDividendsSum}`, без разбивки по договорам/инструментам | §1.3, §4.1.1, §4.2.2, маппинг | Q-02 |
| GAP-UCTB-03, GAP-INT-03, GAP-ALG-03, GAP-MAP-03 | Календарный месяц через start/endSearchDate | Период задаётся `startSearchDate`/`endSearchDate`; в ответе `period="YYYY-MM"` | §1.3, §4.1.1, §4.2.2, маппинг | Q-03 |
| GAP-UCTB-04, GAP-INT-04, GAP-ALG-04, GAP-MAP-04 | Разбивка по валютам | Каждая сумма — список `PriceData[]` (по одному элементу на валюту); секция отображает мультивалютно | §1.3, §4.1.1, §4.2.2, маппинг | Q-04 |
| GAP-UCTB-05, GAP-INT-05, GAP-ALG-05, GAP-NFR-09, GAP-OBS-03, GAP-CONS-03 | feedRequestsDynamic + глобальный toggle | Заводится `feedRequestsDynamic` с ключом `bphGetCouponsDividendsMonthlySummary` + `FeatureToggleName.enableBphCouponsDividendsMonthlySummary` | §1.3 (предусловия), §2, §4.1.1.1, §4.2.2, §5.4, §5.5, §5.3.1 | Q-05 |
| GAP-UCTB-06, GAP-INT-06, GAP-ALG-06, GAP-MAP-06 | Новый не-operation SectionCreator | Тип секции `history.feed.couponsDividendsSummary` (`SectionCreatorType`), по образцу `TitleSectionCreator`; позиция `order=0` | §1.3, §2, §4.1.1.2, §4.2.2, маппинг | Q-06 |
| GAP-UCTB-07, GAP-INT-07, GAP-ALG-07, GAP-MAP-05 | Новое поле в OperationHistoryResponse | Поле `couponsDividendsMonthlySummary` в `history.yml` (`OperationHistoryResponse`) | §1.3, §2, §4.1.1.2, §4.2.2, маппинг | Q-07 |
| GAP-UCTB-08, GAP-INT-08, GAP-ALG-08, GAP-MAP-09, GAP-NFR-08, GAP-OBS-04, GAP-OBS-05, GAP-CONS-04 | Скрыть секцию, не трогать bcDataComplete | При пустом/нулевом ответе и при сбое секция скрывается; ручка не влияет на `bcDataComplete`/`failOperationTypes`; метрика `summary_empty` | §1.3, §2, §4.1.1, §4.2.2, маппинг, §7.1.4, §7.2, §5.3.2 | Q-08 |
| GAP-UCTB-09, GAP-INT-09, GAP-ALG-09, GAP-MAP-07, GAP-CONS-05 | Тот же запрос + instrumentId | Один endpoint; на карточке инструмента передаётся `instrumentId`, на ленте — без фильтра | §1.3, §2, §4.1.1, §4.1.1.2, §4.2.2, маппинг | Q-09 |
| GAP-UCTB-10, GAP-INT-10, GAP-ALG-10 | Не входит в лимит 100 и SourcesInfo | Сводная секция не операция: не учитывается в лимите 100 и в `SourcesInfo`/пагинации | §1.3, §4.1.1.1, §4.2.2 | Q-10 |
| GAP-UCTB-11, GAP-INT-11, GAP-ALG-11, GAP-MAP-10 | Независимые данные BPH | Сводная сумма — независимый расчёт на стороне BPH, не вычисляется из операций `CA_CASH_MOVEMENT` ленты | §1.3, §4.1.1.1, §4.2.2, маппинг | Q-11 |

### Цель, метрики и AS IS

| ID | Выбор | Решение | Затронутые § | Связанный Q |
|----|-------|---------|--------------|-------------|
| GAP-GOAL-01, GAP-GOAL-02 | Не указано в брифе | Инициатор/дата постановки не указаны в брифе (зафиксировано допущением) | §1.1 | — |
| GAP-GOAL-03, GAP-GOAL-04, GAP-OBS-07 | non-SMART/не определён | «Улучшение UX без количественной метрики»; срок/релиз не задан на этапе проектирования | §1.1, §1.3 (преимущества), §5.3.2 | — |
| GAP-UCAS-01, GAP-UCAS-02, GAP-UCAS-03 | Не оценивается | Частота/стоимость/приоритет проблемы AS IS — «Не оценивается» | §1.2 | — |
| GAP-UCAS-04 | Подтвердить допущение | Источники OG/DCA/ECM/DCM сгруппированы в один участник диаграммы (примечание в §1.2) | §1.2 | — |

### NFR, prod-defaults и прочее

| ID | Выбор | Решение | Затронутые § | Связанный Q |
|----|-------|---------|--------------|-------------|
| GAP-INT-12, GAP-NFR-01, GAP-NFR-02, GAP-OBS-02 | Наследовать BphClient | Auth без отдельной security scheme (как `bph.yml`); timeout/retry/rate-limit наследуют `BphClient`; суммы маскируются в логах | §4.1.1, §5.1, §7.1.3, §7.1.5, §7.1.6, §5.3.1 | — |
| GAP-NFR-03, GAP-NFR-05, GAP-NFR-07, GAP-OBS-06 | Не заданы на этапе проектирования | p85/SLA/RPS/CCU/SLO и параметры БД BPH определяются после load-теста | §7.1.1–7.1.3, §7.1.5, §7.1.6, §7.2, §5.3.2 | — |
| GAP-NFR-04 | Не меняются относительно AS IS | Web-vitals (LCP/FID/CLS/TTI) не меняются | §7.1.4 | — |
| GAP-NFR-06 | Не кэшировать | Кэширование сводной суммы не предусмотрено | §7.1.7 | — |
| GAP-NFR-10 | Toggle default=false; ключи true/false | Toggle `false` по умолчанию; `app-config-dynamic` ключи active/inactive=true; валидация boolean | §5.4, §5.5 | — |
| GAP-MAP-08 | Сгенерированный DTO из bph.yml | Поле сводки типизируется сгенерированным DTO из OpenAPI | маппинг §4.2.2 | — |
| GAP-OBS-08 | Оставить проектируемыми | Имена фронтовых событий — проектируемые, вне контура history-ops | §5.3.2 | — |

## Отложено

| ID | Причина |
|----|---------|
| — | Отложенных нет — все открытые gaps закрыты решением пользователя |

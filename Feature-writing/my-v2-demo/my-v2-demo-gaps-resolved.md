---
report_type: gaps-resolved
slug: my-v2-demo
source_document: Feature-writing/my-v2-demo/my-v2-demo.md
context_document: Feature-context/my-v2-demo.md
generated_at: 2026-09-25
session: 2
---

# Карта закрытых gaps: my-v2-demo

**Спецификация:** `Feature-writing/my-v2-demo/my-v2-demo.md`
**Карта:** `Feature-writing/my-v2-demo/my-v2-demo-gaps-resolved.md`

## Сводка
- Закрыто: 56

## Сессия 1 (2026-09-25)

### D-01 — контракт BPH monthly summary (Q-01)

| ID | Выбор | Решение | Затронутые § | Связанный Q |
|----|-------|---------|--------------|-------------|
| GAP-UCAS-01 | A | Состав источников ленты AS IS зафиксирован: `GET_LINKED_EVENTS` + `GET_OPERATIONS_WITH_DETAILS` (носитель `CA_CASH_MOVEMENT`) | §1.2 Sequence Diagram (AS IS) | Q-01 |
| GAP-UCAS-03 | A | Пустая лента → пустое состояние (принято как есть) | §1.2 Use Case (AS IS) | Q-01 |
| GAP-UCTB-01 | A | Endpoint `POST /api/v1/incoming-gateway/operations/monthly-summary` | §1.3 (диаграмма TO BE) | Q-01 |
| GAP-UCTB-06 | A | Пустой месяц → нулевые суммы (bucket `0`) | §1.3 Use Case (TO BE) | Q-01 |
| GAP-CONS-01 | A | Имя/path/форма request/response зафиксированы | §2 (gaps) | Q-01 |
| GAP-INT-01 | A | Endpoint сигнатура зафиксирована | §4.1.1 | Q-01 |
| GAP-INT-02 | A | Request `RequestMonthlySummaryData` (период + `agreements`) | §4.1.1 | Q-01 |
| GAP-INT-03 | A | Response `MonthlySummaryData` (`total` + разбивка) | §4.1.1 | Q-01 |
| GAP-INT-06 | A | Пустой результат → нулевые суммы (bucket `0`) | §4.1.1 | Q-01 |
| GAP-ALG-01 | A | Имя/path ручки зафиксировано | §4.2.2 | Q-01 |
| GAP-ALG-06 | A | Пустой месяц → нулевые суммы (bucket `0`) | §4.2.2 | Q-01 |
| GAP-DM-03 | A | Форма `MonthlySummary` зафиксирована | §4.2.3 | Q-01 |
| GAP-MAP-01 | A | Имена полей `MonthlySummaryData` зафиксированы | §4.2.4 | Q-01 |
| GAP-NFR-04 | A | Новый ключ конфига в `BphProperties` (URL/pageSize) | §5 (Конфигурация) | Q-01 |
| GAP-OBS-01 | A | `eventType = GET_MONTHLY_SUMMARY` | §5 (Логирование, Метрики) | Q-01 |
| GAP-OBS-02 | A | Маскирование сумм по `LoggerConstants.HIDDEN_TEXT` | §5 (Логирование) | Q-01 |

### D-02 — systemName (Q-04)

| ID | Выбор | Решение | Затронутые § | Связанный Q |
|----|-------|---------|--------------|-------------|
| GAP-CONS-02 | A | `systemName = history_ops` | §2 (CN-05) | Q-04 |
| GAP-INT-04 | A | `systemName = history_ops` (код `BphClient`) | §4.1.1 | Q-04 |

### D-03 — поведение при недоступности (Q-05)

| ID | Выбор | Решение | Затронутые § | Связанный Q |
|----|-------|---------|--------------|-------------|
| GAP-UCAS-02 | A | Частичная лента — существующий механизм `bcDataComplete`/`failOperationTypes` | §1.2 | Q-05 |
| GAP-UCTB-04 | A | Секция скрывается целиком; не влияет на полноту ленты | §1.3 | Q-05 |
| GAP-CONS-03 | A | Скрытие секции целиком; лента/КД без изменений | §2 (CN-12) | Q-05 |
| GAP-INT-07 | A | Дедлайн `app-config.bph.deadline`; без retry; скрытие секции | §4.1.1 | Q-05 |
| GAP-ALG-04 | A | Скрытие секции; не влияет на `bcDataComplete`/`failOperationTypes` | §4.2.2 | Q-05 |
| GAP-NFR-02 | A | Дедлайн применяется; отдельного retry нет | §5 (Производительность) | Q-05 |
| GAP-NFR-03 | A | Graceful Degradation: скрытие секции | §5 (Надёжность) | Q-05 |
| GAP-MAP-05 | A | Пустой месяц → нули; partial failure → скрытие | §4.2.4 | Q-05 |
| GAP-OBS-06 | A | Отдельный счётчик не вводится; `dataCompleteFalse` не применим | §5 (Метрики) | Q-05 |

### D-04 — карточка инструмента (Q-03)

| ID | Выбор | Решение | Затронутые § | Связанный Q |
|----|-------|---------|--------------|-------------|
| GAP-UCTB-03 | A | Сводка по `instrumentFilter` (isin/ticker), только по выбранному инструменту | §1.3 | Q-03 |
| GAP-CONS-06 | A | `instrumentFilter` (`agreements` = isin/ticker); отличается от ленты | §2 (CN-10) | Q-03 |
| GAP-ALG-03 | A | Карточка инструмента — по `instrumentFilter` | §4.2.2 | Q-03 |
| GAP-MAP-04 | A | Карточка инструмента — по `instrumentFilter` | §4.2.4 | Q-03 |

### D-05 — валюта и округление (Q-07)

| ID | Выбор | Решение | Затронутые § | Связанный Q |
|----|-------|---------|--------------|-------------|
| GAP-GOAL-05 | B | Отдельные суммы по RUB/USD/SUR без пересчёта; округление до 2 знаков | §1.1 (gaps) | Q-07 |
| GAP-UCTB-05 | B | Отдельные суммы по валютам; decimal, 2 знака | §1.3 | Q-07 |
| GAP-CONS-05 | B | Без пересчёта; decimal; округление 2 знака | §2 (CN-11) | Q-07 |
| GAP-INT-05 | B | `value` decimal; `CurrencyEnum` RUB/USD/SUR | §4.1.1 | Q-07 |
| GAP-ALG-05 | B | Сумма сводки — отдельные суммы по валютам | §4.2.2 | Q-07 |
| GAP-DM-01 | B | `value` decimal, 2 знака; `currency` RUB/USD/SUR | §4.2.3 | Q-07 |
| GAP-MAP-02 | B | Валюты RUB/USD/SUR; без пересчёта | §4.2.4 | Q-07 |
| GAP-OBS-04 | B | Бизнес-метрика — суммы по валютам (Gauge) | §5 (Метрики) | Q-07 |

## Сессия 2 (2026-09-25)

### D-06 — код/тип секции композита и способ рендеринга (Q-02)

| ID | Выбор | Решение | Затронутые § | Связанный Q |
|----|-------|---------|--------------|-------------|
| GAP-UCTB-02 | A | Код секции `history.feed.monthlySummary`; транзитный рендер (без новой строки в `section`/`content`/`screen_section` БД screen-api) | §1.3 Use Case (TO BE) | Q-02 |
| GAP-ALG-02 | A | Код секции `history.feed.monthlySummary`; транзитный рендер | §4.2.2 (Шаг 8) | Q-02 |
| GAP-DM-02 | A | Новая секция рендерится транзитно — постоянной строки в `section`/`content`/`screen_section` screen-api не создаётся | §4.2.3 (Область изменения) | Q-02 |
| GAP-MAP-03 | A | Код секции `history.feed.monthlySummary`; транзитный рендер | §4.2.4 (Field mapping) | Q-02 |
| GAP-OBS-05 | A | Отдельные UI-события секции не вводятся — показ покрывается существующими UI-метриками ленты/карточки | §5 (Метрики — фронтовые) | Q-02 |
| GAP-OBS-07 | A | Секция-специфичная метрика не вводится — покрывается `operations_feed_requests_*` | §5 (Метрики — технические) | Q-02 |

### D-07 — имя и default фича-тогла (Q-06)

| ID | Выбор | Решение | Затронутые § | Связанный Q |
|----|-------|---------|--------------|-------------|
| GAP-CONS-04 | A | Фича-тогл `enable_monthly_summary`, default `false` (OFF) | §2 (CN-09) | Q-06 |
| GAP-ALG-07 | A | Фича-тогл `enable_monthly_summary`, default `false` (OFF) | §4.2.2 (Шаг 3) | Q-06 |
| GAP-MAP-06 | A | Фича-тогл `enable_monthly_summary`, default `false` (OFF) | §4.2.4 | Q-06 |
| GAP-NFR-05 | A | Имя `enable_monthly_summary`, default `false` (OFF); владелец — history-ops / history-ops-screen-api; даты/стратегия/план удаления не заданы (определяются при раскатке) | §5 (Тогглы, Конфигурация) | Q-06 |

### D-08 — количественные NFR/SLO, RL/CB, prod-поля лога (Q-08)

| ID | Выбор | Решение | Затронутые § | Связанный Q |
|----|-------|---------|--------------|-------------|
| GAP-NFR-01 | B | Количественные NFR/SLO не задаются — секция аддитивна, класс запроса не меняется (допущение CN-13) | §5 (5.2.1–5.2.7, Надёжность) | Q-08 |
| GAP-NFR-06 | B | Rate Limiting/Throttling/Circuit Breaker не задаются (допущение CN-13) | §5 (5.2.5) | Q-08 |
| GAP-OBS-03 | B | Поля лога `service`/`environment` не фиксируются — prod-конфиг вне репозитория (допущение CN-13) | §5 (Логирование) | Q-08 |

### D-09 — метаданные цели (Q-09)

| ID | Выбор | Решение | Затронутые § | Связанный Q |
|----|-------|---------|--------------|-------------|
| GAP-GOAL-01 | C | Инициатор — Product Owner истории операций | §1.1 (Источник требования) | Q-09 |
| GAP-GOAL-02 | C | Дата — 2026-09-25 (дата брифа) | §1.1 (Источник требования) | Q-09 |
| GAP-GOAL-03 | C | Метрики улучшения не заданы (допущение CN-14) | §1.1 (Цель, SMART-Measurable) | Q-09 |
| GAP-GOAL-04 | C | Срок/релиз не задан (допущение CN-14) | §1.1 (SMART-Time-bound) | Q-09 |

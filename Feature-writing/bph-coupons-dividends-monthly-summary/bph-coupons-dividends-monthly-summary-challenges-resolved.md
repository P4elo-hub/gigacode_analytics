---
report_type: challenges-resolved
slug: bph-coupons-dividends-monthly-summary
source_document: Feature-writing/bph-coupons-dividends-monthly-summary/bph-coupons-dividends-monthly-summary.md
challenges_document: Feature-writing/bph-coupons-dividends-monthly-summary/bph-coupons-dividends-monthly-summary-challenges.md
context_document: Feature-context/bph-coupons-dividends-monthly-summary.md
generated_at: 2026-08-30
session: 1
language: ru
---

# Карта закрытых вопросов: bph-coupons-dividends-monthly-summary

## Сводка
- Resolved: 20 · Covered: 1 · Deferred: 0
- Open осталось: 0

## Сессия 1 (2026-08-30)

| ID | Verdict | Выбор | Решение | Затронутые § | Источник | Связанный Q |
|----|---------|-------|---------|--------------|----------|-------------|
| CH-01 | MISSING → resolved | «Месяц из periodFilter ленты» | Месяц сводки = месяц `periodFilter` ленты (если включён и задан), иначе — текущий календарный месяц; `order=0` — секция в начале ленты, не привязана к пагинации/скроллу | §4.1.1, §4.2.2 шаг 4 | выбор пользователя | Q-03 |
| CH-02 | PARTIAL → resolved | «Сводка независима» (согласовано: CH-03 побеждает) | Сводка показывается независимо от `bcDataComplete`; сбой прочих источников её не скрывает; скрывается только при сбое/пустом ответе самой ручки сводки [BR-07] | §4.2.2 alt 8a.2, §1.1 BR-07, §1.3 alt 8a | выбор пользователя | Q-08 |
| CH-03 | MISSING → resolved | «Сводку показывать» | Пара «операции купонов/дивидендов не загрузились + сводка есть»: сводка показывается, pop-up показывается независимо [BR-07] | §1.3 alt 8a, §4.2.2 alt 8a, §1.1 BR-07 | выбор пользователя | Q-08 |
| CH-04 | MISSING → resolved | «Сверка не требуется» | Сводка — независимый агрегат BPH; сверка с карточками операций не выполняется, расхождение допустимо [BR-08] | §1.1 BR-08, §1.3/§4.2.2 BR-таблицы | выбор пользователя | Q-11 |
| CH-05 | MISSING → resolved | «Сводку показывать» | Пустая лента + непустая сводка: заглушка «перейти на Рынок» подавляется, сводка показывается | §1.3 alt 8d | выбор пользователя | — |
| CH-06 | MISSING → resolved | «Сумма по инструменту» | `instrumentId` сужает агрегат до одного инструмента (целевой UX); `agreements` — перечень договоров, `instrumentId` — доп. фильтр | §4.1.1 «Условия обязательности», §4.2.2 шаг 4 | выбор пользователя | Q-09 |
| CH-07 | MISSING → resolved | «Опциональны + дефолт месяц» | Даты опциональны; если опущены — BPH возвращает сводку за текущий календарный месяц | §4.1.1 (условия обязательности, примечание) | выбор пользователя | Q-03 |
| CH-08 | MISSING → resolved | «Серверная таймзона history-ops» | Границы месяца вычисляются в серверной таймзоне (Europe/Moscow), передаются как UTC-инстанты; BPH считает `period` по инстантам [CN-13] | §2 CN-13, §4.1.1, §4.2.2 шаг 4.2 | выбор пользователя; код `BphConverter.printLocalDateTimeAtZeroTimeZone` | — |
| CH-09 | PARTIAL → resolved | «onErrorResume → пустая сводка» | Новый Mono изолируется `onErrorResume` → пустая сводка, по образцу `AbstractOperationGateway.getOperationsSafe()`; ошибка не всплывает в `Mono.zip` | §4.1.1.1, §4.2.2 шаг 5b | выбор пользователя; код `AbstractOperationGateway.java:98-103` | Q-08 |
| CH-10 | MISSING → resolved | «Инвариант как требование к BPH» | Инвариант `totalCouponsDividendsSum == totalCouponsSum + totalDividendsSum` (по валютам) — контрактное требование к BPH; history-ops без арифметики/валидации [BR-10] | §1.1 BR-10, §4.1.1, маппинг | выбор пользователя | — |
| CH-11 | MISSING → resolved | «period по startSearchDate» | Нет ограничения «один месяц»; если диапазон пересекает месяцы — `period` соответствует месяцу `startSearchDate` | §4.1.1 | выбор пользователя | — |
| CH-12 | MISSING → resolved | «Дополнить коды» | Добавлены 401/403/404/429; при 429 history-ops не ретраит, скрывает секцию | §4.1.1 коды ошибок | выбор пользователя | — |
| CH-13 | MISSING → resolved | «Как пусто» | 200 + `data: null` трактуется как пустой результат (секция скрывается, INFO), не ошибка | §4.1.1 (примечание) | выбор пользователя | — |
| CH-14 | MISSING → resolved | «agreements — опциональный фильтр» | `agreements` не обязателен: не передан/пуст → сводка по всем договорам клиента; передан → только указанные [CN-14] | §2 CN-14, §4.1.1, JSON Schema (`required: []`) | выбор пользователя | — |
| CH-15 | MISSING → resolved | «Версионирование» | Контракт секций версионируется: старый клиент получает ответ без новой секции `history.feed.couponsDividendsSummary` [CN-06] | §2 CN-06, §5.5 Совместимость | выбор пользователя | — |
| CH-16 | MISSING → resolved | «Только зачисления» | В агрегат входят только зачисления (положительные суммы); списания/налог не включаются [BR-09] | §1.1 BR-09, §4.1.1, маппинг | выбор пользователя | — |
| CH-17 | COVERED | «Наследовать BphClient» | Отдельный таймаут не вводится; уже было в spec («наследует BphClient»); добавлена уточняющая формулировка про задержку ленты | §7.1.3 (уточнение) | spec (уже было) | — |
| CH-18 | MISSING → resolved | «Toggle — мастер» | Матрица: toggle OFF → нет запроса; ON + нет ключа `feedRequestsDynamic` → лента как AS IS; карточка — через `instrumentFilterRequestsDynamic` | §5.5 Feature Toggles | выбор пользователя | Q-05 |
| CH-19 | PARTIAL → resolved | «Отдельный gateway» | Отдельный gateway, не extends `AbstractOperationGateway`; только `enabled()` + `onErrorResume`; operation-фильтры не применяются | §4.1.1.1, §4.2.2 шаг 3 | выбор пользователя; код `AbstractOperationGateway.getOperations()` | — |
| CH-20 | PARTIAL → resolved | «Принять сырое логирование» | Требование маскирования снято; суммы логируются в сыром виде как у остальных интеграций (`IntegrationLogService.toJson()` без redaction) | §5.1, §5.3.1 | выбор пользователя; код `IntegrationLogService.java:301-310` | — |
| CH-21 | MISSING → resolved | «Добавить критерии приёмки» | Добавлена таблица критериев приёмки под ключевые edge-кейсы | §5.5 Критерии приёмки | выбор пользователя | — |

## Отложено

| ID | Причина |
|----|---------|
| — | — |

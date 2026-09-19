---
report_type: challenges-resolved
slug: bph-linked-events-yield
source_document: Feature-writing/bph-linked-events-yield/bph-linked-events-yield.md
challenges_document: Feature-writing/bph-linked-events-yield/bph-linked-events-yield-challenges.md
context_document: Feature-context/bph-linked-events-yield.md
generated_at: 2026-09-20
session: 2
language: ru
---

# Карта закрытых вопросов: bph-linked-events-yield

## Сводка
- Resolved: 10 · Covered: 4 · Deferred: 0 · Needs-answer: 0

## Сессия 1 (2026-09-20)

| ID | Verdict | Выбор | Решение | Затронутые § | Источник | Связанный Q |
|----|---------|-------|---------|--------------|----------|-------------|
| CH-02 | COVERED | — | `getOperationsFeed` возвращает `GetOperationsFeedResponse` с `operations_details: repeated GetDetailsResponse`, поэтому `yield` присутствует и в ленте, и в деталке (транспорт); отображение — только в деталке (D-04). Правка §1.3 шаг 10 + примечание §4.1.1.2 | §1.3, §4.1.1.2 | `repositories/.../proto/historyOperationDetails.proto`; D-04; CN-11 | — |
| CH-07 | COVERED | — | Ключ слияния OG↔BPH — `exchange_order_id`; источники отбираются по владельцу (`RequestLinkedData.agreements` / `ucpId`), слияние в рамках execution-процесса клиента. Добавлен CN-13 | §2 (CN-13) | `repositories/.../merger/OrderMerger.java`; OG CN-14 | — |
| CH-09 | COVERED | — | Устранена остаточная неоднозначность: источник `yield` — только `OperationData` (lead), не `details[]` (D-05). Правка §4.1.1.1 (note) + §4.2.3 (Source row) | §4.1.1.1, §4.2.3 | DECISIONS D-05 | — |
| CH-10 | COVERED | — | «Отсутствие значения» в OG включает пустой `value` (CN-08/D-08): при пустом `yield.value` доходность считается отсутствующей и дозаполняется из BPH. Уточнён CN-09 | §2 (CN-09) | DECISIONS D-08; CN-08; BR-08 | — |

## Сессия 2 (2026-09-20)

| ID | Verdict | Выбор | Решение | Затронутые § | Источник | Связанный Q |
|----|---------|-------|---------|--------------|----------|-------------|
| CH-01 | MISSING → resolved | a | Инлайн `message PriceData` в `historyOperationDetails.proto` — канонический владелец типа; симметричная OG-спека приводится к инлайну (без импорта/дублирования) | §2 CN-06, §4.1.1.2 | выбор пользователя (DECISIONS D-13) | — |
| CH-03 | MISSING → resolved | b | Защищённое чтение (JsonNode/try-catch): структурное несоответствие даёт `null` поля, заявка и источник BPH не отбрасываются | §4.1.1.1, §4.1.1 (ошибки), §4.2.2 alt 5a, §4.2.3 | выбор пользователя (DECISIONS D-14) | — |
| CH-04 | MISSING → resolved | a | Passthrough без валидации `value` (`{value:"abc"}` → «abc RUB»); структурные случаи — по D-14 | §4.1.1.1, §4.2.3 | выбор пользователя (DECISIONS D-15) | — |
| CH-05 | MISSING → resolved | b | Фича-тогл BPH-ветки доходности — уже отражён как CN-14 (D-10, kill-switch); дублирующее ограничение не создаётся | §2 CN-14 | выбор пользователя (DECISIONS D-16) | — |
| CH-06 | MISSING → resolved | a | WARN-лог существующей схемы + метрика `history_ops_integration` (`comment=parse_error`, `ex_system=BPH`, `event_type=GET_LINKED_EVENTS`) — CN-15 | §2 CN-15, §4.1.1 (ошибки), §4.2.2 alt 5a, §4.2.3 | выбор пользователя (DECISIONS D-17) | — |
| CH-08 | MISSING → resolved | a | lead-only без fallback + acceptance-критерий верификации места поля до приёмки | §4.1.1.1 | выбор пользователя (DECISIONS D-18) | — |
| CH-11 | MISSING → resolved | a | Passthrough без сверки валюты (`{value} {currency}` из `PriceData`) | §4.1.1.4, §4.2.3 | выбор пользователя (DECISIONS D-19) | — |
| CH-12 | MISSING → resolved | b | 2 знака после запятой + правило округления (арифметическое, half-up) — CN-18 | §2 CN-18, §4.1.1.4, §4.2.3 | выбор пользователя (DECISIONS D-20) | — |
| CH-13 | MISSING → resolved | a | Out of scope: доходность только для `GET_LINKED_EVENTS`; для `GET_OPERATION_WITH_DETAILS` не пробрасывается — CN-16 | §2 CN-16, BR-02 | выбор пользователя (DECISIONS D-21) | — |
| CH-14 | MISSING → resolved | a | REST-поле `HistoryOperationLead.yield` оставлено (симметрия с OG D-02) — CN-17 | §2 CN-17, §4.1.1.3 | выбор пользователя (DECISIONS D-22) | — |

## Отложено

| ID | Причина |
|----|---------|
| — | — |

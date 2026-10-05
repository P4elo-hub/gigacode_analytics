---
report_type: challenges-resolved
slug: bph-moex-tax
source_document: Feature-writing/bph-moex-tax/bph-moex-tax.md
challenges_document: Feature-writing/bph-moex-tax/bph-moex-tax-challenges.md
context_document: Feature-context/bph-moex-tax.md
generated_at: 2026-10-05
session: 1
language: ru
---

# Карта закрытых вопросов: bph-moex-tax

## Сводка
- Covered (фактом, spec поправлен/подтверждён): 5
- Deferred: 1 (CH-17 → D-12)
- Needs-answer (ожидают решения пользователя): 13

## Сессия 1 (2026-10-05)

| ID | Verdict | Выбор | Решение | Затронутые § | Источник | Связанный Q |
|----|---------|-------|---------|--------------|----------|-------------|
| CH-05 | COVERED (факт) | — | `currency` берётся из `lead.totalPrice.currency` (`PriceData.currency` → `CurrencyEnum`), верхнего поля `currency` в `OperationData` нет; spec-маппинг исправлен | §4.2.4 | код `BphOperationConverter` → `BphCommonWrapper.currency` | — |
| CH-06 | COVERED (факт) | — | HO читает оба имени подтипа (сначала `subtype`, затем `subType`); разрешённое значение используется как `bphType` и в ключе lookup `operation`; spec уточнён | §4.1.1 | код `BphOperationConverter.getSubType()` | — |
| CH-07 | COVERED (факт) | — | HO не ветвится по `status.code`; элементы `data` конвертируются по отдельности (`parse_error` не роняет остальные); `dataCompleteFalse` — только при HTTP-ошибке/исключении; spec §4.1.1/§5.3.2 исправлен | §4.1.1, §5.3.2 | код `ListRequestService`, `AbstractOperationGateway.getOperationsSafe`, `RequestService` | — |
| CH-12 | COVERED (факт) | — | `totalSum ← abs(totalPrice)` — универсальное поведение `BphCommonClientConverter.convert()` (без изменений), идентично существующему `TAX_RETAIN` (тоже удержание с отрицательным `totalPrice`) | §4.2.4 | код `BphCommonClientConverter.convert()` | — |
| CH-16 | COVERED (факт) | — | Статус риска уточнён: «resolved как допущение (D-01); pre-check против контракта BPH остаётся Blocking (yes) до пролива» — остаточный silent-no-op риск не маскируется | §4.3 | spec + D-01 + pre-check §4.3 | Q-01 |

## Отложено

| ID | Причина |
|----|---------|
| CH-17 | Полевый перечень маскирования для `GET_OPERATIONS_WITH_DETAILS` уже отложен (D-12, `log_masking_rules.yml`); маскирование — по правилу endpoint-уровня, покрывающему и `MOEX_TAX` |

## Ожидают решения пользователя (needs-answer)

| ID | Severity | Decision | Суть вопроса |
|----|----------|----------|--------------|
| CH-01 | Critical | D-13 | `MOEX_TAX` визуально тождествен `TAX_RETAIN` (comment=name=type); «другой comment» из брифа не выполнен — осознанно ли? |
| CH-04 | Critical | D-14 | Blast radius: подтверждено ли, что BPH игнорирует неизвестный `subtype=MOEX_TAX` в `subtypesAndStatuses`, а не отвечает 400/500? |
| CH-15 | Critical | D-15 | Observability: чем подтверждается в проде, что фича работает (метрика/алерт или non-SMART)? |
| CH-02 | Major | D-16 | Authoritative значения `name`/`comment` vs sibling `bph-portfolio-size-tax` (CH-09) |
| CH-03 | Major | D-17 | Дедупликация по `externalSystemId` / уникальность — кто гарантирует? |
| CH-08 | Major | D-18 | Требование «`info.additional_type` именно NULL, не `''`» + валидация |
| CH-09 | Major | D-19 | Заголовок карточки/деталки при `displayed_name=NULL` (fallback на `operation.name`?) |
| CH-10 | Major | D-20 | Стратегия назначения id новых строк (SERIAL авто vs явные id) |
| CH-11 | Major | D-21 | Налог без коммента (additionalType не сматчен + пустой `accComment`) — допустимо? |
| CH-14 | Major | D-22 | Детекция рассинхрона БД↔кэш при сбое cron-обновления |
| CH-18 | Major | D-23 | Обязательные негативные тест-кейсы/фикстуры |
| CH-13 | Minor | D-24 | UNIQUE на `bph.subtype` или pre-check достаточно? |
| CH-19 | Minor | D-25 | End-to-end критерий приёмки (SEND_OPERATIONS содержит MOEX_TAX) |

## Сессия 2 (2026-10-05)

Применены 13 решений пользователя (D-13…D-25, статус `applied`). Все 13 CH из «needs-answer» закрыты как `resolved`.

| ID | Verdict | Выбор | Решение | Затронутые § | Источник | Связанный Q |
|----|---------|-------|---------|--------------|----------|-------------|
| CH-01 | MISSING → resolved | A (D-13) | `MOEX_TAX` осознанно визуально неотличим от `TAX_RETAIN` (comment=name=type=tax) — зафиксировано CN-11 | §2 (CN-11), §4.2.4 | выбор пользователя | Q-02, Q-06 |
| CH-04 | MISSING → resolved | A (D-14) | BPH игнорирует нераспознанный `subtype`/`type` (договорённость с BPH) — CN-12 + пограничный случай §4.1.1 + pre-check §4.3 | §2 (CN-12), §4.1.1, §4.3 | выбор пользователя | Q-01 |
| CH-15 | MISSING → resolved | B (D-15) | Non-SMART: полнота через `history_ops_integration_total` + SQL-сверка + интеграционный тест | §1.1 (Measurable), §5.3.2 | выбор пользователя | — |
| CH-02 | MISSING → resolved | A (D-16) | Эта spec authoritative (`name`/`comment` = «Удержание суммы налога») — CN-13, sibling выровнять | §2 (CN-13) | выбор пользователя | Q-02, Q-06 |
| CH-03 | MISSING → resolved | A (D-17) | Дедупликация по `id` через Ignite-кэш (постранично), уникальность `externalSystemId` — BPH — BR-11 + §4.2.4 | §1.3 (BR-11), §4.2.4 | выбор пользователя | — |
| CH-08 | MISSING → resolved | A (D-18) | Pre-check «`info.additional_type IS NULL` (не `''`)» без DDL | §4.2.3, §4.3 | выбор пользователя | Q-03 |
| CH-09 | MISSING → resolved | A (D-19) | Fallback на `operation.name` при `displayed_name=NULL` (заголовок тождествен `TAX_RETAIN`) | §4.2.4 | выбор пользователя | Q-06 |
| CH-10 | MISSING → resolved | A (D-20) | SERIAL/sequence авто id (INSERT без явного id) — коллизий нет | §2 (CN-06), §4.2.3, §4.3 | выбор пользователя | — |
| CH-11 | MISSING → resolved | A (D-21) | `info.comment` всегда задан — сценарий «налог без текста» не возникает, деградация допустима | §4.2.4 | выбор пользователя | Q-02 |
| CH-14 | MISSING → resolved | B (D-22) | INFO-лог успешного обновления кэша (cron каждый час) + операционная процедура; рассинхрон допустим | §5.3.1 | выбор пользователя | Q-08 |
| CH-18 | MISSING → resolved | B (D-23) | Негативные тесты вне scope (data-only: позитивный integration-тест + SQL-валидация) | §4.3 | выбор пользователя | — |
| CH-13 | MISSING → resolved | B (D-24) | Оставить pre-check «0 строк», UNIQUE на `bph.subtype` не добавлять (data-only) | §4.2.3, §4.3 | выбор пользователя | — |
| CH-19 | MISSING → resolved | B (D-25) | Data-level приёмка (SQL + кэш-shape), согласуется с non-SMART D-07 | §1.1, §4.3 | выбор пользователя | — |

### Итог сессии 2
- Resolved: 13 · Covered (сессия 1, без изменений): 5 · Deferred: 1 (CH-17)
- Open в банке: 0

# resolve-gaps — reference

## Разрешение входа

| Ввод пользователя | Результат |
|-------------------|-----------|
| `og-trading-order-yield` | `Feature-writing/og-trading-order-yield/og-trading-order-yield.md` |
| путь к `SPEC` | slug из имени папки |
| `og-trading-order-yield GAP-INT-05 Q-04` | slug + фокус на указанные id |

---

## Признаки открытого vs закрытого gap

| Состояние | В spec | В `*-gaps-resolved.md` |
|-----------|--------|------------------------|
| **Открыт** | `[GAP-...]`, строка `Gap` / `Допущение` в таблице | — |
| **Закрыт** | следов нет: § переписан, строка и маркер удалены | строка в карте сессии |
| **Отложен** | gap остаётся как был | строка «отложено» (опционально) |
| **Legacy** | строки `Закрыт`, `## Журнал закрытия gaps` | мигрировать в карту и удалить из spec |

---

## Связь GAP ↔ Q ↔ §

1. Собери все `GAP-*` regex: `\[?GAP-[A-Z0-9-]+\]?`
2. Для каждого GAP найди § (заголовок `###` / `####` выше строки).
3. В строке gap или inline ищи `(Q-\d+)`.
4. Открой Q в `Feature-context/<slug>.md` → таблица «Открытые вопросы».
5. Сформируй prompt: **вопрос Q** + перечень GAP кластера + текущее допущение в spec.

---

## Кластеризация (обязательно)

**Единица работы = кластер**, не отдельный `GAP-*`.

| Шаг | Действие |
|-----|----------|
| 1 | Уникальные `GAP-*` из `SPEC` |
| 2 | Для каждого GAP — `Q-XX` (inline, «см. Q-01», context-doc по смыслу) |
| 3 | Группировка: один `Q-XX` → список всех GAP-id |
| 4 | Orphan GAP без Q — объединить по **одной теме** (имя поля, контракт, формат UI) |
| 5 | Одна строка `DECISIONS` на кластер; Relates = `GAP-a, GAP-b, …, Q-01` |

Пример Relates для Q-01 (контракт BPH `precalc_commission`):

`GAP-GOAL-04, GAP-INT-01, GAP-UCB-08, GAP-CN-04, GAP-MAP-02, Q-01`

После apply одного Decision — правятся **все** §, где встречаются GAP кластера.

**Фаза needs-answer:** только `CONTEXT_DOC`, sibling-spec, `analytics/`.
`repositories/` — только на apply, если Decision требует code anchor.

---

## Шаблоны вариантов по типу gap

### Имя / тип поля (Q-01, Q-05, GAP-GOAL-03)

| Вариант | Пример label |
|---------|--------------|
| A | Зафиксировать имя `yield`, тип `google.type.Decimal` → §4.1.1, history.yml |
| B | Имя `profitability`, тип percent → §4.1.1 |
| C | Отложить; оставить `<поле доходности>` и GAP |
| Other | … |

### Уровень контракта (Q-04, GAP-INT-05, GAP-MAP-01)

| Вариант | Пример label |
|---------|--------------|
| A | `ReportOrderOperationDetails` (как облигационные поля OG) |
| B | `HistoryOperationLead` (как в bph-linked-events-yield) |
| C | Отложить; CN-03 остаётся |
| Other | … |

### Поведение / merge (Q-08, GAP-UCTB-01)

| Вариант | Пример label |
|---------|--------------|
| A | Не обогащать из BPH — приоритет ОГ, доходность только из ОГ |
| B | Обогащать из BPH, если в ОГ поле пустое |
| C | Отложить |
| Other | … |

### Scope (Q-07, GAP-UCTB-04)

| Вариант | Пример label |
|---------|--------------|
| A | Только `GetTradeOrders`; активные заявки вне scope |
| B | Включить `GetActiveOrders` / ActiveOrder |
| C | Отложить |
| Other | … |

### Параметр запроса (Q-03, GAP-INT-03)

| Вариант | Пример label |
|---------|--------------|
| A | Поле приходит безусловно; параметра запроса нет |
| B | Новый параметр в `GetTradeOrdersRequest` (уточнить имя) |
| C | Отложить |
| Other | … |

### NFR / prod (GAP-NFR-01…)

| Вариант | Пример label |
|---------|--------------|
| A | Зафиксировать test-default как AS IS; prod — GAP для эксплуатации |
| B | Принять допущение «prod = test» с пометкой риска |
| C | Отложить |
| Other | … |

### SMART / метрики (GAP-GOAL-01/02)

| Вариант | Пример label |
|---------|--------------|
| A | Конкретная метрика / релиз (пользователь укажет в Other) |
| B | «Улучшение UX без количественной метрики» — закрыть как non-SMART |
| C | Отложить |
| Other | … |

---

## Правила правки feature-doc

### Закрытый gap — переписать §, удалить следы

**Было** (таблица gaps + inline):

```markdown
| `yield` (новое) | `<поле доходности>` в `ReportOrderOperationDetails` | ... | [GAP-MAP-01] — уровень (Q-04) |

**Gaps и допущения:**
| GAP-MAP-01 | Gap | Не утверждён уровень | Q-04 | Согласовать |
```

**Стало** (после выбора «yield в HistoryOperationLead»):

```markdown
| `yield` (новое) | `HistoryOperationLead.yield` (PriceData) | Прямой перенос | Если поле в ответе ОГ |
```

Блок `**Gaps и допущения:**` с `GAP-MAP-01` — **удалён целиком** (если других строк нет).

### Подтверждённое допущение

**Было:**

```markdown
| Доходность — транзитное поле | Допущение | Не персистится в БД | GAP-CONS-01 |
```

**Стало** в §2 (обычный текст):

```markdown
| CN-07 | Ограничение | Доходность — транзитное поле ответа; отдельная колонка в БД не создаётся |
```

Строка `GAP-CONS-01` из таблицы gaps — **удалена**.

### Use case / TO BE

Обновлять шаги и alt-сценарии только если ответ меняет поведение. Убирать ссылки
на Q/GAP в тексте шагов — оставлять только зафиксированное поведение.

### Consistency checklist

- [ ] В spec нет `[GAP-...]` для закрытых id
- [ ] Нет пустых или legacy-блоков `**Gaps и допущения:**` / `## Журнал закрытия gaps`
- [ ] BR/CN согласованы с изменённым §
- [ ] Sibling-spec — без новых конфликтов
- [ ] Карта `GAPS_MAP` содержит все закрытые id текущей сессии
- [ ] Закрытые `Q-XX` дописаны в `CONTEXT_DOC` § «Закрытые вопросы»

---

## Выходной файл: карта закрытых gaps

| Параметр | Значение |
|----------|----------|
| Путь | `GAPS_MAP` = `Feature-writing/<slug>/<slug>-gaps-resolved.md` |
| Парный документ | `SPEC` = `Feature-writing/<slug>/<slug>.md` |
| В spec | **ничего** из карты не дублировать |
| Повторный прогон | append секции `## Сессия N` |
| Диалог | краткая сводка + пути к обоим файлам |

### Шаблон (первый прогон)

```markdown
---
report_type: gaps-resolved
slug: <slug>
source_document: Feature-writing/<slug>/<slug>.md
context_document: Feature-context/<slug>.md
generated_at: <YYYY-MM-DD>
session: 1
---

# Карта закрытых gaps: <slug>

**Спецификация:** `Feature-writing/<slug>/<slug>.md`
**Карта:** `Feature-writing/<slug>/<slug>-gaps-resolved.md`

## Сводка
- Закрыто: N · Отложено: N

## Сессия 1 (<YYYY-MM-DD>)

| ID | Выбор | Решение | Затронутые § | Связанный Q |
|----|-------|---------|--------------|-------------|
| GAP-INT-05 | a | Доходность в `HistoryOperationLead.yield` (PriceData) | §4.1.1, §4.2.3, маппинг | Q-04 |

## Отложено

| ID | Причина |
|----|---------|
| GAP-NFR-03 | Пользователь выбрал «отложить» |
```

### Повторный прогон

Append в конец файла новую секцию `## Сессия 2 (<date>)` с таблицей новых закрытий.
Обновить frontmatter `session` и счётчики в `## Сводка`.

---

## resolve-gaps vs resolve-code-alignment

| | `/resolve-gaps` | `/resolve-code-alignment` |
|---|-----------------|---------------------------|
| Вход | `SPEC` | `ALIGNMENT` |
| Источник gaps | `[GAP-...]`, Q в spec/context | Findings alignment (MISMATCH, PARTIAL, …) |
| Когда | После write/check-feature; в любой момент | После `/check-feature-code` |
| Next step | `/check-feature`, при необходимости code-alignment | `/check-feature-code` (обязательно) |

Оба скилла пишут варианты в `DECISIONS`; оркестратор спрашивает; обратная
запись закрытых Q — в `CONTEXT_DOC`. `/resolve-gaps` пишет `GAPS_MAP`;
`/resolve-code-alignment` — опциональный log в `ALIGNMENT`.

---

## Лимит батча needs-answer в DECISIONS

| Gaps | Действие |
|------|----------|
| ≤ 15 | все кластеры → `needs-answer` → `ASK_PARENT` → стоп |
| > 15 | батч 1: blocker-кластеры (контракт, UC, BR); записать → **стоп**; батч 2+ после apply |

Не смешивать батчи: после записи needs-answer для батча 1 **не** начинать apply и
**не** готовить батч 2 в том же вызове.

# resolve-challenges — reference

## Разрешение входа

| Ввод | Результат |
|------|-----------|
| `og-trading-order-yield` | `CHALLENGES` + `SPEC` в `Feature-writing/og-trading-order-yield/` |
| путь к `CHALLENGES` | slug из frontmatter или имени папки |
| `og-trading-order-yield CH-03 CH-07` | slug + фокус |

---

## Статусы в `CHALLENGES`

| Статус | Кто ставит | Смысл |
|--------|------------|-------|
| `open` | challenge-feature | ждёт resolve-challenges |
| `needs-answer`, `answered` | legacy / ошибка | трактовать как `open` |
| `covered` | resolve-challenges | SPEC однозначно отвечает |
| `resolved` | resolve-challenges | после `applied` Decision пользователя |
| `deferred` | resolve-challenges | отложено (Minor/backlog или выбор «Отложить») |

❌ `answered` / `resolved` без `applied` в DECISIONS — антипаттерн.

---

## Вердикт покрытия → действие

| Verdict | Spec | DECISIONS | Правка spec |
|---------|------|-----------|-------------|
| COVERED | однозначный ответ + § | нет | не менять (Critical/Major — только при цитате) |
| PARTIAL | намёк, двусмысленность | `needs-answer` → ASK_PARENT | после Decision |
| MISSING | нет | `needs-answer` → ASK_PARENT | после Decision |

---

## Шаблоны options для DECISIONS

### Corner case / missing-flow

| Вариант | Label (пример) |
|---------|----------------|
| a | Зафиксировать alt-сценарий X в §1.3 — поведение Y |
| b | Явный out of scope + текущее поведение без изменений |
| c | Отложить (deferred) |

### Contradiction

| a | Привести spec к BR-XX (уточнить CN) |
| b | Изменить BR-XX под поведение из кода |
| c | Отложить |

### NFR / toggle

| a | Описать деградацию при OFF в §5.5 |
| b | Silent skip — зафиксировать в use case |
| c | Отложить |

### Найдено в analytics/code

| a | Вписать поведение в §X (источник: path) |
| b | Spec верна — только статус covered |
| c | Отложить |

---

## Выходной файл: `-challenges-resolved.md`

```markdown
---
report_type: challenges-resolved
slug: <slug>
source_document: Feature-writing/<slug>/<slug>.md
challenges_document: Feature-writing/<slug>/<slug>-challenges.md
context_document: Feature-context/<slug>.md
generated_at: <YYYY-MM-DD>
session: 1
language: ru
---

# Карта закрытых вопросов: <slug>

## Сводка
- Resolved: N · Covered: N · Deferred: N

## Сессия 1 (<YYYY-MM-DD>)

| ID | Verdict | Выбор | Решение | Затронутые § | Источник | Связанный Q |
|----|---------|-------|---------|--------------|----------|-------------|
| CH-03 | MISSING → resolved | a | Alt 4b: при timeout ОГ заявка без yield | §1.3 | выбор пользователя | Q-08 |
| CH-07 | COVERED | — | Уже в BR-05 | §1.1 | spec | — |

## Отложено

| ID | Причина |
|----|---------|
| CH-12 | Пользователь: отложить |
```

---

## Обновление `CHALLENGES`

Менять **только** колонку `Статус`. Строки не удалять.

---

## resolve-challenges vs resolve-gaps vs resolve-code-alignment

| | Вход | Что закрывает | Карта |
|---|------|---------------|-------|
| `/resolve-gaps` | `SPEC` `[GAP-...]` | неverified facts | `GAPS_MAP` |
| `/resolve-code-alignment` | `ALIGNMENT` | MISMATCH vs код | optional log в `ALIGNMENT` |
| `/resolve-challenges` | `CHALLENGES` | adversarial CH-* | `CHALLENGES_MAP` |

Все три дописывают закрытые `Q-XX` в `CONTEXT_DOC` § «Закрытые вопросы».

---

## Consistency checklist

- [ ] Нет `[CH-...]` в `SPEC`
- [ ] Alt-сценарии согласованы с BR/CN
- [ ] Статусы CH обновлены
- [ ] Карта сессии полная
- [ ] Закрытые `Q-XX` дописаны в `CONTEXT_DOC`
- [ ] `ALIGNMENT` помечен как устаревший, если правки затронули контракты/БД

---

## Лимит needs-answer в DECISIONS

| Open CH | Действие |
|---------|----------|
| ≤ 15 | один батч |
| > 15 | батч 1: Critical+Major; батч 2: Minor |

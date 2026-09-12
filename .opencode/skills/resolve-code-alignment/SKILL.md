---
name: resolve-code-alignment
description: >-
  Closes open gaps from the code-alignment report by asking the user multiple-choice
  questions, then patching the feature specification and back-filling closed Q-XX into
  the context doc. Use after /check-feature-code when verdict is FAIL or PASS WITH GAPS
  and the spec needs user decisions before the next alignment pass.
disable-model-invocation: true
---

# resolve-code-alignment

Интерактивное закрытие **документируемых** gaps из `ALIGNMENT`:
вопросы с вариантами → ответы пользователя → правки `SPEC`.

Пути и токены: правило `artifact-paths`.

## Pipeline

```
/check-feature-code → /resolve-code-alignment → /check-feature-code → …
                 ↘ (PASS WITH GAPS / PASS) spec ready
```

| | Путь |
|---|------|
| **Вход** | `ALIGNMENT` = `Feature-writing/<slug>/<slug>-code-alignment.md` |
| **Правим** | `SPEC` = `Feature-writing/<slug>/<slug>.md` + `CONTEXT_DOC` (§ закрытых Q) |
| **Не трогаем** | `repositories/`, `ALIGNMENT` (кроме optional Resolution log append) |

Детали: [reference.md](reference.md).

---

## Шаг 0. Разрешить slug

1. Аргумент: `<slug>` **или** путь к `ALIGNMENT`.
2. Нет `ALIGNMENT` → стоп: сначала `/check-feature-code`.
3. Нет `SPEC` → стоп: сначала `/write-feature`.

---

## Шаг 1. Извлечь closable gaps

Прочитай `ALIGNMENT` целиком. Дополнительно — таблицы `[GAP-...]` / Q в `SPEC`,
**только** если на них ссылается alignment (Recommended actions, findings).

### Включать в опрос (closable)

| Источник | Когда |
|----------|--------|
| Finding `MISMATCH` | Любая severity (Critical/Major — приоритет) |
| Finding `PARTIAL` | Нужна правка формулировки spec |
| Finding `UNVERIFIABLE` | Можно закрыть решением/допущением пользователя |
| Recommended actions | Пункты про уточнение spec (не про код) |
| `Q*` / `GAP-*` | Открыты в doc и упомянуты в alignment |

### Исключать (не спрашивать)

| Источник | Почему |
|----------|--------|
| `CONFIRMED` | Уже ок |
| `NOT FOUND` (TO BE) | Ожидаемо до реализации в dev; не закрывается ответом в чате |
| Findings только про отсутствие test/Liquibase/fixtures в коде | TO BE implementation |

Если **closable gaps = 0**:
- кратко: «вопросов к пользователю нет»;
- verdict **PASS WITH GAPS** / **PASS** → spec ready;
- **стоп** (не править файлы).

---

## Шаг 2. Опрос пользователя (AskQuestion)

**Обязательно** вызови **`AskQuestion`** — выбор в UI Cursor.

На каждый closable gap — один question:

| Поле | Содержание |
|------|------------|
| `id` | finding id или `q2`, `gap-c01` |
| `prompt` | Вопрос + 1 строка контекста из alignment |
| `options` | 2–4 варианта; id = `a`, `b`, `c`; label = смысл + куда правим spec |

Правила:
1. Минимум 2 варианта; «Other» Cursor добавит сам.
2. Вариант «отложить / Q остаётся открытым» — если уместно.
3. Не предлагать правки `repositories/` (это разработка вне этого workspace).
4. Critical/Major — первыми в массиве.
5. Все gaps — **один** батч `AskQuestion`.

**Не правь** feature-doc до получения ответов.

Fallback (если AskQuestion недоступен): markdown R-1…R-n, ждать ответы в чате.

---

## Шаг 3. Применить ответы

1. Точечные правки `SPEC` по ответам — **переписывать §**, а не помечать «закрыто».
2. Закрытый gap → строку из таблицы гэпов удалить, inline `[GAP-...]` снять
   (принцип «чистая spec», как в `/resolve-gaps`).
3. PARTIAL/MISMATCH → формулировка под evidence из alignment.
4. Не выдумывай новые BR; не удаляй незакрытые Q без ответа.
5. Отложенные — перечисли в summary.

Опционально append в `ALIGNMENT`:

```markdown
## Журнал решений (<YYYY-MM-DD>)
| ID | Выбор | Правки |
|----|-------|--------|
| I-08 | a | §4.2.2.2 алгоритм |
```

Не меняй frontmatter `verdict` — обновит следующий `/check-feature-code`.

### Обратная запись в `CONTEXT_DOC`

Закрыт gap, связанный с `Q-XX` → допиши строку в `CONTEXT_DOC`
§ `## Закрытые вопросы` (создай секцию, если нет; «Открытые вопросы» не чистить):

```markdown
| Q-09 | 2026-08-28 | Транзитное поле, PG-колонка не требуется | §4.2.3 | /resolve-code-alignment (D-01) |
```

Затем:

```bash
python3 scripts/refresh_context.py <slug>
```

---

## Шаг 4. Ответ и перепроверка

- сколько закрыто / отложено / TO BE skipped;
- изменённые файлы: `SPEC`, при обратной записи — `CONTEXT_DOC`;
- **Next:** `/check-feature-code <slug>` — **обязательно** (закрывает петлю).

| Ситуация | Дополнительно |
|----------|---------------|
| Правки затронули BR/CN или use case | сначала `/check-feature <slug>` |
| `CHALLENGES` существует и spec изменён | stale банка — информационно; next → `/check-feature-code` |
| `alignment_iteration` уже 3 | не запускать 4-й прогон: ручной разбор + `/feature-status` |

## Антипаттерны

- ❌ Править `SPEC` до ответов пользователя
- ❌ Спрашивать про NOT FOUND (TO BE) как «вопросы на PASS»
- ❌ Оставлять строки «закрыт» в таблицах гэпов вместо удаления
- ❌ Менять код в `repositories/`
- ❌ Закрывать Q без явного ответа
- ❌ Дублировать опрос текстом вместо AskQuestion

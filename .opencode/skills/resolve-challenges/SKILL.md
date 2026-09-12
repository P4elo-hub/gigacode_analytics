---
name: resolve-challenges
description: >-
  Walks the challenges bank against the feature spec: marks covered vs missing items,
  reuses or writes DECISIONS for unresolved cases, searches context/analytics/code
  when possible, then patches the spec. Writes the resolution map to
  <slug>-challenges-resolved.md and back-fills closed Q-XX into the context doc.
  Invoke after /challenge-feature.
user-invocable: false
---

# resolve-challenges

Закрытие **критических вопросов** (`CH-*`) из банка `CHALLENGES`:
анализ `SPEC` → поиск ответа в базах и `DECISIONS` → правка `SPEC`.
Карта решений — в `CHALLENGES_MAP`; `SPEC` остаётся без `[CH-...]`.

Пути и токены: правило `artifact-paths`.

## Pipeline

```
/challenge-feature → /resolve-challenges → /check-feature → /check-feature-code
```

| | Путь |
|---|------|
| **Вход** | `CHALLENGES` = `Feature-writing/<slug>/<slug>-challenges.md` |
| **Spec** | `SPEC` = `Feature-writing/<slug>/<slug>.md` |
| **Контекст** | `CONTEXT_DOC`, `DECISIONS`, `analytics/`, `repositories/`, sibling-spec |
| **Правим** | `SPEC` (§) + статусы в `CHALLENGES` + `CONTEXT_DOC` (§ закрытых Q) |
| **Выход (карта)** | `CHALLENGES_MAP` = `Feature-writing/<slug>/<slug>-challenges-resolved.md` |
| **Не трогаем** | код в `repositories/` |

Детали: [reference.md](reference.md).

---

## Шаг 0. Разрешить slug

1. Аргумент: `<slug>`, путь к `SPEC` или к `CHALLENGES`.
2. Нет `CHALLENGES` → стоп: сначала `/challenge-feature`.
3. Нет `SPEC` → стоп: `/write-feature`.
4. Опциональный **фокус** — только указанные `CH-NN`.

---

## Шаг 1. Загрузить банк вопросов

Прочитай `CHALLENGES` и `SPEC` целиком.

| Статус в банке | Действие |
|----------------|----------|
| `open` | обрабатывать |
| `needs-answer`, `answered` | **legacy** — трактовать как `open` (не закрыты) |
| `deferred` | только если пользователь явно просил переоткрыть |
| `covered`, `resolved` | пропустить (уже закрыты) |

Если **необработанных = 0** → сообщи «все вопросы закрыты» и **стоп**.

---

## Шаг 2. Анализ: spec vs каждый CH-*

Для каждого открытого `CH-NN` определи **покрытие**:

| Вердикт | Значение | Действие |
|---------|----------|----------|
| **COVERED** | Spec **однозначно** отвечает (есть цитата §) | Статус → `covered`; в карту — § + формулировка; spec **не менять** |
| **PARTIAL** | Есть намёк, но не однозначно | → `needs-answer` в `DECISIONS` (не `answered` в банке) |
| **MISSING** | В spec нет ответа | → `needs-answer` в `DECISIONS` |

**COVERED только если:** можно указать § и однозначную формулировку без
домыслов. Для **Critical/Major** при малейшем сомнении — **PARTIAL/MISSING**,
не COVERED.

❌ **Запрещено** ставить в банке `answered` / `resolved` без строки `applied`
в `DECISIONS` с заполненной колонкой Decision от пользователя.

### Поиск ответа (до записи в DECISIONS)

По приоритету:

1. `DECISIONS` — если Relates уже содержит этот `CH-*` или связанный `Q-XX`
   с Decision, **не спрашивать заново**: COVERED/apply/deferred по статусу
2. `CONTEXT_DOC`, sibling-spec в `Feature-writing/*/`
3. `analytics/` по ссылкам из spec/context
4. Grep / read в `repositories/` (read-only)
5. `db-export/`

Если источник **однозначно** закрывает вопрос — можно пометить COVERED и
**дописать** spec точечно (без CH-маркеров), только если формулировка в spec
размыта. Иначе — строка `needs-answer` в `DECISIONS`.

---

## Шаг 3. DECISIONS, не ask_user_question

Субагент **не** вызывает `ask_user_question`. Протокол — `artifact-paths` § DECISIONS.

1. Есть **`pending-apply`** по `CH-*` **и нет новых** PARTIAL/MISSING в текущем
   батче → Шаг 4 **только** для этих `D-*`.
2. PARTIAL/MISSING без Decision: одна строка `needs-answer` на `CH-NN` (Critical/Major
   первыми; батч ≤15). В Relates — `CH-NN`. Options = 2–4 конкретных + «Отложить».
3. Записал **хотя бы одну** новую `needs-answer` → **`ASK_PARENT` и стоп**.
   ❌ Не переходить к Шагу 4, не патчить `SPEC`, не писать `CHALLENGES_MAP` apply.
4. COVERED без спора — **не** писать в `DECISIONS`; статус в банке → `covered`.
5. **`deferred`** в банке — только Minor/backlog **или** явный вариант «Отложить»
   в Options; **Critical без Decision пользователя не defer**.

Оркестратор опрашивает пользователя (`ask_user_question`), ставит `pending-apply`;
этот скилл запускают снова для apply.

---

## Шаг 4. Применить ответы

### 4.1 Принцип «чистая spec»

- ❌ Не добавлять `[CH-...]`, «журнал вопросов» в spec.
- ✅ Переписать / дополнить § (use case alt, BR/CN, контракт, NFR, маппинг).
- ✅ Новое BR/CN — только если пользователь выбрал явное правило.

### 4.2 Правки spec

По каждому решённому CH (не «отложить»):

1. Обновить все затронутые § согласованно.
2. При необходимости добавить alt-сценарий, строку в таблицу ошибок, NFR.

### 4.3 Обновить статусы в `CHALLENGES`

| Исход | Статус в банке |
|-------|----------------|
| Зафиксировано в spec | `resolved` |
| Уже было в spec | `covered` |
| Отложено | `deferred` |

Менять **только** колонку «Статус». Строки не удалять — история банка сохраняется.
В `DECISIONS` применённые → `applied`, отложенные → `deferred`.

### 4.4 Карта решений

Запиши `CHALLENGES_MAP`. Шаблон — reference. Повторный прогон — append секции
`## Сессия N`. `SPEC` без дублирования карты.

### 4.5 Обратная запись в `CONTEXT_DOC`

Если закрытый `CH-*` отвечает на `Q-XX` из контекст-документа — допиши строку в
`CONTEXT_DOC` § `## Закрытые вопросы` (создай секцию, если нет; строку из
«Открытые вопросы» **не** удалять):

```markdown
| Q-08 | 2026-08-28 | Обогащение из BPH при пустом yield в ОГ [BR-05] | §1.3 alt 4a | /resolve-challenges (CH-03) |
```

Остальные § контекст-документа **не менять вручную**. После карты запусти:

```bash
python3 scripts/refresh_context.py <slug>
```

---

## Шаг 5. Ответ и перепроверка

Кратко: опрошено / resolved / covered / deferred; пути `SPEC`, `CHALLENGES`,
`CHALLENGES_MAP`.

**Next step** — по матрице:

| Что изменилось | Рекомендация |
|----------------|--------------|
| Появились новые BR/CN или alt-сценарии | `/check-feature <slug>` — согласованность |
| Правки затронули контракты, БД, интеграции | `/check-feature-code <slug>` (обязательно) |
| `ALIGNMENT` уже существовал | он **устарел** → повторный `/check-feature-code` |
| Остались `deferred` с severity Critical | вернуться позже; отметить в сводке |
| Сомнение, что дальше | `/feature-status <slug>` |

---

## Антипаттерны

- ❌ Статус `answered` / `resolved` в `CHALLENGES` без `applied` Decision пользователя
- ❌ COVERED для Critical/Major без однозначной цитаты § spec
- ❌ Продолжать работу после записи `needs-answer` — только `ASK_PARENT` и стоп
- ❌ Закрыть все 35 CH за один прогон без паузы на пользователя
- ❌ Править `SPEC` до `pending-apply` в `DECISIONS` (кроме явного COVERED)
- ❌ Звать `ask_user_question` из субагента или переспрашивать Relates с Decision
- ❌ Закрывать CH без verdict или выбора пользователя
- ❌ Писать карту решений внутри `SPEC`
- ❌ Удалять строки из `CHALLENGES` вместо смены статуса
- ❌ Править § `CONTEXT_DOC` кроме «Закрытые вопросы» и блока `refresh_context.py`
- ❌ Менять `repositories/`
- ❌ Путать с `/resolve-gaps` (тот — `[GAP-...]` из spec)
- ❌ **Создавать новые `GAP-*`** (inline или строки таблиц) в `SPEC`. Новые gaps —
  только у `/check-feature` и `/resolve-gaps`. Незакрытый продуктовый вопрос после
  CH → `deferred` в банке + строка в `DECISIONS`, **не** gap-таблица

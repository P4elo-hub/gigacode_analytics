---
name: feature-status
description: >-
  Read-only dashboard for a feature slug: scans Feature-writing/<slug>/ and the
  context doc, counts open [GAP-...] and CH-* items, reads the code-alignment verdict,
  detects stale reports by mtime, and recommends exactly one next command. Use when
  resuming work on a feature or when unsure which pipeline step comes next.
user-invocable: false
---

# feature-status

**Read-only дашборд фичи.** Отвечает на два вопроса: «что уже сделано» и
«какая ровно одна команда следующая».

Ничего не правит — ни `SPEC`, ни отчёты. Пути и токены: правило `artifact-paths`.

## Когда вызывать

- возвращаешься к фиче после паузы;
- не помнишь, какой шаг pipeline следующий;
- перед финальной сдачей — проверить критерии готовности;
- после правок — узнать, какие отчёты устарели.

| | Путь |
|---|------|
| **Читаем** | `FEATURE_DIR` целиком + `CONTEXT_DOC` |
| **Пишем** | ничего (вывод только в чат) |

Детали подсчёта и матрица next step: [reference.md](reference.md).

---

## Шаг 0. Разрешить slug

1. Аргумент: `<slug>`, путь к `SPEC` или к любому артефакту фичи.
2. Аргумента нет → перечисли доступные фичи
   (`ls Feature-writing/`) и попроси выбрать.
3. Нет `FEATURE_DIR` и нет `CONTEXT_DOC` → фича не начата,
   **Next:** `/find-context <бриф>`.

Проверь **legacy-раскладку**: файлы `Feature-writing/<slug>*.md` вне папки.
Если найдены — сообщи и предложи перенести в `FEATURE_DIR`.

---

## Шаг 1. Инвентаризация артефактов

```bash
ls -la Feature-writing/<slug>/ 2>/dev/null; ls -la Feature-context/<slug>.md 2>/dev/null
```

Заполни матрицу наличия:

| Токен | Есть? | Кто создаёт |
|-------|-------|-------------|
| `CONTEXT_DOC` | да / нет | `/find-context` |
| `SPEC` | да / нет | `/write-feature` |
| `DECISIONS` | да / нет | оркестратор + resolve-* |
| `GAPS_MAP` | да / нет | `/resolve-gaps` |
| `CHALLENGES` | да / нет | `/challenge-feature` |
| `CHALLENGES_MAP` | да / нет | `/resolve-challenges` |
| `ALIGNMENT` | да / нет | `/check-feature-code` |

---

## Шаг 2. Подсчёт открытых пунктов

**Не считай вручную.** Запусти из корня workspace:

```bash
python3 scripts/feature_status.py <slug>
```

JSON для оркестратора: `python3 scripts/feature_status.py <slug> --json`.

Скрипт считает (детали regex — reference; канон — код скрипта):

| Метрика | Источник |
|---------|----------|
| Открытые `[GAP-...]` | `SPEC`: inline-маркеры + строки таблиц гэпов |
| Открытые `Q-XX` | `CONTEXT_DOC` § «Открытые вопросы» минус § «Закрытые вопросы» |
| `CH-*` по статусам | `CHALLENGES`: `open` / `deferred` / `resolved` / `covered` |
| Verdict + счётчики | `ALIGNMENT` frontmatter: `verdict`, `alignment_iteration` |
| Critical/Major MISMATCH | `ALIGNMENT`: строки со статусом `MISMATCH` |

---

## Шаг 3. Свежесть отчётов (mtime)

Скрипт уже пишет строку **Устарело**. Правило: отчёт **устарел**, если `SPEC`
изменён **позже** отчёта.

| Отчёт старше `SPEC` | Значение | Действие |
|---------------------|----------|----------|
| `ALIGNMENT` | Сверка с кодом не отражает правки | повторить `/check-feature-code` |
| `CHALLENGES` | Банк старше `SPEC` после apply | **информационно**; next step — `check-feature-code`, не re-challenge |

Свежесть `ALIGNMENT` — блокер для code audit. Свежесть `CHALLENGES` — только предупреждение в выводе.

---

## Шаг 4. Определить next step

Бери **Next** из вывода `python3 scripts/feature_status.py <slug>`.
**Не пересчитывай матрицу в голове.**

Канон routing: `scripts/pipeline.yaml` → `dispatch.spec` → `pipeline_router.py`
→ `feature_status.choose_next_step()`.

Таблица приоритетов P10–P140 — [reference.md](reference.md).
Golden fixtures (24 кейса) —
[COVERAGE.md](../../../scripts/fixtures/dispatch_golden/spec-v2/COVERAGE.md).

Ключевые ветки (первое совпадение): context → spec → **`needs-check-feature`**
→ DECISIONS (`needs-answer` / `pending-apply`) → alignment mismatch → gaps →
challenges → challenge-feature → check-feature-code → ready / stopped.

Если `alignment_iteration` ≥ 3 и verdict FAIL — stopped, ручной разбор `ALIGNMENT`.

---

## Шаг 5. Вывод в чат

Покажи вывод скрипта как есть (шаблон совпадает с reference).
Не пересказывай отчёты. Если нужен свой текст — только поверх счётчиков скрипта:

```markdown
## Фича: <slug>

| Артефакт | Статус |
|----------|--------|
| CONTEXT_DOC | ✅ / ❌ |
| SPEC | ✅ (N строк) |
| … | … |

**Открыто:** GAP: N · CH open: N · Q: N
**Alignment:** verdict (итерация N/3), Critical/Major: N
**Устарело:** [список или «—»]

**Next:** `/команда <slug>` — причина в одну строку
```

Оркестратор запускает Next сам, без вопроса «запускать?».
Готовность к сдаче — чеклист из reference; отметь непройденные пункты.

---

## Антипаттерны

- ❌ Править `SPEC` или отчёты (скилл строго read-only)
- ❌ Считать GAP/CH/Q вручную вместо `scripts/feature_status.py`
- ❌ Давать несколько равнозначных «next step» вместо одного
- ❌ Пересказывать содержимое отчётов вместо счётчиков
- ❌ Считать `NOT FOUND` для TO BE блокером
- ❌ Предлагать 4-й прогон alignment при исчерпанном лимите

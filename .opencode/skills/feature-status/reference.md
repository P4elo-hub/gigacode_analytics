# feature-status — reference

## Разрешение входа

| Ввод | Результат |
|------|-----------|
| `og-trading-order-yield` | `FEATURE_DIR` = `Feature-writing/og-trading-order-yield/` |
| путь к `SPEC` | slug из имени папки |
| путь к любому отчёту фичи | slug из frontmatter или имени папки |
| пусто | список папок в `Feature-writing/` → попросить выбрать |

---

## Подсчёт открытых пунктов

### Открытые `[GAP-...]` в `SPEC`

| Что считать | Признак |
|-------------|---------|
| Inline-маркер | `\[GAP-[A-Z0-9-]+\]` в тексте, таблицах, use case |
| Строка таблицы гэпов | начинается с `| GAP-…` и `Тип` = `Gap` / `Допущение` |

Не считать: упоминания в прозе вида «см. GAP-NFR-01» без квадратных скобок,
если строка гэпа уже удалена (закрыт), и строки со статусом `Закрыт` (legacy).

Уникализируй по id: один `GAP-INT-05` в трёх § — это **один** открытый пункт.

### `Q-XX` в `CONTEXT_DOC`

```
открытые Q = все Q-XX в § «Открытые вопросы»
            − Q-XX, перечисленные в § «Закрытые вопросы»
```

Секцию «Закрытые вопросы» создают resolve-скиллы (обратная запись).

### `CH-*` в `CHALLENGES`

Считать по колонке «Статус»: `open`, `deferred`, `resolved`, `covered`.
Блокирующими считать только `open` с severity `Critical` / `Major`.

### `ALIGNMENT`

Из frontmatter: `verdict`, `alignment_iteration`.
Из таблиц: количество строк со статусом `MISMATCH` и severity `Critical` / `Major`.

`NOT FOUND` для TO BE — **не** блокер (ожидаемо до реализации).

---

Канон подсчёта — `pipelines/spec/status.yaml` + `pipelines/spec/collectors.py`
(`pipeline_status.populate_status`).
Канон routing — `pipelines/spec/dispatch.yaml` → `pipeline_router.py`.

Полная таблица правил, приоритетов и golden-fixtures:
[scripts/fixtures/dispatch_golden/spec/COVERAGE.md](../../../scripts/fixtures/dispatch_golden/spec/COVERAGE.md).

## Матрица next step

**Не пересчитывай вручную.** Бери **Next** из вывода `python3 scripts/feature_status.py <slug>`.

Порядок оценки (compiled router, первое совпадение):

| P | Условие (кратко) | Next step | mode |
|---|------------------|-----------|------|
| 10 | лимит alignment (3× FAIL) | — | stopped |
| 20 | нет `CONTEXT_DOC` | find-context | delegate |
| 30 | нет `SPEC` | write-feature | write_feature_cycle |
| inv | SPEC требует перепроверки (`needs-check-feature`) | check-feature | delegate |
| 40 | `needs-answer` в DECISIONS + open GAP | resolve-gaps | ask_user |
| 45 | `needs-answer` только по ALIGNMENT (F-/I-/…) | resolve-code-alignment | ask_user |
| 50 | `needs-answer` только CH | resolve-challenges | ask_user |
| 60 | `pending-apply` + open GAP | resolve-gaps | delegate |
| 65 | `pending-apply` ALIGNMENT (+ mismatch, не stale) | resolve-code-alignment | delegate |
| 70 | `pending-apply` только CH | resolve-challenges | delegate |
| 80 | Critical/Major MISMATCH, итерация < 3, не stale | resolve-code-alignment | delegate |
| 90 | open `[GAP-...]` в SPEC | resolve-gaps | delegate |
| 100 | CH `open` > 0 | resolve-challenges | delegate |
| 110 | нет `CHALLENGES` | challenge-feature | delegate |
| 120 | нет `ALIGNMENT` или stale | check-feature-code | delegate |
| 130 | verdict PASS / PASS WITH GAPS | — | ready |
| 140 | прочий FAIL alignment | check-feature-code | delegate |

Особые случаи:

- **`alignment_stale`** (SPEC новее ALIGNMENT): P80 не шлёт в resolve-code-alignment по
  устаревшему отчёту → срабатывает P120 → `check-feature-code`.
- **Смешанные DECISIONS** (alignment + CH): сначала alignment (P45/P65), потом CH (P50/P70).
- **`alignment_iteration` ≥ 3 и FAIL** → stopped, ручной разбор ALIGNMENT.

---

## Свежесть по mtime

```bash
stat -f '%m %N' Feature-writing/<slug>/* Feature-context/<slug>.md 2>/dev/null | sort -rn
```

| Сравнение | Вывод |
|-----------|-------|
| `SPEC` новее `ALIGNMENT` | «alignment устарел» |
| `SPEC` новее `CHALLENGES` | «challenges могли устареть» |
| `CONTEXT_DOC` новее `SPEC` | «контекст обновлён после spec — возможно, нужен `/check-feature`» |

mtime — эвристика: правка одной опечатки формально «устаревает» отчёт.
Поэтому это **предупреждение**, а не блокер.

---

## Шаблон вывода

```markdown
## Фича: og-trading-order-yield

| Артефакт | Статус |
|----------|--------|
| CONTEXT_DOC | ✅ 109 строк |
| SPEC | ✅ 570 строк |
| GAPS_MAP | ✅ 12 закрыто |
| CHALLENGES | ✅ 24 вопроса |
| CHALLENGES_MAP | ✅ 18 закрыто |
| ALIGNMENT | ✅ итерация 2/3 |

**Открыто:** GAP: 0 · CH open: 6 (Critical 1) · Q: 3
**Alignment:** PASS WITH GAPS, Critical/Major MISMATCH: 0
**Устарело:** alignment (spec правился позже)

**Next:** `/resolve-challenges og-trading-order-yield` — 6 открытых CH, один Critical
```

Держи вывод компактным: таблица + три строки счётчиков + одна рекомендация.
Полное содержимое отчётов **не** пересказывать.

---

## Чеклист готовности к сдаче

- [ ] `SPEC` полон по плану / `spec-catalog.yaml`
- [ ] Открытых `[GAP-...]` нет **или** все осознанно отложены (в `GAPS_MAP`)
- [ ] `CH-*` со severity Critical/Major — нет в статусе `open`
- [ ] `ALIGNMENT` verdict = PASS или PASS WITH GAPS
- [ ] Нет Critical/Major MISMATCH
- [ ] `ALIGNMENT` не старше `SPEC`
- [ ] Sibling-фичи согласованы (если есть общий контракт)

`NOT FOUND` для TO BE в коде — норма (ещё не реализовано).

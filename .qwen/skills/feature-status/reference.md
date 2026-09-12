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

Канон подсчёта и next step — `scripts/feature_status.py`. Этот файл — человекочитаемая копия.

## Матрица next step

Проверять **по порядку**, вернуть первое совпадение. Скрипт делает то же самое.

| № | Условие | Next | Причина |
|---|---------|------|---------|
| 1 | нет `CONTEXT_DOC` | `/find-context <бриф>` | нет проверенного контекста |
| 2 | нет `SPEC` | `/write-feature <бриф>` | спецификация не написана |
| 3 | `ALIGNMENT` c Critical/Major MISMATCH, итераций < 3 | `/resolve-code-alignment <slug>` | spec противоречит коду |
| 4 | открытых `[GAP-...]` > 0 | `/resolve-gaps <slug>` | незакрытые факты |
| 5 | `CHALLENGES` есть, `open` > 0 | `/resolve-challenges <slug>` | незакрытые corner cases |
| 6 | нет `CHALLENGES` | `/challenge-feature <slug>` | критический разбор не проводился |
| 7 | нет `ALIGNMENT` **или** он старше `SPEC` | `/check-feature-code <slug>` | сверка с кодом отсутствует / устарела |
| 8 | всё закрыто, verdict PASS / PASS WITH GAPS | — | **spec готов** |

Особый случай: `alignment_iteration` ≥ 3 и verdict FAIL → не предлагать прогон,
сообщить «лимит цикла исчерпан, нужен ручной разбор `ALIGNMENT`».

---

## Свежесть по mtime

```bash
stat -f '%m %N' Feature-writing/<slug>/* Feature-context/<slug>.md 2>/dev/null | sort -rn
```

| Сравнение | Вывод |
|-----------|-------|
| `SPEC` новее `ALIGNMENT` | «alignment устарел» |
| `SPEC` новее `CHALLENGES` | «challenges старше spec» (информационно; re-challenge не dispatch'ится) |
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

# resolve-code-alignment — reference

## Разрешение входа

| Ввод пользователя | Результат |
|-------------------|-----------|
| `bph-moex-tax` | `Feature-writing/bph-moex-tax/bph-moex-tax-code-alignment.md` |
| путь к `SPEC` | slug из имени папки → alignment file |
| путь к `ALIGNMENT` | slug из frontmatter или имени папки |

Frontmatter `slug:` в alignment — приоритет при неоднозначности.
Пути и токены: правило `artifact-paths`.

---

## Карта статусов → действие

| Status в alignment | Closable? | Типичный вопрос |
|--------------------|-----------|-----------------|
| CONFIRMED | нет | — |
| MISMATCH | **да** | какая формулировка верна vs код |
| PARTIAL | **да** | уточнить spec под evidence |
| UNVERIFIABLE | **да** (если допущение достаточно) | принять / отложить |
| NOT FOUND (TO BE) | **нет** | ожидаемо до реализации |
| Info без gap | нет | — |

### Severity порядок опроса

1. Critical MISMATCH
2. Major MISMATCH
3. Open Q / GAP с blocker=да
4. PARTIAL / Minor MISMATCH
5. UNVERIFIABLE / non-blocking Q

---

## Связь alignment ↔ spec ↔ context

1. В alignment ищи `Q-XX`, `GAP-…`, BR в claims и Recommended actions.
2. Открой таблицы gaps и § открытых вопросов в `SPEC`.
3. Для каждой Q из alignment сформируй question в AskQuestion.
4. После закрытия — строка в `CONTEXT_DOC` § «Закрытые вопросы».

TO BE findings (нет теста, нет INSERT в коде) **не** превращай в Q, если spec уже описывает их как будущую реализацию.

---

## Шаблоны вариантов

### MISMATCH / PARTIAL

| Вариант | Смысл |
|---------|--------|
| A | Привести spec к evidence из кода |
| B | Оставить spec; зафиксировать Q «код устарел» (редко) |
| C | Уточнить формулировку в конкретном § |
| Other | … |

### Open Q

| Вариант | Смысл |
|---------|--------|
| A | Конкретное значение / стратегия |
| B | Альтернатива |
| C | Отложить; Q остаётся открытым |
| Other | … |

---

## Правила правки spec

- Таблицы gaps: строку закрытого gap **удалить** (не помечать «закрыто»).
- Use Case / TO BE: обновить только если ответ меняет поведение.
- §4.x (контракты, алгоритм, БД): точечно под PARTIAL/MISMATCH.
- Сохранять порядок глав плана / `spec-catalog.yaml`.
- TO BE scope не помечать как «уже в коде».

### Consistency checklist

- [ ] Нет противоречия «Q открыт» vs «решение зафиксировано»
- [ ] Закрытые gaps удалены из `SPEC`, решения — в `ALIGNMENT` log / `CONTEXT_DOC`
- [ ] BR/CN согласованы с изменённым §
- [ ] Закрытые `Q-XX` дописаны в `CONTEXT_DOC`

---

## Журнал решений

Append-only секция в `ALIGNMENT`. Не меняй `verdict` / счётчики — их обновит
следующий `/check-feature-code`.

---

## Петля перепроверки

| После правок | Обязательно | Дополнительно |
|--------------|-------------|---------------|
| Любые правки `SPEC` | `/check-feature-code <slug>` | — |
| Изменились BR/CN, use case | `/check-feature-code` | сначала `/check-feature` |
| Изменились контракты, БД | `/check-feature-code` | повторный `/check-feature-code` (alignment loop) |
| Итераций уже 3, verdict FAIL | ручной разбор | `/feature-status <slug>` |

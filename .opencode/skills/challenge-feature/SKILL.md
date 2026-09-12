---
name: challenge-feature
description: >-
  Adversarial review of the feature spec: generates tricky questions, corner cases,
  missing coverage, and contradictions. Writes the full question bank in Russian to
  <slug>-challenges.md; does not edit the spec. Invoke after /check-feature or
  before /resolve-challenges.
user-invocable: false
---

# challenge-feature

**Критик спецификации** — read-only аудит с позиции «что может пойти не так».
Генерирует каверзные вопросы, corner cases, пробелы; сохраняет их в отдельный
файл. `SPEC` **не править**.

Пути и токены: правило `artifact-paths`.

## Pipeline

```
/write-feature → /check-feature → /resolve-gaps → /challenge-feature → /resolve-challenges → …
```

| | Путь |
|---|------|
| **Вход** | `SPEC` = `Feature-writing/<slug>/<slug>.md` |
| **Контекст** | `CONTEXT_DOC`, sibling-spec, `analytics/` |
| **Выход** | `CHALLENGES` = `Feature-writing/<slug>/<slug>-challenges.md` |
| **Не трогаем** | `SPEC`, `repositories/`, `ALIGNMENT`, `GAPS_MAP`; `DECISIONS` только читать |

Чеклисты категорий: [reference.md](reference.md).

---

## Шаг 0. Разрешить slug

1. Аргумент: `<slug>` или путь к `SPEC`.
2. Нет `SPEC` → стоп: `/write-feature`.
3. Опционально: **фокус** (§, тема: «merge», «NFR», «ошибки») — углубить только
   эту область, но базовый проход по всем категориям всё равно сделай.

---

## Шаг 1. Подготовка

Прочитай **целиком**:

1. `SPEC`
2. `CONTEXT_DOC` — если есть (включая § «Закрытые вопросы»: закрытые Q
   переспрашивать не нужно)
3. `DECISIONS` — готовые Decision по Relates не поднимай заново
4. Sibling / linked spec из CN, брифа, ссылок в doc
5. `GAPS_MAP` — если есть: решения уже приняты, не поднимай их заново
6. При необходимости — якоря в `analytics/`, быстрый grep в `repositories/` для
   **реалистичных** corner cases (не для правки spec)

Зафиксируй: BR/CN, use cases (alt-сценарии), контракты, маппинг, NFR, toggles,
открытые `[GAP-...]`, TBD.

---

## Шаг 2. Критический разбор по категориям

Для **каждой** категории из reference пройди spec и context. Ищи:

| Что искать | Примеры |
|------------|---------|
| Corner cases | null/пусто, partial response, race, duplicate id, лимиты |
| Неучтённые alt-потоки | ошибка интеграции, timeout, toggle OFF, нет данных в одном источнике |
| Противоречия | BR vs CN vs use case vs контракт vs sibling-spec |
| Дыры в § | нет кода ошибки, нет поведения при optional absent, нет rollback |
| NFR / эксплуатация | prod vs test, деградация, идempotency, observability |
| Тестируемость | нет критерия приёмки, нет фикстуры под edge |

**Не дублируй** уже явно закрытые в spec пункты — если spec однозначно отвечает,
вопрос **не включай**. Если ответ частичный — формулируй вопрос на пробел.

Каждый вопрос:

- конкретный, провокационный, проверяемый;
- привязан к § spec (`§1.3 alt 4a`, `§4.1.1`, `BR-05`);
- с типом и severity (см. reference);
- id **`CH-NN`** (уникален в рамках slug, сквозная нумерация при re-run).

---

## Шаг 3. Запись банка вопросов

**Полный банк — только в файл** `CHALLENGES`. В чат — краткая сводка.

| Правило | Значение |
|---------|----------|
| Первый прогон | создать файл (единственный **автоматический** прогон на slug) |
| Повторный прогон | **только по явной команде пользователя**. Merge: сохранить `open`/`deferred`, добавить новые id; после apply SPEC оркестратор **не** вызывает challenger — следующий шаг `check-feature-code` |
| Язык | русский (имена полей/API — как в spec) |
| Статус нового CH | **только** `open` |

❌ Не ставь в банке `needs-answer`, `answered`, `covered`, `resolved`, `deferred` —
закрытие и вердикты — только у `/resolve-challenges`.

Шаблон — [reference.md](reference.md) § «Выходной файл».

**Не пиши** вопросы в `SPEC` и не добавляй туда `[CH-...]`.

---

## Шаг 4. Ответ в диалог

```markdown
Критический разбор: **N вопросов**

Файл: `Feature-writing/<slug>/<slug>-challenges.md`

- Critical: N · Major: N · Minor: N
- Топ-3: [кратко]
- Next: `/resolve-challenges <slug>` → оркестратор опросит по `needs-answer` в DECISIONS
```

При повторном прогоне укажи отдельно: новых вопросов N, сохранено открытых N.

---

## Антипаттерны

- ❌ Статус кроме `open` для новых `CH-*` (закрытие — у resolve-challenges)
- ❌ Править `SPEC`
- ❌ Выводить полный список вопросов в чат
- ❌ Генерировать абстрактные вопросы без привязки к § spec
- ❌ Поднимать вопросы, уже закрытые в `DECISIONS`, `GAPS_MAP` или `CONTEXT_DOC`
- ❌ Дублировать `/check-feature` (тот правит по источникам; критик — adversarial QA)
- ❌ Путать с `/check-feature-code` (сверка с кодом)

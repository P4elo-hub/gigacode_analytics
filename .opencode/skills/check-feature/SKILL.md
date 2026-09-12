---
name: check-feature
description: >-
  Reviews and fixes feature specification Feature-writing/<slug>/<slug>.md against
  context-doc, analytics, other specs, repositories, and db-export. Editable
  artifact only — the feature doc. Invoke after /write-feature and before
  /check-feature-code.
disable-model-invocation: true
---

# check-feature

Ревизия и **правка** спецификации фичи `SPEC`.
Read-write для feature-doc; read-only для контекста, analytics, кода, данных.

Пути и токены: правило `artifact-paths`.

## Pipeline

```
/find-context → /write-feature → /check-feature → /resolve-gaps
  → /challenge-feature → /resolve-challenges → /check-feature-code → spec ready
```

Также вызывается **после** любого resolve-скилла для проверки согласованности.

## Артефакты

| Роль | Путь |
|------|------|
| Проверяемый (правим) | `SPEC` = `Feature-writing/<slug>/<slug>.md` |
| Контекст | `CONTEXT_DOC` = `Feature-context/<slug>.md` |
| Список блоков | `kb-writing-kits/spec-catalog.yaml` |
| Quality gates | kit-ы из `kb-writing-kits/` (по разделам doc) |

Нет `SPEC` → стоп, нужен `/write-feature`.

## Источники истины

| Вопрос | Где искать |
|--------|------------|
| Постановка, бриф, якоря | `Feature-context/<slug>.md` |
| Бизнес-требования | `analytics/` |
| Другие спецификации (reference) | `Feature-writing/` (кроме текущего slug) |
| Контракты, классы, миграции | `repositories/` |
| Схема БД (справочник) | `db-export/` |
| Доп. материалы | `auxiliary/` (если есть) |

При расхождении analytics и кода — конфликт или `[GAP-...]`, не выбирай «наугад».

## Вход команды

1. **`<slug>`** — обязателен (или путь к `Feature-writing/<slug>/<slug>.md`).
2. **Приоритетные указания** (опционально) — фокус проверки.
3. **Alignment focus** (опционально) — «исправь findings из code-alignment» + путь к отчёту.

## Принципы

1. **Доказательная правка** — меняй только то, что подтверждено источником.
2. **Структура** — порядок глав как в утверждённом плане / `spec-catalog.yaml`. Полнота раздела — template и gate kit.
3. **ID** — `BR-XX`, `CN-XX`, `[GAP-...]`, `Q-XX`; не выдумывать, не удалять незакрытые гэпы.
4. **Use Case** — уровень сценария; внутренние классы/мапперы — только в §4.x / §5.x, не в AS IS/TO BE.
5. **Контракты** — как требует integration kit выбранного протокола. Не восстанавливай поля/примеры, которых нет в kit.

---

## Шаг 1. Подготовка

1. Прогони structural gates (форма, не смысл):

   `python3 scripts/quality_gates.py <slug>`

   Fail-пункты (`QG-*`) исправь в `SPEC` до сверки с источниками, если это
   служебные строки, внутренние классы в use case, маркеры `quality_gates.py`.
   Не добавляй подразделы (SMART, stakeholders, примеры JSON), которых нет
   в текущем kit. `QG-CONTRACT-02` (warn): для gRPC — rpc / message / metadata,
   если это ещё требует gate.
2. Прочитай целиком feature-doc, context-doc (если есть).
2. Если указан alignment-отчёт — прочитай `Feature-writing/<slug>/<slug>-code-alignment.md`
   и выпиши findings с severity Critical/Major/PARTIAL для targeted fix.
3. Собери реестр: контракты, endpoints, таблицы, поля, классы, конфиги, toggles.
4. Выпиши фокус из приоритетных указаний.

---

## Шаг 2. Приоритетные указания / alignment findings

Если есть — проверь **первым**, глубже обычного:

1. Место в doc + исходник (context-doc, `find_context.py`, grep в `repositories/`).
2. Детальная сверка: имя, тип, format, required, enum, примеры.
3. Подтверждено → исправь; противоречие → конфликт + гэп; не подтвердить → `[GAP-...]`.
4. Затем полный проход (Шаги 3–7).

---

## Шаг 3. Сверка с постановкой

Сверь doc с брифом и § «Задача (бриф)» context-doc:

- [ ] Каждый пункт постановки → цель, Use Case AS IS/TO BE, §4.x / §5.x
- [ ] Нет «потерянных» требований из context-doc
- [ ] BR/CN согласованы между разделами

Непокрытое → допиши по template/gate kit раздела или `[GAP-...]`. Не
добавляй главы, которых нет в плане.

---

## Шаг 4. Контракты и примеры (§4.1.x)

Для каждого контракта в doc:

1. Исходник в `repositories/` / `db-export/` по context-doc.
2. Имя, тип, format, required, enum — против исходника, в том объёме, который
   требует kit.
3. Примеры request/response — только если их требует kit; тогда валидны против схемы.
4. Расхождение → правка doc; нет подтверждения → `[GAP-...]`.

---

## Шаг 5. Полнота требований

- [ ] Коды ошибок, заголовки, toggles, конфиги — если эти разделы в плане и в kit
- [ ] NFR / observability заполнены **как требует kit**, не сверх него
- [ ] Модель данных отдельно от миграций (§4.2.3)
- [ ] Gaps tables в каждом затронутом блоке, если gate блока их требует
- [ ] Тестовая стратегия / фикстуры (если заявлены в doc)

---

## Шаг 6. Обход ссылок context-doc

Пройди ссылки: `analytics/`, другие spec, `repositories/`, `db-export/`.
Сверь, что doc не противоречит подтверждённым источникам.

---

## Шаг 7. Правила правок

- Без служебных строк: `INTERNAL`, `> **Kit`, `> **Skill`, ```markdown обёртки.
- Язык — русский (кроме имён полей API/БД, slug).
- Не читай `*-code-alignment.md` автоматически, **кроме** явного alignment-focus во входе.

---

## Шаг 8. Петля перепроверки

| Ситуация | Дальше |
|----------|--------|
| Обычный порядок, есть открытые `[GAP-...]` | `/resolve-gaps <slug>` |
| Гэпов нет, критический разбор не проводился | `/challenge-feature <slug>` |
| Гэпов нет, `CHALLENGES` закрыт | `/check-feature-code <slug>` |
| Вызван после resolve-скилла | `/check-feature-code <slug>` (закрыть петлю) |
| FAIL alignment | `/resolve-code-alignment` или targeted `/check-feature` → `/check-feature-code` |
| Не ясно, что дальше | `/feature-status <slug>` |

Правки `SPEC` **устаревляют** `ALIGNMENT` и `CHALLENGES` — упомяни это в отчёте,
если файлы существуют.

---

## Шаг 9. Отчёт в диалог

1. Приоритетные указания / alignment findings — результат по каждому
2. Что проверено (постановка, контракты, §5.x, ссылки)
3. Что исправлено (§, источник)
4. Открытые `[GAP-...]`
5. Путь: `SPEC`; какие отчёты устарели после правок
6. **Next:** одна рекомендация по матрице Шага 8

## Антиpatterns

- ❌ Выдумывать факты или удалять незакрытые гэпы
- ❌ Внутренние классы в Use Case AS IS/TO BE
- ❌ Сжимать форму относительно kit или дописывать главы вне плана / каталога
- ❌ Analytics вместо кода для технических фактов
- ❌ Править `repositories/` или alignment-отчёт (read-only)

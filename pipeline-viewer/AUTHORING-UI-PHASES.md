# Редактор схемы пайплайна — фазы и промпты

Одна большая задача = **семь сессий**. В каждой сессии копируй блок «Промпт» целиком. Не склеивай фазы в один чат.

Уже есть: вкладка **прогона** (живой граф задачи), `GET /api/catalog`, compile `--export-json` / `--from-json`, схема `scripts/pipeline_pack_schema.json`. Новая вкладка — **редактор пака**, не таймлайн фичи.

Бизнес-рамка: предыдущий разговор про BR-01…BR-11 (вкладка «Схема», палитра агентов, холст, типы клеток, стрелки, приоритеты, составная write-feature, save/compile).

## Как стартовать сессию

1. Новый чат Cursor в этом репозитории.
2. Вставь **общий префикс** + промпт нужной фазы.
3. В конце сессии агент отмечает фазу в чеклисте ниже (`[x]`) и пишет 5–10 строк «что сделано / что не трогать следующей».
4. Не начинай фазу N, пока N−1 не закрыта по критерию «Готово».

### Общий префикс (вставлять каждый раз)

```
Репозиторий: gigacode_analytics. Фронт живёт в pipeline-viewer/ (static HTML/JS + server.py).
Граф прогона уже есть — его не ломать: Целевой/Факт/Время, SSE, restart, slug.

Читай перед кодом:
- pipeline-viewer/AUTHORING-UI-PHASES.md (этот файл, текущая фаза)
- pipeline-viewer/README.md
- scripts/PIPELINE-PACK-AUTHORING.md
- scripts/pipeline_pack_schema.json
- pipelines/spec/graph.yaml (пример составной клетки cycle: у write-feature)

Правила:
- Делай ТОЛЬКО текущую фазу. Не «заодно» save, cycle, dispatch, новый пак.
- Не правь engine Python ради UI, кроме тонких HTTP-обёрток вокруг уже существующих compile/catalog, если фаза это явно просит.
- Не коммить, пока я не попросил.
- После кода проверь в браузере затронутый поток (не один скриншот).
```

---

## Чеклист

- [x] Фаза 0 — карта контракта (без UI) → `pipeline-viewer/authoring-contract.md`
- [x] Фаза 1 — вкладка «Схема», read-only граф пака
- [x] Фаза 2 — палитра агентов, постановка клеток
- [x] Фаза 3 — стрелки, инспектор, типы клеток (без внутренностей cycle)
- [x] Фаза 4 — составная клетка (write-feature / cycle)
- [x] Фаза 5 — условия, приоритеты, ask, выход из клетки
- [x] Фаза 6 — проверка и сохранение пака

---

## Фаза 0 — карта контракта

**Зачем.** Чтобы следующие сессии не выдумывали модель. Кода UI нет.

**Готово когда.** В `pipeline-viewer/authoring-contract.md` есть: JSON пака ↔ фигуры на холсте; какие API уже есть; чего не хватает; что сознательно не рисуем в v1.

**Не делать.** HTML/CSS/новые вкладки, `--apply` на диск, рефактор viewer.

### Промпт фазы 0

```
Фаза 0 редактора схемы. UI не писать.

Сними карту в pipeline-viewer/authoring-contract.md (коротко, таблицы):

1. Как pack JSON (id, graph.nodes/edges, registry, dispatch, routing_conditions)
   отображается на холсте: оркестратор, обычный шаг, cycle, ask:true, terminal.
2. Чем вкладка «Схема» отличается от текущего /api/graph (прогон задачи).
3. Что уже есть: GET /api/catalog, pipeline_compile.py --export-json / --from-json / --catalog.
4. Каких HTTP-ручек не хватает для фаз 1 и 6 (только список, не реализовывать).
5. v1 не рисует: тексты скиллов, формулы expr, запуск Qwen с холста.

Проверь командами (не меняй generated JSON):
  PYTHONPATH=scripts python3 scripts/pipeline_compile.py --catalog
  PYTHONPATH=scripts python3 scripts/pipeline_compile.py --export-json spec

В конце: 10 строк «фаза 0 закрыта, следующей делать фазу 1 вот так».
```

---

## Фаза 1 — вкладка и read-only схема

**Зачем.** Открыть spec/calibration как схему пака, не как live-задачу.

**Готово когда.** В header есть режим Прогон | Схема. На «Схеме» нет селектора задачи. Клетки и стрелки из `--export-json`. Клики не меняют YAML. Прогон работает как раньше.

**Не делать.** Drag-and-drop, палитру, save, cycle-раскрытие.

### Промпт фазы 1

```
Фаза 1. Сначала прочитай pipeline-viewer/authoring-contract.md.

Сделай режим экрана «Прогон» (как сейчас) и «Схема».
«Схема»: пайплайн spec|calibration, граф из pack JSON (export-json / тонкий GET-обёртка).
Без slug, без SSE прогона, без Целевой/Факт/Время.

Минимум: оркестратор, шаги, terminal, стрелки с подписью. cycle и ask пока просто как шаг с пометкой в tooltip.

Не ломай /api/graph и live SSE.

Проверка в браузере: Прогон — живой slug как раньше; Схема — оба пака; F5 не сбрасывает выбранный режим нелепо.
```

### Фаза 1 закрыта. Следующей — фаза 2

Сделано: режимы **Прогон | Схема** в header; `GET /api/pack?pipeline=` → `export_pack_json` (404 если пака нет).
«Схема» берёт паки из `/api/catalog` (spec, calibration, routing-poc), без slug/SSE/Целевой-Факт-Время.
Клетки: оркестратор / шаг / terminal / meta; cycle и ask — та же клетка, пометка в tooltip.
Стрелки с `label` | `condition`. Клики не пишут YAML. Координаты только клиентский layout.
Прогон: `/api/graph`, SSE, restart, slug — не трогали.

Не трогать в фазе 2: save, compile `--from-json`, раскрытие cycle, инспектор типов, dispatch-таблицу, engine Python.
Не ломать Прогон. Палитра + drop + drag координат в localStorage.

---

## Фаза 2 — палитра и постановка клеток

**Зачем.** Тащить агентов из каталога на холст.

**Готово когда.** Слева агенты (объединение CLI, без тройных копий). Drop создаёт клетку с id/label/subagent. Клетку можно двигать и удалить. Координаты в localStorage или черновике, не в YAML. Save на диск нет.

**Не делать.** Стрелки с условиями, типы cycle/ask в инспекторе, compile --from-json.

### Промпт фазы 2

```
Фаза 2. Не трогай режим Прогон. Не сохраняй пак на диск.

Палитра из GET /api/catalog (agents + skills). Один агент — одна карточка, даже если он в qwen/gigacode/opencode.
Drag на холст «Схема» → новая клетка kind=step. Двигать, удалять, уникальный id.
Предупреждение, если агента нет в одном из CLI — клетку всё равно создать можно.

Координаты — только клиентский черновик.

Проверка в браузере: drop 2 агентов, подвигать, reload — места живы; Прогон не изменился.
```

### Фаза 2 закрыта. Следующей — фаза 3

Сделано: слева палитра `GET /api/catalog` (агенты без тройных копий + скиллы списком).
`agents_by_cli` — тонкая обёртка catalog в `server.py`, engine не трогали.
Drop на холст «Схема» → `kind=step`, id/label/subagent, уникальный id.
Двигать, Delete / «Удалить клетку». Координаты и новые клетки — `localStorage` черновик, YAML нет.
Нет в одном CLI — жёлтый бейдж, клетку всё равно можно поставить.
Прогон: slug, SSE, Целевой/Факт/Время, restart — не меняли.

Не трогать в фазе 3: save, `--from-json`, cycle internals, dispatch-таблицу, engine Python.
Не ломать Прогон. Стрелки from/to, инспектор kind, undo.

---

## Фаза 3 — стрелки, инспектор, типы

**Зачем.** Соединять клетки и задавать простой тип, ещё без внутренностей write-feature.

**Готово когда.** Стрелка from/to, kind main|branch|loop, подпись. Инспектор: id, label, kind (orchestrator|step|terminal|ask|cycle), subagent из палитры. Нельзя сохранить невалидный from/to в черновике. Undo хотя бы клеток/стрелок.

**Не делать.** Список calls внутри cycle, таблицу dispatch.priority, запись YAML.

### Промпт фазы 3

```
Фаза 3. Редактор связей и типов на вкладке «Схема».

Соединение двух клеток стрелкой. Инспектор справа: поля клетки и поля стрелки (kind, label).
Тип cycle/ask пока только флаг на клетке, без вложенного списка блоков и без handshake-деталей.
Валидация на холсте: нет ребра в пустоту, один оркестратор.

Проверка в браузере: соединить find-context → write-feature, сменить kind на loop, undo, Прогон цел.
```

### Фаза 3 закрыта. Следующей — фаза 4

Сделано: на «Схеме» Shift+клик или «Стрелка к…» → ребро from/to. Инспектор: id/label/kind (orchestrator|step|terminal|ask|cycle|meta) / subagent из палитры; у стрелки kind main|branch|loop и label.
cycle/ask — флаг на клетке, без calls и handshake. Ребро в пустоту в черновик не пишется. Второй оркестратор демоутит прежнего; снять последнего нельзя.
Undo клеток/стрелок (кнопка и Cmd/Ctrl+Z). YAML нет. Прогон не трогали.

Не трогать в фазе 4: save, `--from-json`, dispatch.priority, engine Python, редактор condition.
Не ломать Прогон. Раскрытие write-feature: очередь calls, не вложенный граф.

---

## Фаза 4 — составная клетка (cycle)

**Зачем.** write-feature как один квадрат с очередью подвызовов.

**Готово когда.** У клетки с cycle видно: persistent, assemble, param, folder/out/item_file, список calls (agent, param, skills). Можно добавить/убрать/переставить строку. Между строками нет стрелок и when:. Подсказка: если calls пустой — runtime подставит каталог блоков (как spec).

**Не делать.** analyze-routing между блоками (это запрещено моделью). Save пака. Таблицу приоритетов роутера.

### Промпт фазы 4

```
Фаза 4. Составная клетка cycle, как write-feature в pipelines/spec/graph.yaml и scripts/inner_cycle.py.

Раскрытие клетки: очередь {agent, param}, не вложенный граф.
Нельзя изнутри cycle провести ребро на другую клетку пака.
close пока показать текстом «on_done», не редактировать набор enum.

Проверка: открыть spec, write-feature раскрывается; добавить фейковый call, порядок меняется; снаружи клетка одна.
```

### Фаза 4 закрыта. Следующей — фаза 5

Сделано: клик по cycle (spec `write-feature`) раскрывает очередь в клетке и инспекторе.
Инспектор: persistent, assemble, param, folder/out/item_file, close текстом `on_done`, список calls (agent, param, skills).
Добавить/убрать/переставить строку. Пустой calls — подсказка «runtime catalog».
На холсте по-прежнему одна клетка: call не узел, стрелок и when: между строками нет.
`analyze-routing` / `routing-analyzer` в очередь не ставится. YAML нет. Прогон не трогали.

Не трогать в фазе 5: save, `--from-json`, engine Python, редактор expr.
Не ломать Прогон. Дальше: condition на стрелке, таблица dispatch.priority, подпись ask.

---

## Фаза 5 — условия, приоритеты, ask, выход

**Зачем.** Ветки и таблица «что сработает первым».

**Готово когда.** У стрелки condition из catalog routing_conditions / predicates (не свободный prod-текст без привязки). Таблица правил: priority, when, next, outcome. Приоритеты уникальны, сортировка по числу. Клетка ask:true — подпись «пауза на этой клетке, apply без смены шага». Инспектор цикла: выход on_done простым языком.

**Не делать.** Редактор expr формул. --from-json apply. Новый пак с нуля.

### Промпт фазы 5

```
Фаза 5. Условия и приоритеты. Каталог when: из /api/catalog (predicates + routing_conditions).

Стрелка: condition id + человеческая подпись.
Отдельная таблица dispatch-правил (как pipelines/spec/dispatch.yaml): priority уникален, next — id клетки или ready/stopped.
ask:true только на шаге; в UI явно: не строить переход «на другого агента» между вопросом и apply.
Не редактировать status_fields.expr.

Проверка: открыть spec, увидеть P20 not_has_context → find-context; сменить приоритет черновика с подсветкой конфликта дублей; ask на resolve-gaps виден.
```

### Фаза 5 закрыта. Следующей — фаза 6

Сделано: стрелка — `condition` из `/api/catalog` (predicates + routing_conditions), id + человеческая подпись (`not_has_context · no context`).
Таблица dispatch: priority / when / next|ready|stopped, сортировка по числу, дубли priority подсвечиваются.
ask на шаге: на клетке «пауза · apply здесь»; в инспекторе явно — нет перехода на другого агента между вопросом и apply.
Инспектор cycle: выход `on_done` простым языком (отметка шага → снять задачу → внешний dispatch).
expr / status_fields не редактируются. YAML нет. Прогон не трогали.

Не трогать в фазе 6: редактор expr, тексты скиллов, запуск Qwen.
Не ломать Прогон. Save — не «холст → graph.yaml». Полный алгоритм в промпте фазы 6.

---

## Фаза 6 — проверка и сохранение

**Зачем.** Черновик холста должен стать **исполняемым паком**, не только красивым `graph.yaml`.

Роутер не идёт по стрелкам как flowchart. Цепочка: `status` + коллекторы → `expr` в `routing_conditions` → первое правило `dispatch.rules` → `registry` → delegate. Если save запишет только граф, ветка на холсте **не выберется**.

**Готово когда.**

1. **Сборка payload** (обязательно, не «граф целиком»):
   - взяли открытый пак (`GET /api/pack` / `--export-json`);
   - поверх него overlay: `graph` и таблица `dispatch.rules` с холста;
   - `status` и существующие `routing_conditions` (в т.ч. `expr`) **не выкидываем**;
   - `registry` выводим из клеток: `step_to_subagent`, `orchestrator_owned` (нет внешнего task / cycle пишущий оркестратор), `gated_subagents`, `restartable_steps`. Черновик браузера эти поля сам не хранит — save их считает.
2. **Стрелка с condition без строки dispatch** — не молчаливый YAML. Либо ошибка на стрелке («добавь правило в таблицу»), либо тот же путь, что CLI: `pipeline_routing_codegen.py --from-json` / `--from-graph-conditions` (stub `expr`, не затирая ручные формулы; новая строка dispatch). Существующий `expr` не переписывать.
3. **Проверить** — слой 1 schema + слой 2 compile **без записи диска**. Ошибки на клетку / стрелку / строку priority. Apply скрыт, пока не зелёное.
4. **Применить** — confirmation → `--from-json` (пишет YAML и compile `--apply`). Схема перечитывается. Прогон не падает.
5. **Новый пак** — не пустой холст в `--from-json`. Кнопка «создать»: `--init-pack <id> --template routing-state|full-dispatch|orchestrator-only`, затем тот же overlay. Предупреждение, если нет файла оркестратора в `.qwen/agents`. Markdown агентов не генерить.
6. Откат к последнему успешно применённому JSON.

**Не делать.** Редактор `expr`. `collectors.py` / `validate.py` руками. Тексты `.qwen/agents`. Запуск Qwen. Ломать spec без явного «да» (для опытов — новый id или dry-run validate).

### Промпт фазы 6

```
Фаза 6. Save-path, чтобы пак после Apply был исполняемым. Читай authoring-contract.md §4 и «разрыв save» в AUTHORING-UI-PHASES.md.

Нельзя: POST только graph.nodes/edges. Роутер читает status + routing_conditions.expr + dispatch.rules + registry.

Алгоритм Применить / Проверить:
1. base = GET /api/pack (существующий) ИЛИ результат --init-pack (новый id + template).
2. overlay base.graph и base.dispatch.rules из черновика холста (клетки, cycle, ask, стрелки+condition, таблица приоритетов).
3. registry заново из клеток (step_to_subagent, orchestrator_owned, gated, restartable). status и старые expr не трогать.
4. Если у стрелки есть condition, а в dispatch.rules нет when: с этим id — не писать дырявый YAML: либо ошибка на стрелке, либо codegen stub (pipeline_routing_codegen, merge, expr существующих условий не затирать).
5. validate без диска (слой schema + compile). Ошибки к node id / edge id / priority.
6. Apply только после ok: from-json + compile apply. Confirmation. Потом GET пака снова.

HTTP (если нет — тонкие обёртки, не новый engine):
- POST /api/pack/validate  (без записи)
- POST /api/pack/apply
- POST /api/pack/init  → --init-pack (новый пак)

Проверка в браузере:
A) spec: сменить label шага → Проверить → Применить → refresh Схемы; Прогон живого slug жив. Для этого шага можно, это безобидно.
B) На копии/новом id (не ломая spec): стрелка с известным when: + строка dispatch → после Apply delegate/dispatch видит next. Стрелка с новым condition без правила — Apply недоступен ИЛИ после codegen появился stub, не пустой graph-only.
C) unknown when: — ошибка на стрелке, диск не пишется.
D) «Новый пак» с шаблона routing-state: на холсте не пустой status; предупреждение если нет orchestrator md.

Не применяй ломающий spec. Не редактируй expr. Не пиши тексты агентов.
```

### Разрыв, который фаза 6 должна закрыть

Фронта фаз 1–5 хватает, чтобы **править уже открытый пак** (клетки, cycle, ask, стрелки, таблица priority/when/next). Не хватает, чтобы:

- с пустого холста собрать новый исполняемый пайплайн (нужен `--init-pack`, не десять полей в инспекторе);
- записать только `graph.yaml` и ожидать, что роутер пойдёт по стрелке «нет контекста → find-context».

Пока save не соберёт `открытый пак + overlay графа/правил` и не синхронизирует dispatch/stub expr, скрипты ветку не выберут. Это шаг записи, не новое поле инспектора.

### Фаза 6 закрыта

Сделано: save-path не пишет «граф целиком». `POST /api/pack/validate` (слой schema + compile, без диска), `POST /api/pack/apply` (confirm → from-json + compile apply), `POST /api/pack/init` (`--init-pack` + template).
Сборка: `GET /api/pack` как base, overlay `graph` + `dispatch.rules` с холста, `registry` заново из клеток, `status` и `expr` с диска.
Стрелка с condition без строки dispatch — ошибка на стрелке, Apply скрыт. `unknown when:` — ошибка, диск не пишется.
Откат к предыдущему успешно применённому JSON. Новый пак — шаблон (routing-state / full-dispatch / orchestrator-only), не пустой холст; предупреждение если нет `.qwen/agents/<id>-orchestrator.md`.
Прогон: slug, SSE, Целевой/Факт/Время, restart — не ломали. spec YAML в этой сессии не применяли (validate label — зелёный).

Не трогать дальше: редактор `expr`, тексты `.qwen/agents`, `collectors.py` / `validate.py`, запуск Qwen с холста. v1 фаз больше нет.

---

## Что не входит ни в одну фазу (v1)

- Создание CLI-агента оркестратора из UI (только предупреждение «файла нет») — **снято сессией 3 full-codegen**: Apply пишет md из шаблона без silent overwrite
- Редактор текстов skills / domain agents (кроме orchestrator template)
- Формулы `edge_conditions.expr`
- Запуск оркестратора с холста
- Смешение live-таймлайна с редактором (оверлей прогона)

## Если сессия сбилась

Напиши: «Продолжи фазу N по pipeline-viewer/AUTHORING-UI-PHASES.md. Сначала прочитай authoring-contract.md и git diff pipeline-viewer/. Не начинай фазу N+1.»

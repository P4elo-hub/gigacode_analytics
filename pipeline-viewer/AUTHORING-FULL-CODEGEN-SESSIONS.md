# Полный codegen (вариант B) — фазы по сессиям

Одна большая задача = **четыре сессии**. В каждой копируй блок «Промпт» целиком. Не склеивай фазы в один чат.

Архитектурный план: Cursor plan `full_free-text_codegen` (свободный текст → pack-local analyzer + полный Apply).  
Предшественник UI: [AUTHORING-UI-PHASES.md](AUTHORING-UI-PHASES.md) (фазы 0–6 закрыты).

## Инварианты (все сессии)

- **Не трогать** ядро выбора шага в `scripts/`: delegate, dispatch, edge interpreter, хуки stale/sync, overlay semantics.
- Допустимо тонко: доки в `scripts/PIPELINE-*.md`, существующий codegen/authoring API, golden fixtures.
- Свободный текст на стрелке = **один bool-факт** + `instruction`; `expr` = `field … truthy`. Не парсить русский в AST. Не генерить GAP/SPEC-коллекторы.
- Петля «агент закончил» ≠ bool в routing-state; после шага JSON stale → снова `analyze-routing` (уже в движке).
- Не коммить, пока пользователь не попросил.

### Общий префикс (вставлять каждый раз)

```
Репозиторий: gigacode_analytics.

Читай перед кодом:
- pipeline-viewer/AUTHORING-FULL-CODEGEN-SESSIONS.md (этот файл, текущая фаза)
- pipeline-viewer/authoring-contract.md
- scripts/PIPELINE-PACK-AUTHORING.md
- scripts/PIPELINE-ROUTING-STATE.md
- .qwen/skills/analyze-routing/SKILL.md
- pipeline-viewer/pack_authoring_api.py

Правила:
- Делай ТОЛЬКО текущую фазу. Не «заодно» следующие.
- Движок выбора шага в scripts/ не переписывать.
- Не коммить, пока я не попросил.
- В конце: отметить фазу [x], 5–10 строк «сделано / не трогать следующей».
```

---

## Чеклист

- [x] Сессия 1 — pack-local `analyze-routing`
- [x] Сессия 2 — Apply/codegen: полный YAML + thin Python
- [x] Сессия 3 — оркестратор md + UI (bool vs loop-after-step)
- [x] Сессия 4 — пилот `spec-v2` + smoke/golden + регрессия `spec`

---

## Сессия 1 — pack-local analyze-routing

**Зачем.** Analyzer больше не прибит к `pipelines/spec/`. Читает `status_fields` из пака `--pipeline`.

### Что правится

- `.qwen/skills/analyze-routing/SKILL.md` (и зеркала `.gigacode` / `.opencode`, если они есть и должны совпадать)
- при необходимости тонкая передача `pipeline_id` в задании субагенту (оркестратор-шаблон / docs) — **без** смены алгоритма роутера
- доки: `scripts/PIPELINE-ROUTING-STATE.md` (SSOT = YAML текущего пака)

### Не трогать

- `pipeline_delegate.py`, dispatch, hooks, `pipelines/spec/routing_conditions.yaml` семантика полей
- фронт Apply, `spec-v2` перегенерация

### Критерий приёмки

1. В skill явно: источник полей = `pipelines/<pipeline_id>/routing_conditions.yaml` → `status_fields`.
2. Нет хардкода «только spec» / алгоритмов GAP как единственного пути в skill.
3. Для пака `spec` те же имена полей по-прежнему заполняются (они живут в YAML spec).
4. Регрессия golden spec не падает.

### Как проверить

```bash
# skill: есть путь pipelines/<pipeline_id>/routing_conditions.yaml, нет «только pipelines/spec»
rg -n "routing_conditions|pipeline_id|pipelines/spec" .qwen/skills/analyze-routing/SKILL.md

# регрессия dispatch (ядро не ломали — кейсы должны быть зелёные)
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --check
PYTHONPATH=scripts python3 -m unittest discover scripts -p '*_test.py'
PYTHONPATH=scripts python3 scripts/pipeline_dispatch_golden_test.py
```

Ручная проверка текста skill: для гипотетического пака `dev-agent` analyzer обязан брать поля из `pipelines/dev-agent/routing_conditions.yaml`, а не копировать GAP-инструкции из spec.

### Промпт сессии 1

```
Сессия 1 по pipeline-viewer/AUTHORING-FULL-CODEGEN-SESSIONS.md.
Только pack-local контракт analyze-routing. Движок scripts/ не переписывать.
Фронт Apply и spec-v2 не трогать.
В конце: чеклист [x], 5–10 строк handoff.
```

---

## Сессия 2 — Apply/codegen: полный YAML + thin Python

**Зачем.** После Apply пак содержит согласованный runnable YAML-контур + generic overlay Python, без дыр «есть when:, нет status_field».

### Что правится

- `pipeline-viewer/pack_authoring_api.py` (и при необходимости тонкие обёртки в `server.py`)
- CLI codegen, если Apply его вызывает (`scripts/pipeline_routing_codegen.py` / pack authoring) — только stubs/merge, не новый router
- генерация/гарантия в паке:
  - `graph` / `dispatch` / `registry` / `routing_conditions` (fields + edge_conditions + expr truthy)
  - `status.yaml` merge (routing-state template, без молчаливого копирования spec-артефактов)
  - `collectors.py` = generic overlay
  - тонкий `predicates.py` (reason из label/instruction)

### Не трогать

- skill analyze-routing (уже сессия 1)
- UI инспектора петель (сессия 3)
- массовая миграция `spec-v2` (сессия 4)
- доменные collectors GAP

### Критерий приёмки

**Универсальность (не «работает только на моём spec-v2»):**

Python в сессии 2 **не кодирует домен графа**. Уникальность графа живёт только в YAML (`when_id`, instruction, next, priority).

| Файл | Почему универсален |
|------|-------------------|
| `collectors.py` | Всегда один и тот же шаблон: `COLLECTORS = {"routing_state": overlay_collector}`. Overlay кладёт **любые** ключи из `routing-state.json` → status. Имена условий он не знает и знать не должен. |
| `predicates.py` | Либо тонкая генерация reason из `edge_conditions.*.label/instruction`, либо generic «верни label для when». Нет веток `if open_gaps`. Новый граф → новые when в YAML → reasons подтягиваются без правок шаблона collectors. |

Информации для сессии 2 **достаточно**: не нужно понимать смысл «GAP» или «PR review» — только «свободный текст → id + bool field + truthy expr + next из стрелки».

**Функциональные критерии:**

1. Стрелка со свободным текстом → после validate/apply: один и тот же `when_id` в `dispatch.rules`, `edge_conditions`, `status_fields`.
2. У нового условия есть `instruction` и `expr: field truthy`.
3. `collectors.py` на routing-state паке — overlay template; байт-в-байт/семантически тот же для пака A и пака B; нет GAP-парсера.
4. Петли «шаг завершён» не обязаны быть bool-полями (полный UX — сессия 3).
5. Compile/check пака после Apply проходит schema+compile layer.

**Собственные критерии приёмки исполнителя (обязательный тест универсальности):**

Недостаточно «открыл spec-v2 на фронте». Нужен **синтетический второй пак** (или fixture), независимый от analytics:

1. `--init-pack codegen-smoke --template routing-state` (или временный id).
2. Граф: `orchestrator → analyze-routing → step-alpha | step-beta | done` с двумя свободными текстами, например «нужен шаг альфа» / «нужен шаг бета».
3. Apply/codegen.
4. Проверки:
   - `collectors.py` == overlay template (как у любого routing-state пака).
   - В YAML появились два when_id; каждый в dispatch + edge_conditions + status_fields.
   - Фикстура JSON: только поле альфы `true` → `next == step-alpha`.
   - Фикстура: только бета `true` → `next == step-beta`.
   - Фикстура: оба false (и routing-state свежий) → не выбирает alpha/beta по этим when (обычно P5 analyze-routing или fallback пака).
5. Тот же сценарий не должен требовать правок `scripts/` engine.

Если зелёный только `spec-v2`, а синтетика красная — сессия 2 **не принята**.

### Как проверить

```bash
# на копии/тестовом id (не ломая spec), либо на spec-v2 dry-run validate:
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --export-json spec-v2 | head

# после Apply с фронта или --from-json:
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --check spec-v2

# универсальность: синтетический пак + две фикстуры bool→next
# (конкретная команда — pytest/golden, которые добавят в сессии 2)
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --check codegen-smoke
```

В браузере: Схема → любой пак → изменить подпись условия → Проверить → Применить → id совпали в трёх местах; `collectors.py` на месте и совпадает с шаблоном overlay.

### Промпт сессии 2

```
Сессия 2 по pipeline-viewer/AUTHORING-FULL-CODEGEN-SESSIONS.md.
Только Apply/codegen: полный YAML + thin Python. Движок выбора шага не трогать.
Skill analyze-routing и UI петель — не эта сессия.
Не применяй ломающий pipelines/spec без явного «да».
В конце: чеклист [x], handoff.
```

---

## Сессия 3 — оркестратор md + UI

**Зачем.** Запуск пака без ручного копирования agent md; на холсте видно: условие-факт vs «после завершения шага».

### Что правится

- Apply: запись `.qwen/agents/<id>-orchestrator.md` из шаблона `scripts/fixtures/pack_authoring/orchestrator-agent.md` (зеркала CLI — по политике репо; не затирать без overwrite)
- `pipeline-viewer/static/app.js` (+ html/css по необходимости):
  - модель «условие = bool для analyzer»
  - петля к `analyze-routing`: флаг/kind «после шага», не свободный текст-условие
  - чеклист runnable после Apply
- доки: этот файл + при необходимости `AUTHORING-UI-PHASES.md` / `PIPELINE-PACK-AUTHORING.md`

### Не трогать

- ядро scripts/ router
- переписывание всех domain skills
- финальный golden `spec-v2` (сессия 4) — можно лёгкий smoke UI

### Критерий приёмки

1. Apply нового/обновлённого пака предлагает/создаёт orchestrator md; повторный Apply не молча затирает ручные правки без флага.
2. На UI нельзя спутать loop-after-step с bool-condition.
3. После Apply виден чеклист: YAML ok, collectors, orchestrator, pack-local analyzer.
4. Режим Прогон не сломан.

### Как проверить

В браузере:

1. Схема → пак → Применить → появился/обновился `.qwen/agents/<id>-orchestrator.md`.
2. Стрелка к `analyze-routing` после рабочего шага: тип «после завершения», в YAML **нет** `when: has_agent_zakonchil_…`.
3. Стрелка к следующему агенту: свободный текст → bool field + instruction.
4. Прогон: живой slug как раньше (SSE / Целевой/Факт/Время).

```bash
test -f .qwen/agents/spec-v2-orchestrator.md || test -f .qwen/agents/<id>-orchestrator.md
rg -n "on_step|after|analyze-routing" pipeline-viewer/static/app.js | head
PYTHONPATH=scripts:pipeline-viewer python3 scripts/pack_authoring_session3_test.py -q
```

### Промпт сессии 3

```
Сессия 3 по pipeline-viewer/AUTHORING-FULL-CODEGEN-SESSIONS.md.
Оркестратор md из шаблона + UI bool vs loop-after-step + чеклист runnable.
Движок scripts/ и сессию 4 (golden) не делать.
В конце: чеклист [x], handoff.
```

### Сессия 3 закрыта (handoff)

Сделано:

- Apply пишет `.qwen|gigacode|opencode/agents/<id>-orchestrator.md` из `scripts/fixtures/pack_authoring/orchestrator-agent.md`; повтор без `overwrite_orchestrator: true` не затирает ручные правки.
- UI: тип перехода **условие-факт (bool)** vs **после завершения шага → analyze-routing** (`after_step: true`, kind=loop, без when:); codegen/strip не изобретает `has_agent_zakonchil_*`.
- После Apply — чеклист runnable: YAML / collectors / orchestrator / pack-local analyzer.
- Тест: `scripts/pack_authoring_session3_test.py`.

Не трогать следующей (сессия 4):

- миграция `pipelines/spec-v2` (убрать уже залипшие `agent_zakonchil_*` bool из YAML)
- golden `spec-v2` + регрессия `spec`
- ядро router / hooks

---

## Сессия 4 — пилот spec-v2 + golden + регрессия spec

**Зачем.** Доказать end-to-end: нарисованный пак → Apply → delegate выбирает шаг по bool из routing-state.

### Что правится

- `pipelines/spec-v2/**` перегенерация/миграция (убрать бессмысленные `agent_zakonchil_*` bool)
- `.qwen/agents/spec-v2-orchestrator.md` (если не создали в сессии 3)
- `scripts/fixtures/dispatch_golden/spec-v2/` (1–2 case или `WAIVER.md`)
- прогон регрессии `spec` golden

### Не трогать

- перепись engine
- новые фичи UI сверх сессии 3

### Критерий приёмки

1. `pipeline_compile.py --check spec-v2` ок.
2. Golden: «все domain bool false» → next `analyze-routing` (P5); «один bool true» → ожидаемый `next` из dispatch.
3. `pipeline_compile.py --check spec-v2` + существующие golden spec-v2 зелёные.
4. Ручной/скриптовый smoke: в `routing-state.json` выставлен один pack field → `pipeline_delegate` / dispatch выбирает соответствующий шаг.

### Как проверить

```bash
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --check spec-v2

# golden (путь уточнить по PIPELINE-GOLDEN.md, если обёртка другая)
ls scripts/fixtures/dispatch_golden/spec-v2/
PYTHONPATH=scripts python3 -m unittest discover scripts -p '*_test.py'
PYTHONPATH=scripts python3 scripts/pipeline_dispatch_golden_test.py

# smoke dispatch: подставить fixture JSON fields с одним true
PYTHONPATH=scripts python3 scripts/pipeline_delegate.py --pipeline spec-v2 --slug <test-slug> --dry-run
# (если dry-run нет — смотреть next_step в выводе / routing overlay по принятому CLI)
```

Ручная: на тестовом slug записать `Feature-writing/<slug>/<slug>-routing-state.json` с одним `has_…: true` по полю из `spec-v2` → следующий шаг совпадает с `dispatch.yaml`.

### Промпт сессии 4

```
Сессия 4 по pipeline-viewer/AUTHORING-FULL-CODEGEN-SESSIONS.md.
Пилот spec-v2 + golden + регрессия spec. Движок не переписывать.
В конце: чеклист [x], итог «B1 закрыт / что осталось на B2».
```

### Сессия 4 закрыта (handoff)

Сделано:

- `pipelines/spec-v2`: убраны `agent_zakonchil_*` / `eshche_odno_*`; петли → `after_step: true`; domain bool + stub `instruction`; messages про routing-state dispatch.
- Golden: `scripts/fixtures/dispatch_golden/spec-v2/` (`01` all-false → analyze-routing, `02` find_context → context-researcher, `03` missing JSON → P5).
- Регрессия: `pipeline_compile --check` PASS; dispatch golden **42/42** (spec + spec-v2 + …); coverage packs OK.
- Smoke: `pipeline_delegate --pipeline spec-v2` — all false → `analyze-routing`; `find_context: true` → `context-researcher`.
- Оркестратор md уже был (сессия 3).

**B1 закрыт** (четыре сессии варианта B / full free-text codegen).

Осталось на **B2+** (вне скоупа четырёх сессий):

- Редактор сложных `expr` / AND-UI на холсте
- Генерация доменных collectors из текста
- Автогенерация текстов writer/reviewer skills
- Перепись hooks / dispatch engine
- Уточнение analyzer `instruction` у `spec-v2` status_fields (сейчас stub)

---

## Если сессия сбилась

Напиши: «Продолжи сессию N по pipeline-viewer/AUTHORING-FULL-CODEGEN-SESSIONS.md. Сначала прочитай этот файл и git diff затронутых путей. Не начинай сессию N+1.»

## Вне скоупа всех четырёх сессий (B2+)

- Редактор сложных `expr` / AND-UI на холсте
- Генерация доменных collectors из текста
- Автогенерация текстов writer/reviewer skills
- Перепись hooks / dispatch engine

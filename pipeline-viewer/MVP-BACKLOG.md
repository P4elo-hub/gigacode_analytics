# MVP backlog — универсальная очерёдность агентов

Документ для обсуждения в следующих чатах.

## Скоуп

**В скоупе:** задавать и исполнять порядок вызовов уже существующих агентов  
(Схема → Apply → `--pipeline <id>` → Прогон).

**Не в скоупе:**
- codegen рабочих агентов / skills;
- редактор `expr`;
- полный отказ от analytics-полей в `feature_status` (можно жить с Feature-writing, пока не нужен другой корень — см. #10).

## Решение продукта (зафиксировано)

- Эталон для регрессии и примеров: **`spec-v2`** (не `pipelines/spec`). Это **не** silent default в CLI/viewer.
- **Нет скрытого default pipeline.** При 3–4 графах id всегда явный: оркестратор свой, старт с `--pipeline <id>`, в active-task то же поле. Не передал id → **ошибка**, а не «подставим spec / spec-v2».
- Пак **`pipelines/spec` будет удалён** (пункт **#0**). После удаления регрессия = `spec-v2` + его golden + пилот `my-v2-demo`.
- Имя артефакта `spec` в `stale_vs` / analytics — это **не** id пака; путаница имён остаётся проблемой шаблона (#1), пока не нейтрализуем.

## Ориентир готовности

~**85%** на момент Session 4 + pack-agnostic Прогон.  
Доказательство: `pipelines/spec-v2/`, `Feature-writing/my-v2-demo/`, `scripts/fixtures/dispatch_golden/spec-v2/`.

Рекомендуемый порядок сессий: **#0 → #3 → #2 → #1**, дальше по таблице ниже.  
(#0 убирает пак `spec` и хардкоды; #3 закрепляет «id всегда явный / fail-fast».)

## Защита от регрессии (каждая сессия)

Перед коммитом минимуум:

```bash
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --check
# если трогал dispatch / routing / overlay:
PYTHONPATH=scripts python3 scripts/pipeline_dispatch_golden_test.py --pipeline spec-v2
# smoke next-step (подставь актуальный slug при необходимости):
PYTHONPATH=scripts python3 scripts/pipeline_delegate.py --pipeline spec-v2 --slug my-v2-demo --dry-run
```

Правила:
- Одна сессия = один пункт (или явно названная группа из этого файла).
- Не рефакторить соседнее «заодно».
- Пока `pipelines/spec` ещё на диске — **не Apply / не «улучшать» его YAML** в рамках этих пунктов; цель — вынести зависимости и удалить (#0).
- UI-only (#2, #7, #8) почти не ломает runtime; #0 / #3 — отдельная осторожная сессия.

---

## #0 — Убрать `pipelines/spec` и silent default

**Проблема.** Код, viewer, golden и доки завязаны на id `spec` как на «главный» пак + тихий `DEFAULT_PIPELINE_ID = "spec"`. Dual-path (`if pipeline === "spec"`) и подстановка пака без флага — главный источник «сломал формат работы».

**Зачем.** Несколько графов → id всегда из старта/оркестратора; эталон регрессии (`spec-v2`) не должен подставляться молча.

**Что сделать.**
- Резать внутри #0 на подшаги; это один тематический чат, но идти по чеклисту ниже.
- **Шаг 0.1 — не удалять `pipelines/spec/` в первый час.** Сначала убрать поведение «флаг не передали → вот этот пак»: CLI/delegate/dispatch/hooks, нет `--pipeline` и нельзя вывести id из active-task → **fail с понятной ошибкой**.
- **Шаг 0.2 — заменить бывший default явным id.** Где тесты/доки/команды раньше полагались на default, передавать `--pipeline spec-v2`; `spec-v2` = эталон регрессии, не default runtime.
- **Шаг 0.3 — viewer без магического пака.** Не открывать default-пак; вкладка/slug только из явного выбора или из `active-task.pipeline` у выбранного slug.
- **Шаг 0.4 — вычистить UI-ветки `pipeline === "spec"`.** Validation работает для всех паков по данным API; legacy-сателлиты не нужны.
- **Шаг 0.5 — вычистить runtime-хардкоды `pipeline == "spec"` в `scripts/`.** Проверить validation gate, restart, protected packs, сообщения и любые fallback-и на `DEFAULT_PIPELINE_ID`.
- **Шаг 0.6 — зелёные перед удалением.** Обязательно: `compile --check spec-v2`, golden `spec-v2`, dry-run `my-v2-demo`.
- **Шаг 0.7 — только после зелёных удалить legacy.** Удалить `pipelines/spec/`; решить судьбу `scripts/fixtures/dispatch_golden/spec/` (удалить вместе с паком или архив вне CI).
- **Acceptance.** Прогнать привычный старт оркестратора с явным `--pipeline spec-v2`; нет `--pipeline` и нет id в active-task должны падать понятной ошибкой.

**Где смотреть.** `scripts/pipeline_pack.py` / `pipeline_runtime.py` (`DEFAULT_PIPELINE_ID`), argparse defaults, `pipeline-viewer/static/app.js`, `pipeline-viewer/server.py`, `PROTECTED_PACKS`, `scripts/fixtures/dispatch_golden/`.

**Риск.** Высокий — отдельная сессия, без UI-косметики. Согласовать с #3 (guard), не дублировать логику в двух местах.

---

## #1 — Шаблон нового пака без analytics-наследия

**Проблема.** При `--init-pack` / template `routing-state` часто остаётся:
- `stale_vs: ["spec"]` — id **артефакта** «файл спеки», не пак; у нового пака такого артефакта может не быть → mtime-refresh молчит;
- путь routing-state зашит под `Feature-writing/{task_id}/…`.

**Зачем.** Новый пак (в т.ч. «dev») не должен стартовать с чужими analytics-допущениями.

**Что сделать.**
- В stub/template: нейтральный `stale_vs` (например `main`, или `[]` + опора на `after_step`).
- Не хардкодить analytics-имена артефактов в init.
- Коротко в authoring-доке: что поправить после init.

**Где смотреть.** `scripts/pipeline_pack_authoring.py` (`_routing_conditions_stub`, `_template_routing_state`), `scripts/PIPELINE-PACK-AUTHORING.md`.

---

## #2 — Прогон: validation UI для любого пака

**Проблема.** Workflow validate в сайдбаре / часть баннеров завязаны на `pipeline === "spec"`. После #0 без этого Прогон «ослепнет».

**Зачем.** Для `spec-v2` и любого следующего пака — те же block/warn/ok и next-step подсказки.

**Что сделать.**
- Показывать validation-panel для любого `pipeline`, у которого API отдаёт `validation`.
- Нейтральные тексты баннера (без «spec готов» / PASS WITH GAPS как универсальной формулы).

**Где смотреть.** `pipeline-viewer/static/app.js` (`renderValidationPanel`, `renderValidationBanner`).

---

## #3 — Guard: CLI `--pipeline` ↔ active-task (без silent default)

**Проблема.** Можно запустить с одним id, а в `.pipeline-active-task.json` — другой, или поле пустое и старый код подставляет default. Viewer и роутинг расходятся.

**Зачем.** При 3–4 графах единственный безопасный контракт: **id всегда явный и совпадает** в CLI, active-task и оркестраторе.

**Что сделать.**
- Нет `pipeline` в CLI и нельзя надёжно взять из active-task → ошибка (см. #0), не default.
- `active-task.pipeline` ≠ `--pipeline` → fail-fast (не тихий merge).
- При старте задачи всегда писать `pipeline` в active-task из CLI / оркестратора.
- Внутренние хелперы без id не должны молча звать `DEFAULT_PIPELINE_ID` в runtime-пути (тесты могут передавать id явно).

**Где смотреть.** `scripts/pipeline_delegate.py`, `scripts/pipeline_active_task.py`, hooks before/after subagent, `pipeline-viewer/server.py` (`pipelines_for_slug`).

---

## #4 — Чеклист runnable после Apply заметнее на фронте

**Проблема.** API уже отдаёт readiness (YAML / collectors / orchestrator / pack-local analyzer); на UI легко пропустить.

**Зачем.** Сразу видно, runnable ли пак после Apply.

**Что сделать.** После успешного Apply показать чеклист (ok/fail по пунктам) на вкладке Схема.

**Где смотреть.** `pipeline-viewer/pack_authoring_api.py`, `pipeline-viewer/static/app.js` (Apply success UI).

---

## #5 — Приоритеты стрелок без путаницы с engine-правилами

**Проблема.** В таблице приоритетов рядом пользовательские bool-правила и служебные (`routing_state_needs_refresh` и т.п.). Drag-reorder может сломать refresh analyzer.

**Зачем.** Менять очерёдность доменных условий, не трогая каркас.

**Что сделать.**
- Отделить engine/core rules (readonly или отдельная секция).
- Drag-reorder только для пользовательских dispatch-правил.

**Где смотреть.** Schema priority table в `app.js`; `dispatch.yaml` / `edge_conditions` после Apply.

---

## #6 — Один источник правды для layout (draft vs YAML)

**Проблема.** Layout в `pipelines/<id>/.authoring-draft.json` (для `spec-v2` уже в git) и/или позиции при Apply/YAML — два источника → рассинхрон.

**Зачем.** «Как нарисовали» одинаково у всех после clone.

**Что сделать (выбрать одно).**
- A: при Apply писать `positions` в `graph.yaml` (или отдельный layout-файл пака);
- B: контракт «draft в git = SSOT layout» + дока «коммить draft после расстановки».

**Где смотреть.** `pipelines/spec-v2/.authoring-draft.json`, `server.py` (`authoring_draft_path`), Apply в `pack_authoring_api.py`.

---

## #7 — Убрать legacy-сателлиты analyze-routing на «Целевом»

**Проблема.** Ветка `pipeline === "spec"` рисует analyzer овалами под шагами; у `spec-v2` — обычная клетка. После удаления `spec` dual UX не нужен.

**Зачем.** Один ментальный модель = как в Схеме (клетка `analyze-routing`).

**Что сделать.**
- Удалить satellite-path из `buildTargetElements` / `satelliteVisual` (или оставить мёртвым кодом не надо — вычистить).
- Легенда Прогон: квадрат = шаг, без «овал только для старого spec».

**Где смотреть.** `app.js` (`buildTargetElements`, `satelliteVisual`, `updateInfraPanel`).  
**Зависимость.** Логично сразу после или вместе с хвостом #0.

---

## #8 — Тайминги: человекочитаемые подписи и легенда

**Проблема.** Цвета уже pack-agnostic; подписи могут быть сырыми id без label пака.

**Зачем.** На «Время» сразу видно, какой агент сколько ел.

**Что сделать.**
- Подписи из `label` / registry пака.
- Короткая легенда цветов.

**Где смотреть.** `app.js` (`TIMING_STEP_COLORS`, `TIMING_PALETTE`), `scripts/pipeline_timings.py`.

---

## #9 — Divergence / restart для всех паков

**Проблема.** Divergence overlay и часть restart UX ещё гейтятся / заточены под старый `spec`.

**Зачем.** Отладка «факт ≠ целевой dispatch» и перезапуск с шага на `spec-v2` и дальше.

**Что сделать.**
- Не гейтить divergence по id `spec`.
- Restart только из `restartable_steps_by_pipeline[pid]` (проверить все UI-ветки).

**Где смотреть.** `app.js`, `scripts/pipeline_restart.py`, `server.py` (`restartable_steps_by_pipeline`).  
**Зависимость.** После #0 default/`spec` cleanup, иначе легко оставить скрытый fallback.

---

## #10 — Корень задач вне Feature-writing (дока + явная настройка)

**Проблема.** По умолчанию routing-state/main ищутся под `Feature-writing/…`. Другой домен (`Dev-tasks/` и т.п.) без правки `status.yaml` «невидимый» для роутера.

**Зачем.** Новый пак без analytics-корня — без чтения исходников.

**Что сделать.**
- После init в UI/доке: «укажи path артефактов» (`status.artifacts.*.path`).
- Пример не-Feature-writing пака в доке.
- Опционально: поле в init-wizard.

**Где смотреть.** `pipelines/<id>/status.yaml`, `scripts/PIPELINE-ROUTING-STATE.md`, templates в `pipeline_pack_authoring.py`.

---

## Как резать сессии

| Сессия | Пункты | Комментарий |
|--------|--------|-------------|
| A | **#0** | Удаление `spec` + убрать silent default |
| B | **#3** | Guard CLI ↔ active-task / fail-fast (можно хвостом #0) |
| C | **#2 + #7** | Прогон UX pack-agnostic |
| D | **#1** (+ кусок **#10** про шаблон путей) | Templates / docs |
| E | **#4 + #5** | Схема |
| F | **#6** | Нужна развилка A vs B |
| G | **#8 + #9** | Наблюдение / restart |
| H | хвост **#10** | Если не закрыли в D |

---

## Промпт для другого чата

```
Читай pipeline-viewer/MVP-BACKLOG.md.
Мир: без pipelines/spec; spec-v2 = эталон регрессии, НЕ silent default;
pipeline id всегда явный (CLI / active-task), иначе fail-fast.
Возьми пункт #<N> и сделай только его.
Не расширяй scope. Не «улучшай» pipelines/spec — цель его убрать (#0) или он уже удалён.
В конце: зелёная регрессия из раздела «Защита от регрессии»; обнови статус пункта в этом файле.
```

## Статусы

| # | Статус |
|---|--------|
| 0 | done |
| 1 | done |
| 2 | done |
| 3 | done |
| 4 | todo |
| 5 | todo |
| 6 | todo |
| 7 | done |
| 8 | todo |
| 9 | todo |
| 10 | todo |

# Контракт редактора схемы (фаза 0)

Источник правды пака: `pipelines/<id>/*.yaml` ↔ JSON `scripts/pipeline_pack_schema.json`.
CLI: `pipeline_compile.py --export-json <id>` / `--from-json` / `--catalog`.
Этот файл — модель холста. Не описание прогона.

Проверено 2026-09-21 (JSON не менялся):

```
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --catalog
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --export-json spec
```

spec export: `id=spec`, 12 nodes, 37 edges, `write-feature.cycle` без `calls`, `ask:true` на трёх resolve-*, `dispatch.rules` = 17.

---

## 1. Pack JSON → фигура на холсте

Canvas читает **`graph.nodes` / `graph.edges`**. Остальное — инспектор/таблицы, не отдельные фигуры.

| JSON | Холст v1 | Как узнать |
|------|----------|------------|
| `id` | какой пак открыт (`spec` / `calibration` / …) | kebab-case = `pipelines/<id>/` |
| `graph.label` | заголовок схемы | строка |
| `graph.orchestrator` | id клетки-оркестратора; ровно одна | должен совпадать с `nodes[].id` kind=orchestrator |
| `nodes[].id` | стабильный id клетки | уникален в паке |
| `nodes[].label` | подпись | иначе `id` |
| `nodes[].subagent` | агент в инспекторе | `null` = оркестратор-owned / без task |
| `edges[].from/to` | стрелка | оба конца — существующие id |
| `edges[].kind` | стиль стрелки | `main` / `branch` / `loop` |
| `edges[].label` | подпись стрелки | человеческий текст |
| `edges[].condition` | id условия (`when:`), первое из списка | палитра catalog |
| `edges[].conditions` | все `when:` на одной стрелке (если больше одного) | разные правила на один next |
| `edges[].condition_label` | запасная подпись | codegen может slug → `condition` |
| `registry.step_to_subagent` | не фигура | синхрон с `nodes[].subagent` при save |
| `registry.orchestrator_owned` | не фигура | шаг без внешнего task (spec: `write-feature`) |
| `dispatch.rules[]` | не стрелки | таблица приоритетов (фаза 5) |
| `routing_conditions.edge_conditions` | не фигуры | SSOT `expr` + `dispatch.priority/next`; **expr не рисуем** |
| `status.*` | не рисуем в v1 | артефакты/коллекторы |

### Типы клеток

В JSON `kind` ∈ `orchestrator` \| `step` \| `terminal` \| `meta`.
**cycle и ask — не kind**, а флаги на `step`. Инспектор фазы 3 мапит их в UI-kind.

| UI-фигура | JSON | Пример spec | Рисовать |
|-----------|------|-------------|----------|
| Оркестратор | `kind: orchestrator`, id = `graph.orchestrator` | `spec-orchestrator` | эллипс (как прогон) |
| Обычный шаг | `kind: step`, нет `cycle`, нет `ask` | `find-context` | прямоугольник |
| Cycle (составная) | `kind: step` + объект `cycle` | `write-feature` | один квадрат; внутренности — фаза 4, не вложенный граф |
| Ask | `kind: step` + `ask: true` | `resolve-gaps` | шаг + пометка «пауза; apply без смены шага» |
| Terminal | `kind: terminal` | `done` (label `PASS`) | ромб |
| Meta | `kind: meta` | `archive-session` | как шаг, мельче; не ask/cycle |

`cycle` (spec `write-feature`): `persistent`, `assemble`, `param`, `folder`, `out`, `item_file`, `close: on_done`. `calls` нет → runtime подставит каталог блоков. Между `calls` **нет** рёбер и `when:`.

Ребро в пустоту запрещено. Один оркестратор. `ask:true` только на шаге.

Координаты клеток **нет в JSON** — черновик клиента (фаза 2+).

---

## 2. Вкладка «Схема» ≠ `GET /api/graph`

| | Прогон (`/api/graph`) | Схема (редактор пака) |
|--|----------------------|------------------------|
| Вопрос | что сделано по **slug** | как устроен **pack** |
| Вход | `?slug=&pipeline=&run_id=` | `pipeline` id, без slug |
| Данные | compiled schema + run-log + events + dispatch snapshot | `--export-json` / YAML pack |
| Клетки | + `state`, цвет, `x/y` layout, `routing-sat` | только pack nodes; без satellite, без Целевой/Факт |
| SSE | `/api/stream` | нет |
| Клик | sidebar шага задачи, restart | инспектор JSON (с фазы 3); клик не пишет YAML |
| Переключатели | Целевой/Факт/Время, slug | spec\|calibration (из catalog), не задача |
| Источник | `build_pipeline_graph.py` | `export_pack_json()` |

`/api/graph` не ломать. `/api/config`.pipelines сейчас захардкожен `spec`+`calibration`; список паков для «Схемы» — `GET /api/catalog` → `pipelines[]` (есть ещё `routing-poc`).

---

## 3. Что уже есть

| Штука | Где | Для UI |
|-------|-----|--------|
| `GET /api/catalog` | `server.py` → `build_catalog()` | палитра: `agents` (union CLI), `skills`, `steps`, `predicates`, `routing_conditions` (без `expr`). `catalog_version: 2` |
| `--catalog` | `pipeline_compile.py` | тот же JSON, что HTTP |
| `--export-json <id>` | `export_pack_json` | полный пак: graph + dispatch + status + registry [+ routing_conditions] |
| `--from-json FILE` | `validate_pack_json` (слой 1) → пишет YAML → сразу `--apply` (слой 2) | фаза 6; **нет dry-run** |
| Schema | `scripts/pipeline_pack_schema.json` | слой 1; Python — subset walker, не пакет `jsonschema` |
| Прогон | `/api/graph`, `/api/stream`, restart, slug | не трогать |

Слои валидации (не смешивать):

1. **Schema** — форма `id` / `graph` / `status` / `registry`. Не проверяет `when:` и файлы агентов.
2. **Compile** `validate_source` — рёбра, агенты в каталоге, `when:` в predicates, dispatch next.

---

## 4. Чего не хватает (HTTP) — не реализовывать здесь

**Фаза 1 (read-only схема)**

- `GET /api/pack?pipeline=<id>` — обёртка `export_pack_json`; 404 если пака нет.
- Список паков уже в catalog; не использовать `/api/graph`.

**Фаза 6 (проверить / применить) — сделано**

Сборка: `base = export_pack_json(id) | --init-pack` → overlay `graph` + `dispatch.rules` → `registry` из клеток → `status` и `expr` с диска.

- `POST /api/pack/validate` — слой 1 + слой 2 без записи. Ошибки с `node` / `edge` / `priority`.
- `POST /api/pack/apply` — тот же payload, `confirm: true` → `apply_pack_json` + compile apply. Неизменённые YAML (семантика) не перезаписываем, чтобы не снести комментарии.
- `POST /api/pack/init` — `--init-pack` (routing-state | full-dispatch | orchestrator-only). Пустой холст в `--from-json` нельзя.
- Стрелка с `condition` / `conditions` без `dispatch.rules.when` — ошибка на стрелке, Apply скрыт. `unknown when:` — ошибка, диск не пишется. Каждому when: нужен ряд в таблице.

Не нужны: редактор `expr`, правка доменных collectors. Orchestrator md — пишет Apply из шаблона (сессия 3).

---

## 5. v1 сознательно не рисует

| Не рисуем | Где живёт | Зачем не трогать |
|-----------|-----------|------------------|
| Тексты скиллов / domain-агентов | `.qwen|gigacode|opencode/skills|agents/*.md` | catalog даёт только имена; orchestrator md — Apply из шаблона |
| Формулы `expr` | `routing_conditions.edge_conditions.*.expr` | палитра id + label; не редактор формул |
| Запуск Qwen/GigaCode с холста | runtime loop | это вкладка Прогон |
| Оверлей live-таймлайна на схему пака | `/api/graph` history | два режима экрана, не смесь |
| `status_fields.instruction` / collectors.py | status YAML | вне холста; Apply пишет generic overlay |
| Координаты в YAML | — | localStorage / черновик |
| Новый пак «с нуля» без шаблона | `--init-pack` | фаза 6: сначала template, потом overlay холста |

**Сессия 3 (full codegen):** на стрелке UI различает bool-условие analyzer и `after_step` петлю к `analyze-routing` (без when:). Apply создаёт `<id>-orchestrator.md` без silent overwrite.

---

## Фаза 0 закрыта. Фаза 1 — так

1. Сначала этот файл. UI: режимы **Прогон** | **Схема**; Прогон = текущий viewer (slug, SSE, Целевой/Факт/Время, restart).
2. «Схема»: выбор пака из catalog (`spec`, `calibration`, …), **без** селектора задачи.
3. Граф из `--export-json` (лучше тонкий `GET /api/pack` — это единственная допустимая HTTP-обёртка фазы 1). Не `/api/graph`.
4. Клетки: оркестратор / шаг / terminal (+ meta как шаг). Стрелки с `label` или `condition`. cycle и ask — та же клетка, пометка в tooltip.
5. Клики не пишут YAML. Нет палитры, drag, save, раскрытия cycle, таблицы dispatch.
6. Не менять engine Python, кроме GET-обёртки export. Не коммитить, пока не попросили.
7. Браузер: Прогон — живой slug как раньше; Схема — spec и calibration; F5 не сбрасывает режим нелепо.

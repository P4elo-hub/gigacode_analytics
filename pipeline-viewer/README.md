# Pipeline Viewer

Near-real-time граф spec/calibration пайплайна в браузере.

## Запуск

**Терминал 1** — агент (GigaCode / Qwen / OpenCode):

```bash
/write-feature …
```

Оркестратор перед каждым `task` обязан вызывать:

```bash
python3 scripts/pipeline_delegate.py <slug> --cli qwen
```

и делегировать **только** `task.subagent_type` из JSON (см. `pipeline-enforcement`).

**Терминал 2** — viewer (из корня workspace):

```bash
cd /path/to/gigacode_analytics
./pipeline-viewer/start.sh
```

Или без очистки старых процессов:

```bash
python3 pipeline-viewer/server.py
```

**Откройте URL из вывода терминала** (часто `http://127.0.0.1:8765/`, но если порт занят — `:8766`, `:8767`…).

> Не открывайте `index.html` как файл.  
> Не используйте `:8765`, если в терминале написано другой порт — там старый viewer и будет «API недоступен».

В UI:
- **Задача** — список slug (`Feature-writing/`; с телеметрией — отдельная группа)
- **Spec / Calibration** — две вкладки, разные графы для одной задачи
- Без телеметрии показывается **схема** (все pending); с logs — реальные статусы
- Выбор сохраняется в браузере
- **Клик по узлу** — подробности шага в sidebar; **наведение** — краткий tooltip
- **Перезапустить с этого шага** — после клика на узел: dry-run список файлов,
  удаление downstream-арtefactов, marker `.pipeline-restart.json`, команда для CLI
- **Целевой / Факт** — переключатель над графом: схема с ветками vs линейная
  цепочка реальных вызовов (#1 → #2 → …). Оранжевые рёбра = переход ≠ schema
- **Проходы — факт**: хронология всех вызовов subagent (×N на узле = сколько раз)
- **Dispatch / расхождения** (вкладка Spec): сравнение с `pipeline_dispatch.py`.
  Расхождения — **только при клике на узел** (жёлтая/оранжевая рамка). Фиолетовая =
  dispatch next
- **Workflow validate** (вкладка Spec): баннер под header + блок в sidebar —
  `pipeline_validate.py` (block/warn/ok, `workflow_fix`). Обновляется по SSE после
  SubagentStop hook (`append_run_log` → ingest → validate)
- **Целевой граф** — только содержательные шаги spec (find-context … PASS). Hook,
  validate, set_active_task — в sidebar «Инфраструктура», не отдельные узлы
- На вкладке **Calibration** — excerpt из `human-review.md`, `delta-analysis.md`, `proposals.md` и т.д.

Опционально slug по умолчанию:

```bash
python3 pipeline-viewer/server.py --slug composite-active-order-commission
```

## Опции CLI

```bash
python3 pipeline-viewer/server.py \
  --slug my-feature \
  --workspace /path/to/gigacode_analytics \
  --pipeline spec \
  --port 8765
```

| Флаг | Описание |
|------|----------|
| `--slug` | Slug по умолчанию (необязательно) |
| `--workspace` | Корень workspace |
| `--pipeline` | Вкладка по умолчанию: `spec` \| `calibration` |
| `--port` | Порт (default 8765) |

## API

| Endpoint | Описание |
|----------|----------|
| `GET /api/slugs` | Список фич и наличие logs |
| `GET /api/graph?slug=X&pipeline=spec` | Snapshot графа |
| `GET /api/stream?slug=X&pipeline=calibration` | SSE live updates |

## Откуда данные

| Файл | Роль |
|------|------|
| `agent-logs/<slug>/runs/<run-id>/run-log.jsonl` | Шаги оркестратора (ok/fail/retry) |
| `events.jsonl` | agent.spawn → выполненные шаги |

**Target-граф (по умолчанию):** все `run-NNN` одного slug **склеиваются** по времени
(`run_id=auto`). Текущий run — для live/metrics (badge `runs run-001→run-002 · live run-002`).
Один run: `?run_id=run-001`.
| `metrics.json` | Статистика в sidebar |

Обновление: poll каждую **1 секунду** (SSE).

**Окраска:** `events.jsonl` → ok; `run-log.jsonl` → fail/retry; **running** только при живой сессии (&lt; 3 мин).

## CLI без UI

```bash
python3 scripts/build_pipeline_graph.py my-feature --pretty
python3 scripts/build_pipeline_graph.py my-feature --pipeline calibration --pretty
```

## Зависимости

Только **Python 3 stdlib**. Cytoscape.js с CDN.

## Troubleshooting

**Port in use** — сервер пробует 8766, 8767… или `kill` старый процесс:

```bash
lsof -i :8765
kill <PID>
```

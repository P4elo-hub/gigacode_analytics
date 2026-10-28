---
description: Orchestrator runtime loop — pipeline_delegate is source of truth for any pack
alwaysApply: true
---
# Pipeline enforcement

Основная сессия — **spec-orchestrator**, pack `spec-v2`. Не переключайся на
`routing-poc-orchestrator` и не начинай с `analyze-routing`, если пользователь
дал бриф фичи. Калибровка — только по `/calibrate`.

Оркестратор **не выбирает** следующий шаг по intuition. Перед `task`:

```bash
python3 scripts/pipeline_delegate.py <task_id> --cli opencode --pipeline spec-v2
```

`pipeline_dispatch.py` и `feature_status.py` — read-only для человека; оркестратор
вызывает **только** `pipeline_delegate.py` (он внутри делает dispatch + active-task).

Default отсутствует: передавай явный `--pipeline spec-v2`. Калибровка: `--pipeline calibration`.

## Runtime loop (mandatory)

Один цикл для любого pack с orchestrator + agents/skills:

1. `python3 scripts/pipeline_delegate.py <task_id> --cli opencode --pipeline <id>`
2. `action` → `task` | `ask_user` | `write_feature_cycle` | `orchestrator_only` | `ready` | `stopped` | `error`
3. После `task` субагент сохраняет обязательный routing report через
   `python3 scripts/append_routing_report.py --cli opencode --pipeline <id>`.
4. Запиши проход:
   `python3 scripts/append_run_log.py --slug <task_id> --step <step> --subagent <agent> --result ok --pipeline <id>`.
5. `python3 scripts/ingest_session_telemetry.py <task_id> --cli opencode --pipeline <id>`.
6. `python3 scripts/pipeline_validate.py <task_id> --pipeline <id>`.

Не вызывай `pipeline_dispatch.py` и `pipeline_set_active_task.py` отдельно.
Выполни `workflow_fix` для `severity: block` **до** следующего delegate.

OpenCode не имеет SubagentStop/PreToolUse hooks в этом workspace, поэтому
post-task цепочка выше обязательна и не заменяется injected context.

Preflight (опционально):

```bash
python3 scripts/pipeline_delegate.py <task_id> --assert-subagent <имя> --pipeline <id>
```

Код ≠ 0 → subagent не тот; **не** вызывай `task`.

## Режимы (`action`)

| action | Действие |
|--------|----------|
| `task` | Один `task` **только** на `task.subagent_type` из JSON |
| `ask_user` | `ask_user_question` (сейчас без `task`); после ответа — `task` из JSON, без delegate |
| `write_feature_cycle` | Цикл write-feature: JSON `cycle` (`task` / `assemble` / `done`) |
| `orchestrator_only` | Dispatch нет — шаги по markdown; delegate проверяет рёбра (`--from-step` / `--to-step`) |
| `ready` | Финальный ответ пользователю |
| `stopped` | Сообщить причину, стоп |
| `error` | Стоп, показать `instruction` — **не** improvising retry |

## Run until done

Выход только на `ready`, `ask_user`, `stopped` (или `orchestrator_only`, когда
следующий шаг оркестратор ведёт сам). Fail субагента → `append_run_log` →
**`pipeline_delegate.py --pipeline <id>`** → retry **только** если delegate снова
вернул `action: task`.

**Не завершай ход**, пока `must_continue: true`.

## Запреты

- ❌ `task` без предшествующего `pipeline_delegate.py` в том же ходе
  (кроме следующих блоков внутри уже открытого `write_feature_cycle`
  и apply после `ask_user` по `task` из того JSON)
- ❌ Subagent ≠ `task.subagent_type` из delegate JSON
- ❌ Ручной re-run resolver после fail, если delegate указал другой шаг
- ❌ Отдельный вызов `pipeline_set_active_task.py` (делает delegate)
- ❌ Завершать сессию при `must_continue: true`
- ❌ Параллельные содержательные `task`

## Spec pack

- `ask_user` — строки `needs-answer` в DECISIONS. После ответа: `task` из JSON
  ask_user (apply), **без** delegate. После apply — снова delegate.
- `write_feature_cycle` — читай JSON `cycle`: `task` → `spec-writer` с `block_id`; `assemble` → `write_feature_cycle.py --assemble` (не LLM); `done` → снова delegate. Между блоками **без** delegate.
- Не писать/править `SPEC` и отчёты — только через субагентов (`DECISIONS` — исключение)

## Calibration pack

Явно `--pipeline calibration`. `orchestrator_mode: orchestrator_only` — правил
dispatch нет; цепочка по markdown, рёбра графа через delegate.

## Карта шаг → субагент

Канон: `pipelines/<id>/registry.yaml` **активного** pipeline
(`--pipeline` / `.pipeline-active-task.json` → `registry_for(pipeline_id)`).
Не `STEP_TO_SUBAGENT`. Контракт: `scripts/PIPELINE-RUNTIME.md`.

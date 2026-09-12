---
description: Strict spec-orchestrator step order — pipeline_delegate is source of truth
alwaysApply: true
---
# Pipeline enforcement

Оркестратор (**spec-orchestrator**, основная сессия GigaCode/Qwen) **не выбирает**
следующий шаг по intuition. Единственный источник истины перед `task`:

```bash
python3 scripts/pipeline_delegate.py <slug> --cli qwen
```

`pipeline_dispatch.py` и `feature_status.py` — read-only для человека; оркестратор
вызывает **только** `pipeline_delegate.py` (он внутри делает dispatch + active-task).

## Обязательный цикл

Перед **каждым** `task` (кроме повторных `spec-writer` внутри `write_feature_cycle`):

1. `pipeline_delegate.py <slug> --cli qwen`
2. `action: task` → **сразу** `task` только на `task.subagent_type` из JSON
3. После SubagentStop hook (или fallback ingest) → снова шаг 1
4. **Не завершай ход**, пока `must_continue: true` (смотри `dispatch` внутри JSON)

**Hard gate:** PreToolUse hook `.qwen/hooks/pipeline-before-subagent.sh` **блокирует**
`task`, если `subagent_type` ≠ active-task из delegate. Обойти нельзя — только
снова `pipeline_delegate.py`.

Preflight (опционально):

```bash
python3 scripts/pipeline_delegate.py <slug> --assert-subagent gap-resolver
```

Код ≠ 0 → subagent не тот; **не** вызывай `task`.

## Режимы (`action`)

| action | Действие |
|--------|----------|
| `task` | Один `task` на `subagent_type` из JSON |
| `ask_user` | `ask_user_question` по DECISIONS, **без** `task` |
| `write_feature_cycle` | Цикл spec-writer (оркестратор) |
| `ready` | Финальный ответ пользователю |
| `stopped` | Сообщить причину (лимит alignment, права) |
| `error` | Стоп, показать `instruction` |

## Run until done

Правило **`run-until-done`**: выход только на `ready`, `ask_user`, `stopped`.
Fail субагента → `append_run_log` → **`pipeline_delegate.py`** → retry **только**
если delegate снова вернул `action: task` с тем же или новым subagent.

## Запреты

- ❌ `task` без предшествующего `pipeline_delegate.py` в том же ходе
- ❌ Subagent ≠ `task.subagent_type` из delegate JSON
- ❌ Ручной re-run resolver после fail, если delegate указал другой шаг
- ❌ Отдельный вызов `pipeline_set_active_task.py` (делает delegate)
- ❌ Завершать сессию при `must_continue: true`
- ❌ Параллельные содержательные `task`
- ❌ Писать/править `SPEC`, отчёты — только через субагентов

## write-feature

После assemble — **обязательно** `task spec-reviewer` (`check-feature`) через delegate.

## Карта шаг → субагент

Канон: `scripts/pipeline_common.py` (`STEP_TO_SUBAGENT`). Граф viewer:
`scripts/pipeline_schema.json`.

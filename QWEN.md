# Qwen Code — SIHIST analytics

Workspace пишется и гоняется в **Qwen Code CLI** (`qwen`). Общие правила
процесса — в `AGENTS.md`. Этот файл — только рантайм CLI.

## Роль основной сессии

Ты **spec-orchestrator**. Спецификацию, контекст-документ и отчёты сам не
пишешь и не правишь, кроме файла `DECISIONS` (`<slug>-decisions.md`): туда
записываешь ответы пользователя после `ask_user_question`.

Финальный артефакт: `Feature-writing/<slug>/<slug>.md`.

Пользователь **не** прожимает каждый `/check-feature` / `/resolve-gaps` вручную.
Один старт — дальше ты сам делегируешь субагентов и переходишь к next step.

Как стартовать (достаточно одного):

- свободный бриф в чате («сделай spec: …»);
- или `/find-context <бриф>`;
- или `/write-feature <бриф>`;
- или `/feature-status <slug>` — показать состояние **и сразу запустить**
  следующий шаг.

Слэш-команды — точки входа и ручной прыжок на шаг, не чеклист для человека.

## Где что лежит

| Путь | Назначение |
|------|------------|
| `.qwen/commands/` | Слэш-команды `/find-context`, `/write-feature`, … |
| `.qwen/agents/` | Субагенты шагов пайплайна |
| `.qwen/skills/` | Инструкции шага / kit-блока (`user-invocable: false`) |
| `.qwen/rules/` | Инварианты процесса |

Скиллы пайплайна с `/` не вызываются: их читает субагент. Пользователь
стартует брифом или одной командой; дальше оркестратор сам зовёт `task`.

## Пайплайн

```
/find-context → /write-feature → /check-feature → /resolve-gaps
  → /challenge-feature → /resolve-challenges
  → /check-feature-code ↔ /resolve-code-alignment (≤3)
```

Нет `<slug>-routing-state.json` → delegate всегда даст `analyze-routing` (P5),
потом `find-context` / domain-шаги. После mutating step — снова delegate;
устаревший JSON → снова `analyze-routing`. Check-feature без правок файлов
не зовёт анализатор: хук ставит stamp в JSON.

Перед **каждым** `task`: `python3 scripts/pipeline_delegate.py <slug> --cli qwen --pipeline spec-v2` →
`action: task` → **только** `task.subagent_type` из JSON. После subagent — снова delegate.
Исключение: `action: ask_user` — после ответа `task` из того JSON, без повторного
delegate; снова delegate после apply.
**Не завершай ход**, пока `must_continue: true`. Не спрашивай «запускать X?».
Не читай `pipelines/` и `scripts/pipeline_*`: повтор шага из delegate — не баг,
снова `task` на тот же `subagent_type`.
Не читай `pipelines/` и `scripts/pipeline_*`: повтор шага из delegate — не баг,
снова `task` на тот же `subagent_type`.

**Run until done:** иди по delegate в цикле, пока не `PASS` / `PASS WITH GAPS` или
`action: ask_user`. Fail — retry **только** через delegate, не improvising subagent.
Правила: `.qwen/rules/run-until-done.md`, `pipeline-enforcement.md`.

После каждого `task` — телеметрия в `agent-logs/<slug>/` (`append_run_log` +
`ingest_session_telemetry`). Слэш: `/archive-session`, `/analyze-telemetry`.

Пауза только если без человека нельзя: нет брифа, неоднозначный slug,
набор блоков write-feature, `ASK_PARENT` / `needs-answer` в `DECISIONS`
(оркестратор сам зовёт `ask_user_question`), лимит alignment, отказ по правам.

## Делегирование

Субагента запускай через `task`:

- `subagent_type` — имя из `.qwen/agents/`
- `run_in_background: false` — дождись результата в этом ходе

| Шаг | Субагент |
|-----|----------|
| find-context | `context-researcher` |
| write-feature | цикл `spec-writer` по одному блоку |
| check-feature | `spec-reviewer` |
| resolve-gaps | `gap-resolver` |
| challenge-feature | `spec-challenger` |
| resolve-challenges | `challenge-resolver` |
| check-feature-code | `code-auditor` |
| resolve-code-alignment | `alignment-resolver` |
| code-review | `doc-reviewer` |
| archive-session | оркестратор (ingest) |
| analyze-telemetry | `session-telemetry-analyst` |

## Что можно менять

Писать: `Feature-writing/`, `Feature-context/`, `agent-logs/`.

Не трогать: `analytics/`, `db-export/`, `repositories/`, `kb-writing-kits/`.

`analytics/`, `db-export/` и `repositories/` в git не входят — без них на
машине `/find-context` и `/check-feature-code` сверять факты нечем.

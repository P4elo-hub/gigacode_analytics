# GigaCode — SIHIST analytics

Workspace пишется и гоняется в **GigaCode CLI** (`gigacode`). Общие правила
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
| `.gigacode/commands/` | Слэш-команды `/find-context`, `/write-feature`, … |
| `.gigacode/agents/` | Субагенты шагов пайплайна |
| `.gigacode/skills/` | Инструкции шага / kit-блока (`user-invocable: false`) |
| `.gigacode/rules/` | Инварианты процесса |

Скиллы пайплайна с `/` не вызываются: их читает субагент. Пользователь
стартует брифом или одной командой; дальше оркестратор сам зовёт `task`.

## Пайплайн

```
/analyze-routing (если нет routing-state.json или JSON stale)
  → /find-context → /write-feature → /check-feature → /resolve-gaps
  → /challenge-feature → /resolve-challenges
  → /check-feature-code ↔ /resolve-code-alignment (≤3)
```

Перед **каждым** `task`: `python3 scripts/pipeline_delegate.py <slug> --cli gigacode` →
`action: task` → **только** `task.subagent_type` из JSON. После subagent — снова delegate.
**Не завершай ход**, пока `must_continue: true`. Не спрашивай «запускать X?».
Не читай `pipelines/` и `scripts/pipeline_*`: повтор шага из delegate — не баг,
снова `task` на тот же `subagent_type`.

**Run until done:** иди по delegate в цикле, пока не `PASS` / `PASS WITH GAPS` или
`action: ask_user`. Fail — retry **только** через delegate, не improvising subagent.
Правила: `.gigacode/rules/run-until-done.md`, `pipeline-enforcement.md`.

После каждого `task` — телеметрия в `agent-logs/<slug>/` (`append_run_log` +
`ingest_session_telemetry`). Слэш: `/archive-session`, `/analyze-telemetry`.

После **PASS** предложи `/snapshot-baseline <slug>`. После human review —
отдельный контур `/calibrate <slug>` (`CALIBRATION.md`, **calibration-orchestrator**).

Пауза только если без человека нельзя: нет брифа, неоднозначный slug,
набор блоков write-feature, `ASK_PARENT` / `needs-answer` в `DECISIONS`
(оркестратор сам зовёт `ask_user_question`), лимит alignment, отказ по правам.

## Делегирование

Субагента запускай через `task`:

- `subagent_type` — имя из `.gigacode/agents/`
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

Писать: `Feature-writing/`, `Feature-context/`, `agent-logs/`, `Calibration/`
(калибровка), `.gigacode/skills/` (только через `/apply-calibration`).

Не трогать: `analytics/`, `db-export/`, `repositories/`, `kb-writing-kits/`.

`analytics/`, `db-export/` и `repositories/` в git не входят — без них на
машине `/find-context` и `/check-feature-code` сверять факты нечем.

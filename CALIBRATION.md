# Calibration mode (GigaCode / Qwen / OpenCode)

**Отдельный контур** от `spec-orchestrator`. Явный старт: `/calibrate <slug>`.

Полный гид для человека: [HOW-WORK-CALIBRATION.md](HOW-WORK-CALIBRATION.md).

## Роль calibration-orchestrator

Не пишет spec в обычном `Feature-writing/` (кроме sync gold через скрипт).
Патчи скиллов — только `/apply-calibration` после approve.

## Workflow

```
PASS → /snapshot-baseline <slug>
     → [вы правите SPEC в Feature-writing/]
     → /capture-review <slug>
     → /analyze-delta <slug>        ← + context-gaps.md (CTX-GAP-*)
     → /analyze-telemetry <slug>
     → /propose-calibration <slug>
     → [approve PROP-* в proposals.md]
     → /apply-calibration <slug>
     → новая сессия spec-orchestrator → /benchmark-rerun <slug>
     → python3 scripts/score_calibration_run.py <slug>
```

## Команды

| Команда | Субагент |
|---------|----------|
| `/snapshot-baseline` | скрипт |
| `/capture-review` | review-capturer |
| `/analyze-delta` | regression-analyst |
| `/analyze-telemetry` | session-telemetry-analyst |
| `/propose-calibration` | calibration-proposer |
| `/apply-calibration` | calibration-applier |
| `/benchmark-rerun` | benchmark-runner |
| `/calibrate` | calibration-orchestrator (цепочка) |

CLI ingest: `--cli gigacode` | `qwen` | `opencode`.

## Context gaps vs skill proposals

| Тип | ID | Смысл |
|-----|-----|--------|
| Не хватило источника | `CTX-GAP-*` | «Не тупой агент — неполный контекст»: дописать analytics, repo, context-doc |
| Ошибка процесса/скилла | `PROP-*` | Патч `.gigacode/skills/` после approve |

`human-review.md`: поле `cause: context-gap | skill-gap | hybrid`.
Скрипт: `python3 scripts/analyze_context_gaps.py <slug>`.

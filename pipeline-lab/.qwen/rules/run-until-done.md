---
description: Lab live run stops on cursor_exhausted / ready / ask_user — not on fail
alwaysApply: true
---
# Run until done (pipeline-lab)

`/lab-run` не ждёт «продолжить?» между шагами.

## Выход

| Условие | Действие |
|---------|----------|
| `gate: stop` / `cursor_exhausted` | `run.py --compare`, финальный ответ |
| `action: ready` / `stopped` / `error` | стоп, показать JSON |
| `action: ask_user` | `ask_user_question` по DECISIONS |

**Не выход:** fail/retry субагента, пока `--tick` снова даёт `gate: task`.

Не иди до боевого PASS, если курсор сценария кончился — иначе retry
уходит в бесконечный `task`.

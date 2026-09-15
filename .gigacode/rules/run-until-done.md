---
description: Orchestrator runs until PASS / PASS WITH GAPS — no idle stops on fail
alwaysApply: true
---
# Run until done

Оркестратор (**spec-orchestrator**, основная сессия Qwen/GigaCode) **не завершает ход**
и **не ждёт «продолжи»**, пока `pipeline_delegate.py` не вернёт `ready` / `ask_user` /
`stopped`.

## Единственные точки выхода

| Условие | Действие |
|---------|----------|
| `action: ready` | Финальный ответ: `PASS` или `PASS WITH GAPS` |
| `action: ask_user` | `ask_user_question` по `needs-answer` в DECISIONS — **ждать ответ** |
| `action: stopped` | Только: нет брифа, неоднозначный slug, лимит alignment (3× FAIL), отказ по правам |
| План write-feature (набор блоков) | Один `ask_user_question` по таблице блоков — затем цикл writer |

**Не выход:** fail/retry субагента, truncated output, «сессия idle» — продолжай через
delegate.

## После каждого `task` (обязательный цикл)

1. SubagentStop hook: run-log + ingest + validate (или fallback вручную).
2. **`pipeline_delegate.py <slug> --cli qwen`**
3. `action: task` → следующий `task` **в том же ходе** на **только** `subagent_type` из JSON.
4. Без «упало», «остановлюсь», «продолжить?».

## Fail субагента — retry только через delegate

- залогируй `--result fail` (если hook не успел);
- **`pipeline_delegate.py`** — не выбирай subagent сам;
- retry **только** если delegate вернул `action: task`;
- ❌ не re-run `challenge-resolver`, если delegate ждёт `spec-reviewer`.

`pending-apply` — delegate вернёт resolver apply (`action: task`), без ask_user.

После ответов по `needs-answer` — запиши Decision → delegate → apply.

## Запреты

- ❌ `task` без `pipeline_delegate.py` в том же ходе
- ❌ Subagent не из delegate JSON
- ❌ Завершать ход при `must_continue: true`
- ❌ Спрашивать «продолжить?» / «запустить check-feature?»
- ❌ Improvised re-run после удаления артефактов
- ❌ Читать `pipelines/` / `scripts/pipeline_*`, если «кажется цикл»

Канон шага: **`pipeline_delegate.py`**. Порядок: `pipeline-enforcement`.

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
| `action: ask_user` | `ask_user_question` по `needs-answer` в DECISIONS — **ждать ответ**; после ответа `task` из JSON, **без** delegate |
| `action: stopped` | Только: нет брифа, неоднозначный slug, лимит alignment (3× FAIL), отказ по правам |
| План write-feature (набор блоков) | Один `ask_user_question` по таблице блоков — затем цикл writer |

**Не выход:** fail/retry субагента, truncated output, «сессия idle» — продолжай через
delegate.

## После каждого `task` (обязательный цикл)

Исключение: `action: write_feature_cycle` — между блоками читай JSON `cycle`
(`write_feature_cycle.py`). `task` → spec-writer; `assemble` → скрипт, не writer.
**Не** вызывай `pipeline_delegate.py` пока цикл открыт. Снова delegate после `done`.

Исключение: `action: ask_user` — после ответа человека запиши Decision → сразу
`task` на `task.subagent_type` из **того же** JSON ask_user (apply). **Не** вызывай
`pipeline_delegate.py` между ответом и apply. Снова delegate после возврата apply.

1. SubagentStop hook: run-log + ingest + validate (или fallback вручную).
2. **`pipeline_delegate.py <slug> --cli qwen`** (не между блоками write-feature)
3. `action: task` → следующий `task` **в том же ходе** на **только** `subagent_type` из JSON.
4. Без «упало», «остановлюсь», «продолжить?».

## Fail субагента — retry только через delegate

Хук пишет fail только если заход **оборвался** (timeout, cancel, ошибка CLI),
не если в отчёте агента есть слово fail. Качество шага смотрит analyze-routing + delegate.

- залогируй `--result fail` (если hook не успел и это обрыв);
- **`pipeline_delegate.py`** — не выбирай subagent сам;
- retry **только** если delegate вернул `action: task`;
- ❌ не re-run `challenge-resolver`, если delegate ждёт `spec-reviewer`.

`pending-apply` — после ответа `task` apply из JSON `ask_user`, без повторного delegate.
Снимок/роутер — только после возврата apply.

## Запреты

- ❌ `task` без `pipeline_delegate.py` в том же ходе (кроме блоков внутри
  уже открытого `write_feature_cycle` и apply после `ask_user` по `task` из того JSON)
- ❌ Subagent не из delegate JSON
- ❌ Завершать ход при `must_continue: true`
- ❌ Спрашивать «продолжить?» / «запустить check-feature?»
- ❌ Improvised re-run после удаления артефактов
- ❌ Читать `pipelines/` / `scripts/pipeline_*`, если «кажется цикл»

Канон шага: **`pipeline_delegate.py`**. Порядок: `pipeline-enforcement`.

---
description: Дашборд фичи — что открыто, какой вердикт, один следующий шаг
---

Ты **spec-orchestrator** этой сессии Qwen Code. Спецификацию и отчёты сам не пиши и не правь — только дашборд, план блоков и делегирование субагентам из `.qwen/agents/`.
Субагентов запускай через `task` с `run_in_background: false`.
Скилл шага: прочитай `.qwen/skills/feature-status/SKILL.md` или вызови `skill` `feature-status`.

Покажи состояние фичи через скилл `feature-status`. Счётчики и next step
бери из `python3 scripts/feature_status.py <slug>` (не считай вручную).
Скилл read-only: сам файлы не правь.

Затем **`pipeline_delegate.py <slug> --cli gigacode --pipeline spec-v2`** и **сразу** `task` только на
`task.subagent_type` из JSON (`run_in_background: false`). Не считай next step
вручную и не спрашивай «запускать?». После каждого `task` — снова delegate,
пока нет паузы по существу или verdict PASS / PASS WITH GAPS.

Фича (slug или путь к артефакту): {{args}}

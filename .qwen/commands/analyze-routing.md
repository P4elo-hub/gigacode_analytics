---
description: Записать routing-state.json для детерминированного роутера (POC)
---

Делегируй субагенту `routing-analyzer` через инструмент `task`:
- `subagent_type`: `routing-analyzer`
- `run_in_background`: false
- в prompt передай это задание и аргументы пользователя целиком

Сам работу шага не выполняй. Скилл субагента: `.qwen/skills/analyze-routing/SKILL.md`.

Собери факты фичи в `Feature-writing/<slug>/<slug>-routing-state.json` по
скиллу `analyze-routing`. Next step не выбирай.

Фича (slug): {{args}}

## После шага — продолжай пайплайн

Когда субагент вернул результат, не жди новой слэш-команды. Сразу:
`python3 scripts/pipeline_delegate.py <slug> --cli qwen --pipeline routing-poc` →
`task` на `task.subagent_type` из JSON (`run_in_background: false`).
Не спрашивай «запускать X?».

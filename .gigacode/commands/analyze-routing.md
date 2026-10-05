---
description: Записать routing-state.json для детерминированного роутера (pack-local)
---

Делегируй субагенту `routing-analyzer` через инструмент `task`:
- `subagent_type`: `routing-analyzer`
- `run_in_background`: false
- в prompt передай это задание и аргументы пользователя целиком,
  включая `pipeline_id` (из args / `--pipeline` / `.pipeline-active-task.json`;
  если не указан — `spec`)

Сам работу шага не выполняй. Скилл субагента: `.gigacode/skills/analyze-routing/SKILL.md`.

Собери факты фичи в `Feature-writing/<slug>/<slug>-routing-state.json` по
скиллу `analyze-routing` и `pipelines/<pipeline_id>/routing_conditions.yaml`
→ `status_fields`. Next step не выбирай.

Аргументы (slug и опционально pipeline): {{args}}

## После шага — продолжай пайплайн

Когда субагент вернул результат, не жди новой слэш-команды. Сразу:
`python3 scripts/pipeline_delegate.py <slug> --cli gigacode --pipeline <pipeline_id>` →
`task` на `task.subagent_type` из JSON (`run_in_background: false`).
Не спрашивай «запускать X?».

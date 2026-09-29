---
name: music-revision-plan
description: >-
  Rules for choosing one internal operation. The adapter executes it later.
user-invocable: false
---

# music-revision-plan

Вход: `defect.json` и capability, уже отмеченные CapabilityRegistry. Artifact внутри envelope имеет тип `revision-plan`.

Поля artifact определяет `revision-plan.schema.json`: plan id, defect id, source version, operation, objective, preserve, capability, status и blocked reason.

`operation` — одно значение из enum `music_production/contracts/generation-request.schema.json`, и только если CapabilityRegistry включил его. Enum не означает доступность в Suno API.

PASS — один дефект и одна включённая operation. REVISE — цель правки не собрана. BLOCKED — capability выключена или бюджет попыток исчерпан. Тогда эскалация человеку, без обхода BudgetGuard.

План не исполняй и провайдера не вызывай.

## Машинный результат

Верни только JSON по `music_production/contracts/agent-result.schema.json`, без Markdown. `artifact_type` = `revision-plan`; `artifact` проверяется по `music_production/contracts/revision-plan.schema.json`. Не записывай результат, пока обе схемы не пройдены.

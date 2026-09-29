---
name: music-version-comparison
description: >-
  Rules for comparing parent and child against one revision goal.
user-invocable: false
---

# music-version-comparison

Вход, все обязательны: edit-attempt artifact, revision-plan, parent version, child version, target defect и измеренные или переданные факты сравнения. Artifact внутри envelope имеет тип `version-comparison`.

Поля artifact определяет `music_production/contracts/version-comparison.schema.json`. Обязателен `edit_attempt_id`. Также обязательны comparison id, parent_version_id, child_version_id, target defect, outcome, признаки сохранения, regressions и remaining_defects.

Перед записью проверь lineage:

- `edit_attempt_id` существует во входе;
- comparison относится к этому edit attempt;
- `parent_version_id` и `child_version_id` совпадают с edit-attempt;
- `revision_plan_id` и `defect_id` согласованы с revision-plan и target defect;
- если данных нет или IDs не совпадают, outcome artifact = `BLOCKED`.

Не исправляй lineage самостоятельно и не подменяй parent/child IDs или `edit_attempt_id`.

Outcome artifact: `ACCEPTED`, `PARTIAL`, `REJECTED`, `BLOCKED`; outcome envelope отдельно равен `PASS`, `REVISE` или `BLOCKED`. Рекомендация не меняет `current_version_id` и не перезаписывает expert decision.

Не утверждай непереданное свойство звука. Не вызывай провайдера.

## Машинный результат

Верни только JSON по `music_production/contracts/agent-result.schema.json`, без Markdown. `artifact_type` = `version-comparison`; `artifact` проверяется по `music_production/contracts/version-comparison.schema.json` и обязан содержать `edit_attempt_id`. Не записывай результат, пока обе схемы не пройдены.

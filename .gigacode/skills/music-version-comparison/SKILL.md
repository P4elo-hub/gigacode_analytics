---
name: music-version-comparison
description: >-
  Rules for comparing parent and child against one revision goal.
user-invocable: false
---

# music-version-comparison

Вход: план правки, parent, child, целевой дефект. Artifact внутри envelope имеет тип `version-comparison`.

Поля artifact определяет `version-comparison.schema.json`: comparison id, версии, target defect, outcome, признаки сохранения и regressions.

Outcome artifact: `ACCEPTED`, `PARTIAL`, `REJECTED`, `BLOCKED`; outcome envelope отдельно равен `PASS`, `REVISE` или `BLOCKED`. Рекомендация не меняет `current_version_id` и не перезаписывает expert decision.

Не утверждай непереданное свойство звука. Не вызывай провайдера.

## Машинный результат

Верни только JSON по `music_production/contracts/agent-result.schema.json`, без Markdown. `artifact_type` = `version-comparison`; `artifact` проверяется по `music_production/contracts/version-comparison.schema.json`. Не записывай результат, пока обе схемы не пройдены.

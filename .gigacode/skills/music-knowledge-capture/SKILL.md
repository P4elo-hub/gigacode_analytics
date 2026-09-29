---
name: music-knowledge-capture
description: >-
  Rules for one candidate knowledge case. Production skills stay unchanged.
user-invocable: false
---

# music-knowledge-capture

Artifact внутри envelope имеет тип `knowledge-case`. Новое правило — только `rule_status: candidate_rule`. Активные production skills, agent-файлы и expert decision не меняй.

Обязательные поля, копируемые из входов, без догадки:

- `decision_id`
- `gate`
- `version_before_id` — версия до решения
- `defect_id` — найденный дефект
- `proposed_action` — предложенное действие
- `prompt_id` — использованный prompt
- `result_version_id` — полученный результат
- `verdict`
- `decided_by`
- `comment`
- `captured_at`

Плюс `schema_version`, `track_id`, `rule_status`.

PASS — все поля взяты из входа. BLOCKED — нет решения человека. REVISE не используется.

Не вызывай провайдера и не подписывай verdict своим именем.

## Машинный результат

Верни только JSON по `music_production/contracts/agent-result.schema.json`, без Markdown. `artifact_type` = `knowledge-case`; `artifact` проверяется по `music_production/contracts/knowledge-case.schema.json`. `rule_status` всегда `candidate_rule`. Не записывай результат, пока обе схемы не пройдены.

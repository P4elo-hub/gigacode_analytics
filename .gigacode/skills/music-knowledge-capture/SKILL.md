---
name: music-knowledge-capture
description: >-
  Rules for one candidate knowledge case. Production skills stay unchanged.
user-invocable: false
---

# music-knowledge-capture

Artifact внутри envelope имеет тип `knowledge-case`. Новое правило — только `rule_status: candidate_rule`. Один кейс не меняет active agents или skills. Повышение `candidate_rule` в `active_rule` в этот этап не входит.

Вход: expert decision, текущее состояние трека и только committed artifacts. Для gate используй связанные song package, candidate, version, defect, revision-plan, comparison и QC. Prompt history включай, только если она уже committed.

Копируй факты и id из evidence. Не придумывай отсутствующие значения. Не подставляй имя Алекса. Не оценивай музыку заново. Не меняй `verdict`.

Обязательные поля, копируемые из входов, без догадки:

- `decision_id`
- `gate`
- `subject_type` и `subject_id` — предмет этого gate
- `version_before_id` — версия до решения, либо `null`, если её нет
- `defect_id` — найденный дефект, либо `null`, если дефект не committed
- `proposed_action` — предложенное действие, либо `null`
- `prompt_id` — использованный prompt, либо `null`, если prompt history нет
- `result_version_id` — полученный результат, либо `null`, если версии результата нет
- `verdict`
- `decided_by`
- `comment` — дословно, включая пустую строку и перевод строки
- `captured_at`
- `evidence_refs`
- `technical_facts`

Если соответствующий committed artifact есть, `defect_id`, `prompt_id` и `result_version_id` не оставляй `null`.

`subject_type`: `SONG_PACKAGE`, `CANDIDATE`, `VERSION` или `REVISION`.

Плюс `schema_version`, `track_id`, `rule_status`.

PASS — все поля взяты из входа. BLOCKED — нет решения человека или нет обязательного subject. REVISE не используется.

Не вызывай провайдера и не подписывай verdict своим именем.

## Машинный результат

Верни только JSON по `music_production/contracts/agent-result.schema.json`, без Markdown. `artifact_type` = `knowledge-case`; `artifact` проверяется по `music_production/contracts/knowledge-case.schema.json`. `rule_status` всегда `candidate_rule`. Не записывай результат, пока обе схемы не пройдены.

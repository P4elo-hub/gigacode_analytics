---
name: music-candidate-review
description: >-
  Rules for reviewing a generation batch from supplied facts only.
user-invocable: false
---

# music-candidate-review

Вход: `generation-request.json` и список кандидатов от Adapter. Artifact внутри envelope имеет тип `candidate-review`.

Поля artifact определяет `candidate-review.schema.json`: `review_id`, `generation_request_id`, кандидаты и `shortlist_candidate_ids`.

Если аудио не было во входе, assessment не может утверждать факт прослушивания. Outcome envelope: `PASS`, `REVISE`, `BLOCKED`.

PASS не выбирает базу. Выбор — human gate `select-base`. Не ставь `SELECT_AS_BASE`.

Не вызывай провайдера и не объявляй запись качественной без переданного факта.

## Машинный результат

Верни только JSON по `music_production/contracts/agent-result.schema.json`, без Markdown. `artifact_type` = `candidate-review`; `artifact` проверяется по `music_production/contracts/candidate-review.schema.json`. Не добавляй `selected_candidate_id` или human verdict. Не записывай результат, пока обе схемы не пройдены.

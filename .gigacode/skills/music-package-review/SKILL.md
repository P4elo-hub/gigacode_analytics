---
name: music-package-review
description: >-
  Rules for reviewing the song package without signing the human decision.
user-invocable: false
---

# music-package-review

Вход: `brief.json`, `lyrics.json`, `sound-direction.json`. Artifact внутри envelope имеет тип `package-review`.

Поля artifact определяет `package-review.schema.json`: `review_id`, `verdict`, `revision_target`, структурированные `issues`, `song_package`.

`verdict`: `PASS`, `REVISE`, `BLOCKED`. При REVISE `revision_target` — `LYRICS` или `PRODUCTION`. При PASS `song_package` обязателен, а `revision_target` — null.

Если в брифе `package_review_required` истинно, PASS не заменяет human gate `package-approval`. Expert decision не пиши.

Не вызывай провайдера и не собирай generation request.

## Машинный результат

Верни только JSON по `music_production/contracts/agent-result.schema.json`, без Markdown. `artifact_type` = `package-review`; `artifact` проверяется по `music_production/contracts/package-review.schema.json`. Используй `verdict`, структурированные `issues` и условные поля схемы. Не записывай результат, пока обе схемы не пройдены.

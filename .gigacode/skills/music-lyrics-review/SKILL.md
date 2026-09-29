---
name: music-lyrics-review
description: >-
  Rules for reviewing lyric text, singability, and structure.
user-invocable: false
---

# music-lyrics-review

Вход: `brief.json`, `lyrics.json`. Artifact внутри envelope имеет тип `lyrics-review`. `lyrics.json` не меняй.

Поля artifact определяет `lyrics-review.schema.json`: `review_id`, `lyrics_version_id`, `verdict`, структурированные `issues`.

`verdict`: `PASS`, `REVISE` или `BLOCKED`. Проверяй только текст, удобство пения фразы и структуру против брифа. REVISE обязан содержать `issues`. Граф возвращает REVISE на `lyrics-write`.

PASS — замечаний нет. BLOCKED — нет текста или вывод требует аудио, которого нет.

Не утверждай, что слышал аудио. Не вызывай провайдера.

## Машинный результат

Верни только JSON по `music_production/contracts/agent-result.schema.json`, без Markdown. `artifact_type` = `lyrics-review`; `artifact` проверяется по `music_production/contracts/lyrics-review.schema.json`. Используй `verdict` и структурированные `issues` из схемы. Не записывай результат, пока обе схемы не пройдены.

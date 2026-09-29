---
name: music-lyrics
description: >-
  Rules for one lyrics.json written only from brief.json.
user-invocable: false
---

# music-lyrics

Вход: `brief.json`. Artifact внутри envelope имеет тип `lyrics`. Чужой бриф не меняй.

Artifact следует `lyrics.schema.json`: `lyrics_version_id`, `language` и `sections` с `section_id`, `section_type`, `text`.

`sections` повторяет форму из `assignment`. `text` поётся фразами этой формы. Факта нет в брифе — не добавляй имя, место и обещание прослушиваний.

PASS — текст собран из брифа. REVISE этот агент сам не ставит. BLOCKED — брифа нет.

Не утверждай, что запись прослушана. Не вызывай провайдера.

## Машинный результат

Верни только JSON по `music_production/contracts/agent-result.schema.json`, без Markdown. `artifact_type` = `lyrics`; `artifact` проверяется по `music_production/contracts/lyrics.schema.json`. Поля этого schema-файла имеют приоритет над кратким описанием выше. Не записывай результат, пока обе схемы не пройдены.

---
name: music-sound-direction
description: >-
  Rules for a sound description taken only from the ready brief.
user-invocable: false
---

# music-sound-direction

Вход: `brief.json`. Artifact внутри envelope имеет тип `sound-direction`.

Поля artifact определяет `sound-direction.schema.json`: version id, структура, вокал, аранжировка, динамика, пространство и негативные ограничения.

`description` следует только заданию. Не добавляй поля Suno API.

PASS — описание честно выведено из брифа. REVISE — брифу не хватает ограничения, без которого описание было бы догадкой. BLOCKED — брифа нет или нужен непереданный аудиофайл.

Не утверждай, что слышал аудио. Не вызывай провайдера.

## Машинный результат

Верни только JSON по `music_production/contracts/agent-result.schema.json`, без Markdown. `artifact_type` = `sound-direction`; `artifact` проверяется по `music_production/contracts/sound-direction.schema.json`. Поля схемы обязательны; свободное `description` их не заменяет. Не записывай результат, пока обе схемы не пройдены.

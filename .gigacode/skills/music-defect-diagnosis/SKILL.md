---
name: music-defect-diagnosis
description: >-
  Rules for one defect.json taken from supplied version facts.
user-invocable: false
---

# music-defect-diagnosis

Artifact внутри envelope имеет тип `defect` и следует `music_production/contracts/defect.schema.json`.

Пиши `id`, `version_id`, `start_seconds`, `end_seconds`, `category`, `importance`, `diagnosis`, `preserve`, `desired_change`, `status` только из переданных фактов. Секунды — позиция в аудио, не время суток.

PASS — документ валиден и не шире фактов. REVISE — фрагмент не следует из фактов. BLOCKED — нет версии или факта о фрагменте.

Не выбирай operation и не вызывай провайдера. Не утверждай, что слышал аудио, если его не передали.

## Машинный результат

Верни только JSON по `music_production/contracts/agent-result.schema.json`, без Markdown. `artifact_type` = `defect`; `artifact` проверяется по `music_production/contracts/defect.schema.json`. Не записывай результат, пока обе схемы не пройдены.

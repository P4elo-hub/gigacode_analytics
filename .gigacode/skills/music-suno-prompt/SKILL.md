---
name: music-suno-prompt
description: >-
  Rules for compiling one abstract generation-request. No provider call.
user-invocable: false
---

# music-suno-prompt

Вход: `song-package.json` и `brief.json`. Artifact внутри envelope имеет тип `generation-request` и следует `music_production/contracts/generation-request.schema.json`.

Разрешены только поля схемы. `operation` — внутренняя операция движка. Запись в enum не подтверждает доступность в Suno API; это позже проверяет CapabilityRegistry. Исполнение делает Adapter, не этот скилл.

Если `package_review_required` истинно, не пиши запрос, пока нет отдельного expert decision: gate `PACKAGE_APPROVAL`, verdict `APPROVE_PACKAGE`. Это решение человека, его не подписывай.

PASS — запрос валиден. REVISE — в пакете нет version id для ссылки. BLOCKED — нет одобрения человека там, где бриф его требует.

Не добавляй endpoint, cookie, model и не вызывай провайдера.

## Машинный результат

Верни только JSON по `music_production/contracts/agent-result.schema.json`, без Markdown. `artifact_type` = `generation-request`; `artifact` проверяется по `music_production/contracts/generation-request.schema.json`. Не записывай результат, пока обе схемы не пройдены.

---
name: music-brief
description: >-
  Rules for writing one schema-valid brief.json from a ready song assignment.
user-invocable: false
---

# music-brief

Artifact внутри envelope имеет тип `brief` и следует `music_production/contracts/brief.schema.json`.

Обязательные поля схемы: `schema_version` = `1.0`, `track_id`, `created_at` с суффиксом `Z`, `assignment`, `package_review_required`, `reference_use_permitted`, `budget`.

`package_review_required` по умолчанию истинно, если задание его не выключило. `reference_use_permitted` истинно только при явном разрешении. Числа бюджета бери из задания; если их нет, не выдумывай коммерческий лимит — остановись.

PASS — документ валиден и не шире задания. REVISE — форма пения или смысл противоречивы. BLOCKED — задания нет или запрошен запрещённый референс.

Не пиши текст песни и не вызывай провайдера.

## Машинный результат

Верни только JSON по `music_production/contracts/agent-result.schema.json`, без Markdown. `artifact_type` = `brief`; `artifact` проверяется по `music_production/contracts/brief.schema.json`. Не записывай результат, пока обе схемы не пройдены.

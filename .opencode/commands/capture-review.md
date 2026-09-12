---
description: Sync gold spec + human review themes после ваших правок
agent: review-capturer
---

Делегируй `review-capturer` через `task` (`run_in_background: false`).

Slug: {{args}}

Сначала `python3 scripts/sync_gold_spec.py {{args}}`.
Скилл: `.opencode/skills/capture-review/SKILL.md`.

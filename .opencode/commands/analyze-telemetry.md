---
description: Разбор agent-logs — anomalies, повторы skill, retry loops
---

Делегируй `session-telemetry-analyst` через `task` (`run_in_background: false`).

Slug: {{args}}

Субагент пишет только `telemetry-analysis.md` в текущем run.
Если metrics нет — сначала `/archive-session {{args}}`.

Скилл: `.opencode/skills/analyze-telemetry/SKILL.md`.

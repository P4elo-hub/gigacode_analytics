---
description: Полный цикл калибровки после PASS и human review
agent: calibration-orchestrator
---

Ты **calibration-orchestrator** (не spec-orchestrator). Прочитай `CALIBRATION.md`
и скилл `.opencode/skills/calibrate/SKILL.md`.

Slug: {{args}}

Запусти цепочку: snapshot (если нет) → capture-review (если user ready) →
analyze-delta → analyze-telemetry → propose-calibration → pause approve →
apply → benchmark handoff.

Делегируй субагентов через `task`, `run_in_background: false`.

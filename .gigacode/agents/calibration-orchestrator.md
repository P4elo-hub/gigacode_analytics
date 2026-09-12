---
name: calibration-orchestrator
description: >-
  Meta-pipeline after PASS: snapshot, capture review, delta, telemetry, proposals,
  benchmark. Does not write SPEC except via approved calibration apply.
model: inherit
approvalMode: default
tools:
  - read_file
  - grep_search
  - glob
  - list_directory
  - run_shell_command
  - skill
  - task
  - ask_user_question
  - write_file
  - edit
---

> GigaCode: скилл `calibrate` или `.gigacode/skills/calibrate/SKILL.md`.

# Роль

Оркестратор **калибровки процесса**, не spec-пайплайна. Не смешивай с
`spec-orchestrator`.

# Цепочка `/calibrate <slug>`

1. Нет baseline → `python3 scripts/snapshot_baseline.py <slug> --new-run`
2. Спроси: «Review spec готов?» → `/capture-review`
3. `task regression-analyst` → delta + `context-gaps.md`
4. `task session-telemetry-analyst` → telemetry
5. `task calibration-proposer` → proposals (только skill-gap)
6. Покажи **CTX-GAP-*** (что дописать в analytics/repo) и **PROP-***; approve PROP-* → `/apply-calibration`
7. Предложи **новую сессию** → `/benchmark-rerun`

Пиши только: `Calibration/`, `proposals.md`, `human-review.md` (через субагентов).

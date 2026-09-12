---
name: calibrate
description: Full calibration orchestration after PASS and human review.
user-invocable: false
---

# calibrate

Meta-pipeline. См. `CALIBRATION.md`, `HOW-WORK-CALIBRATION.md`.

## Preconditions

- `SPEC` существует; желательно verdict PASS / PASS WITH GAPS.

## Order

1. snapshot-baseline (если нет baseline)
2. capture-review (после confirm user)
3. analyze-delta
4. analyze-telemetry
5. propose-calibration
6. pause for approve → apply-calibration
7. benchmark-rerun (new session handoff)

Делегируй через `task` с `run_in_background: false`.

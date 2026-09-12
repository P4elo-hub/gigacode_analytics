# Dispatch golden — coverage matrix

Maps `choose_next_step()` / `needs_check_feature()` branches to fixture ids.

## `choose_next_step` (priority order)

| Branch | Fixture | Assert |
|--------|---------|--------|
| Alignment limit exhausted | `15-alignment-limit-stopped` | `stopped`, empty next |
| No context | `01-no-context` | `find-context` |
| No spec | `02-no-spec` | `write-feature`, `write_feature_cycle` |
| Graph gate: first check | `03-spec-needs-check` | `check-feature` |
| Graph gate: SPEC newer GAPS_MAP | `04-spec-newer-gaps-map` | `check-feature`, reason GAPS_MAP |
| Graph gate: SPEC newer CHALLENGES_MAP | `18-spec-newer-challenges-map` | `check-feature`, reason CHALLENGES_MAP |
| Graph gate: run-log check ok | `16-graph-gate-run-log`, `10-no-challenges-file` | bypass → gaps / challenge |
| needs-answer + open gaps | `06-needs-answer-gaps` | `resolve-gaps`, `ask_user` |
| needs-answer + no gaps (CH) | `08-needs-answer-challenges` | `resolve-challenges`, `ask_user` |
| pending-apply + open gaps | `07-pending-apply-gaps` | `resolve-gaps`, delegate |
| pending-apply + no gaps (CH) | `17-pending-apply-challenges` | `resolve-challenges`, delegate |
| Critical/Major MISMATCH | `14-alignment-fail-mismatch` | `resolve-code-alignment` |
| Open gaps (plain) | `05-open-gaps` | `resolve-gaps` |
| Open CH | `09-open-challenges` | `resolve-challenges` |
| No CHALLENGES file | `10-no-challenges-file` | `challenge-feature` |
| No ALIGNMENT | `11-no-alignment` | `check-feature-code` |
| Stale alignment | `12-stale-alignment` | `check-feature-code`, reason устарела |
| Verdict PASS | `13-alignment-pass` | `ready` |
| Verdict PASS WITH GAPS | `19-alignment-pass-with-gaps` | `ready` |
| FAIL, no Critical/Major mismatch | `20-alignment-fail-no-critical-mismatch` | `check-feature-code`, re-audit |

## Out of scope (phase 0)

These stay in `pipeline_smoke_test.py` or hooks — not dispatch routing:

| Concern | Smoke check |
|---------|-------------|
| Graph edges / illegal transition | `pipeline-delegate`, `pipeline-before-subagent` |
| Graph order gate on live slug | `graph-order-gate:bph-moex-tax` |
| Run-log vs active-task (viewer) | `log-first`, `ts-sort` |
| Timings / agent-logs archive | `step-timings` |
| CLI hooks / settings | `cli-settings` |
| Calibration pipeline graph | `graph:*:calibration` |
| Exit policy (must_continue vs ask_user) | `run-until-done:*` |

Phase 1+ (registry compile) must keep **dispatch-golden** green; phase 2 router adds no duplicate
live-slug checks unless a branch is removed from golden first.

# Dispatch golden — coverage matrix

Maps `choose_next_step()` / `needs_check_feature()` branches to fixture ids.

Branches are declared in `pipelines/spec/dispatch.yaml` and evaluated by
`pipeline_router.py` via `build_dispatch(..., pipeline_id="spec")`.
Golden fixtures are the spec routing contract. Calibration has no dispatch rules
(`orchestrator_only`).

Phase 12: live dispatch overlays `routing_state` (option B — key on each case,
injected after `touch_after` / run-log, JSON mtime newest so P5
`routing_state_needs_refresh` is false). `expect` values are unchanged.
Domain parse for the etalon is `scripts/routing_state_baseline.py`
(`routing_state_replay_from_collectors.py --golden`).

`needs_check_feature` is stored in JSON (analyzer / baseline), including
run-log cases `03`, `04`, `16`, `18`. Engine does not recompute it on the hot
path. `stale` / `alignment_stale` are engine mtime after overlay.

P5 `routing_state_needs_refresh` → `analyze-routing` is covered by routing-poc
golden (`02-missing-json`, `03-stale-json`), not by renaming the 24 spec ids.

## Invariant (after P10–P30, before P40+)

| Invariant | Fixtures | Effect |
|-----------|----------|--------|
| `needs-check-feature` | `03-spec-needs-check`, `04-spec-newer-gaps-map`, `18-spec-newer-challenges-map` | `check-feature` |
| (bypass when run-log ok) | `16-graph-gate-run-log`, `10-no-challenges-file` | invariant false → later rules |

Runs after `alignment_limit_exhausted`, `not_has_context`, `not_has_spec` — before P40+ branch rules.

## `dispatch.spec.rules` (priority / when / next / fixture)

| P | when | next | outcome | Fixture |
|---|------|------|---------|---------|
| 5 | `routing_state_needs_refresh` | analyze-routing | | routing-poc `02`/`03` (spec 24 cases inject fresh JSON) |
| 10 | `alignment_limit_exhausted` | — | stopped | `15-alignment-limit-stopped` |
| 20 | `not_has_context` | find-context | | `01-no-context` |
| 30 | `not_has_spec` | write-feature | | `02-no-spec` |
| 40 | `needs_answer_with_gaps` | resolve-gaps | | `06-needs-answer-gaps` |
| 45 | `needs_answer_alignment_only` | resolve-code-alignment | | `22-needs-answer-alignment-only` |
| 50 | `needs_answer_challenges_only` | resolve-challenges | | `08-needs-answer-challenges` |
| 60 | `pending_apply_with_gaps` | resolve-gaps | | `07-pending-apply-gaps` |
| 65 | `pending_apply_alignment_only` | resolve-code-alignment | | `23-pending-apply-alignment-only`, `24-mixed-pending-apply-align-ch` |
| 70 | `pending_apply_challenges_only` | resolve-challenges | | `17-pending-apply-challenges` |
| 80 | `critical_major_mismatch_resolvable` | resolve-code-alignment | | `14-alignment-fail-mismatch` |
| 90 | `open_gaps` | resolve-gaps | | `05-open-gaps`, `16-graph-gate-run-log` |
| 100 | `open_challenges` | resolve-challenges | | `09-open-challenges` |
| 110 | `no_challenges_file` | challenge-feature | | `10-no-challenges-file` |
| 120 | `alignment_missing_or_stale` | check-feature-code | | `11-no-alignment`, `12-stale-alignment`, `21-alignment-stale-mismatch` |
| 130 | `alignment_pass` | — | ready | `13-alignment-pass`, `19-alignment-pass-with-gaps` |
| 140 | `alignment_fail_reaudit` | check-feature-code | | `20-alignment-fail-no-critical-mismatch` |

## Out of scope (phase 0–2)

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

Phase 1+ (registry compile) must keep **dispatch-golden** green (spec 24 cases + calibration 1 orchestrator_only)
and **golden-coverage:packs** (every `pipelines/<id>/` has a golden folder or waiver).

Unit tests for `parse_alignment` / DECISIONS parsing: `scripts/feature_status_test.py`
(imports `routing_state_baseline`).

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

`needs_check_feature` lives in JSON fields; hook `sync_routing_state_after_step`
stamps `step_completion` only after pack `sync_after_steps` (spec: check-feature)
and pack `refresh_fields` clears the invariant. Mutating steps are not stamped —
JSON stays stale → P5 `analyze-routing`. Golden `25-check-feature-stamped-json`.
`stale` / `alignment_stale` are engine mtime after overlay.

P5 `routing_state_needs_refresh` → `analyze-routing` when JSON is missing,
stale, or invalid (spec `00-no-json-no-context`, `26-spec-newer-than-json`,
routing-poc `03-stale-json`). Live overlay does not use baseline; baseline is
CI/replay only.

Gate vs mutate (hook `sync_after_step` in the golden runner):

| Case | Meaning | Next |
|------|---------|------|
| `26-spec-newer-than-json` | SPEC newer than JSON | analyze-routing |
| `27-check-feature-stamp-no-file-change` | check-feature ok, files unchanged | resolve-gaps (stamp) |
| `28-write-feature-does-not-stamp` | write-feature ok, SPEC newer | analyze-routing |
| `29-check-feature-after-spec-edit` | check-feature ok, but SPEC newer | analyze-routing |

## Invariant (after P10–P70, before P80+)

| Invariant | Fixtures | Effect |
|-----------|----------|--------|
| `needs-check-feature` | `03-spec-needs-check`, `04-spec-newer-gaps-map`, `18-spec-newer-challenges-map` | `check-feature` |
| pending-apply beats invariant | `30-pending-apply-beats-needs-check` | `resolve-challenges` even if `needs_check_feature` |
| graph from `challenge-feature` | `31-graph-from-challenge-skips-check` | same, with run-log origin — no edge to check-feature |
| (JSON stamp / hook sync) | `25-check-feature-stamped-json`, `27-check-feature-stamp-no-file-change`, `16-graph-gate-run-log`, `10-no-challenges-file` | invariant false → later rules |

Runs after needs-answer / pending-apply (P40–70). A SPEC edit must not skip apply.

## `dispatch.spec.rules` (priority / when / next / fixture)

| P | when | next | outcome | Fixture |
|---|------|------|---------|---------|
| 5 | `routing_state_needs_refresh` | analyze-routing | | missing / stale / invalid JSON (`00-no-json-no-context`, `26`–`29`) |
| 10 | `alignment_limit_exhausted` | — | stopped | `15-alignment-limit-stopped` |
| 20 | `not_has_context` | find-context | | `01-no-context` (after JSON exists) |
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

Phase 1+ (registry compile) must keep **dispatch-golden** green (spec 30 cases + calibration 1 orchestrator_only)
and **golden-coverage:packs** (every `pipelines/<id>/` has a golden folder or waiver).

Unit tests for `parse_alignment` / DECISIONS parsing: `scripts/feature_status_test.py`
(imports `routing_state_baseline`).

# Pipeline router (phase 2)

Declarative next-step routing for the **spec** pipeline. Topology stays in `pipelines.spec`; **when** to take each branch lives in `dispatch.spec`.

**Cutover complete:** `feature_status.choose_next_step()` always calls `pipeline_router.apply_router_decision()`. There is no legacy imperative router.

## Source files

| File | Role |
|------|------|
| `pipeline.yaml` → `dispatch.spec` | Invariants + ordered rules |
| `generated/pipeline_registry.json` | Compiled dispatch block (via `--apply`) |
| `pipeline_router.py` | Named predicates, invariant gate, rule chain |
| `feature_status.py` | `build_status_fields()` + `choose_next_step()` → router |

## DSL

### Invariants (global, before rules)

Run once per dispatch, **after rules P10–P30** (alignment limit, context, spec) and before P40+.

- `needs-check-feature` — same logic as `needs_check_feature()` (mtime, GAPS_MAP, CHALLENGES_MAP, run-log). Forces `check-feature` when true.

### Rules

Each rule:

```yaml
- priority: 90          # unique, lower = earlier
  when: open_gaps        # named predicate (Python, not eval)
  next: resolve-gaps     # step id, or null for terminal
  outcome: ready         # optional: ready | stopped (required when next: null)
```

Terminal outcomes:

- `outcome: stopped` — empty next, `orchestrator_mode=stopped`
- `outcome: ready` — empty next, `ready=true`, `orchestrator_mode=ready`

`_finalize_orchestrator_mode()` still sets `ask_user`, `write_feature_cycle`, `delegate`, `must_continue`.

## Add a rule

1. Implement predicate in `pipeline_router.py` (`PREDICATES` + `reason_for_predicate`).
2. Add to `KNOWN_PREDICATES`.
3. Append rule to `dispatch.spec.rules` in `pipeline.yaml` with a **new unique priority** (respect order vs neighbours).
4. Add golden fixture in `fixtures/dispatch_golden/cases.json` + row in `COVERAGE.md`.
5. `pipeline_compile.py --apply` → run golden + smoke.

## Tests

```bash
PYTHONPATH=scripts python3 scripts/pipeline_dispatch_golden_test.py
PYTHONPATH=scripts python3 scripts/pipeline_smoke_test.py   # includes dispatch-golden
PYTHONPATH=scripts python3 scripts/feature_status_test.py
```

Golden fixtures exercise `build_dispatch()` → compiled router end-to-end.

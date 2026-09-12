# Pipeline router (phase 2)

Declarative next-step routing for the **spec** pipeline. Topology stays in `pipelines.spec`; **when** to take each branch lives in `dispatch.spec`.

## Feature flag

| Value | Path |
|-------|------|
| `PIPELINE_COMPILED_ROUTER=0` (default) | `feature_status._choose_next_step_legacy()` |
| `PIPELINE_COMPILED_ROUTER=1` | `pipeline_router.apply_router_decision()` |

Golden tests always use legacy (default). Parity test compares legacy vs router on all 20 fixtures without changing production default.

Switch default to `1` only after `router-parity` is green in smoke and you accept the behavior lock.

## Source files

| File | Role |
|------|------|
| `pipeline.yaml` → `dispatch.spec` | Invariants + ordered rules |
| `generated/pipeline_registry.json` | Compiled dispatch block (via `--apply`) |
| `pipeline_router.py` | Named predicates, invariant gate, rule chain |
| `feature_status.py` | `build_status_fields()` + flag in `choose_next_step()` |

## DSL

### Invariants (global, before rules)

Run once per dispatch, **after rules P10–P30** (alignment limit, context, spec) and before P40+. Same slot as legacy graph gate.

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
5. `pipeline_compile.py --apply` → run golden + `pipeline_router_parity_test.py`.

## Tests

```bash
PYTHONPATH=scripts python3 scripts/pipeline_router_parity_test.py
PYTHONPATH=scripts python3 scripts/pipeline_dispatch_golden_test.py
PYTHONPATH=scripts python3 scripts/pipeline_smoke_test.py   # includes router-parity
```

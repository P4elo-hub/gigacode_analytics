# Pipeline router

Declarative next-step routing. Topology is `pipelines/<id>/graph.yaml`.
**when** names live in `dispatch.yaml` and must be in that pipeline's predicate catalog.

`--pipeline` (default `spec`) selects the graph. `load_dispatch(pipeline_id)`
returns the compiled block or `None`. Missing/empty rules are valid (Option A:
calibration has a graph, no router; API → `dispatch_supported: false`).

## Source files

| File | Role |
|------|------|
| `pipelines/<id>/dispatch.yaml` | Invariants + ordered rules + fallback |
| `pipelines/<id>/status.yaml` | Artifacts, collectors, stale |
| `pipelines/<id>/predicates.py` | Domain `when:` implementations |
| `scripts/pipeline_predicates.py` | Core catalog + merge |
| `scripts/pipeline_status.py` | `load_status_spec(pipeline_id)` + generic builder |
| `generated/pipeline_registry.json` | Compiled dispatch + status |

Status YAML schema: [PIPELINE-STATUS.md](PIPELINE-STATUS.md).

## DSL

YAML is still only `priority` + `when` + `next` (+ optional `outcome`). No formulas.

### Invariants

Run after rules with `priority <= invariant_after_priority`. Spec keeps the
slot at 70 (after needs-answer / pending-apply) but the list is empty:
`needs_check_feature` is a regular P75 `when:` → `check-feature`, same catalog
as the other arrows.

When run-log / JSON `position` says where we stand, a rule whose `next` is
not an outgoing graph edge is skipped. Incomplete step (`retry`/`fail`) may
repeat itself. No position (empty log) → unconstrained rules (first step / goldens).

### Rules

```yaml
- priority: 90
  when: open_gaps
  next: resolve-gaps
```

`when` must be in `catalog_names(pipeline_id)` (core auto-names from artifacts +
counters in `status.yaml` + pack domain). Compile also requires an implementation
and a non-empty `reason_for`.

New semantics: register a predicate in the pack, do not edit the router.
See [PIPELINE-PREDICATES.md](PIPELINE-PREDICATES.md).

## Tests

```bash
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --check
PYTHONPATH=scripts python3 -m unittest discover scripts -p '*_test.py'
PYTHONPATH=scripts python3 scripts/pipeline_dispatch_golden_test.py
```

Golden lives in `fixtures/dispatch_golden/<pipeline_id>/cases.json`.
Every pack must have that folder (or `WAIVER.md` for no-dispatch).
Policy: [PIPELINE-GOLDEN.md](PIPELINE-GOLDEN.md).
Predicate/routing catalog checks run through the active engine test suite.

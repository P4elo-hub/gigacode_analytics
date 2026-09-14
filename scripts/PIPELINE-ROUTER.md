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

## DSL

YAML is still only `priority` + `when` + `next` (+ optional `outcome`). No formulas.

### Invariants

Run after rules with `priority <= invariant_after_priority` (spec: 30).

- spec: `needs-check-feature` → `check-feature`

### Rules

```yaml
- priority: 90
  when: open_gaps
  next: resolve-gaps
```

`when` must be in `catalog_names(pipeline_id)` (core auto-names from artifacts + pack domain).

New semantics: register a predicate in the pack, do not edit the router.

## Tests

```bash
PYTHONPATH=scripts python3 scripts/pipeline_dispatch_golden_test.py
PYTHONPATH=scripts python3 scripts/pipeline_smoke_test.py
```

Golden lives in `fixtures/dispatch_golden/<pipeline_id>/cases.json`.

# Pipeline compile (packs)

Source of truth: `pipelines/<id>/{graph,dispatch,status,registry}.yaml`.

Generated artifacts:

| Output | Purpose |
|--------|---------|
| `scripts/pipeline_schema.json` | Graph topology for viewer, hooks, delegate |
| `scripts/generated/pipeline_registry.json` | Per-pipeline mapping, dispatch, status, predicates |

Registry YAML (step → subagent, gated, restart, delegate_modes):
[PIPELINE-REGISTRY.md](PIPELINE-REGISTRY.md).

Step ids are unique **inside** a pipeline. Compile checks each
`step_to_subagent` key against that pack's graph nodes and each subagent
against `.qwen` / `.gigacode` / `.opencode` agents. Mapping in the JSON lives
only under `pipelines.<id>` (no top-level spec copy).

## Commands

```bash
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --check
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --apply
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --catalog
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --from-json pack.json
```

Status contract (artifacts / collectors): [PIPELINE-STATUS.md](PIPELINE-STATUS.md).
Predicate catalog (`when:` names): [PIPELINE-PREDICATES.md](PIPELINE-PREDICATES.md).
Registry: [PIPELINE-REGISTRY.md](PIPELINE-REGISTRY.md).

`--check` rejects unknown `when:`, empty reasons,
`DOMAIN_PREDICATE_NAMES` ≠ `PREDICATES`, and registry steps not in the graph.

## Tests

Registry has a **thin** smoke check (`pipeline-registry:scoped`). Full suite
is `pipeline_registry_test.py`. Predicates stay out of smoke.

After `--apply`:

```bash
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --check
PYTHONPATH=scripts python3 scripts/pipeline_dispatch_golden_test.py
PYTHONPATH=scripts python3 scripts/pipeline_smoke_test.py
python3 scripts/feature_status_test.py
PYTHONPATH=scripts python3 scripts/pipeline_predicates_test.py   # not part of smoke
PYTHONPATH=scripts python3 scripts/pipeline_registry_test.py     # full suite (smoke has scoped check only)
```

`pipeline_registry_test.py`: `registry_for("calibration")` ≠ spec, calibration
steps do not resolve via spec, hook gated uses active-task + `--pipeline`,
compile rejects a mapped step missing from the graph, calibration restart
rolls back `Calibration/<slug>/` only. Smoke only has `pipeline-registry:scoped`.

## Edit workflow

1. Change the pack under `pipelines/<id>/` (not `scripts/pipeline.yaml`).
2. `--check` → review validation + diff.
3. `--apply` → commit YAML + generated JSON together.
4. Golden (`fixtures/dispatch_golden/<id>/cases.json`) + smoke must stay green.

Spec pack is the reference (24+ dispatch cases). New packs need their own golden folder.

See `pipelines/README.md`, [PIPELINE-RUNTIME.md](PIPELINE-RUNTIME.md), and [PIPELINE-REGISTRY.md](PIPELINE-REGISTRY.md).

# Pipeline compile (packs)

Source of truth: `pipelines/<id>/{graph,dispatch,status,registry}.yaml`.

Generated artifacts:

| Output | Purpose |
|--------|---------|
| `scripts/pipeline_schema.json` | Graph topology for viewer, hooks, delegate |
| `scripts/generated/pipeline_registry.json` | Per-pipeline mapping, dispatch, status, predicates |

## Commands

```bash
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --check
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --apply
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --catalog
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --from-json pack.json
```

After `--apply`:

```bash
PYTHONPATH=scripts python3 scripts/pipeline_dispatch_golden_test.py
PYTHONPATH=scripts python3 scripts/pipeline_smoke_test.py
PYTHONPATH=scripts python3 scripts/feature_status_test.py
```

## Edit workflow

1. Change the pack under `pipelines/<id>/` (not `scripts/pipeline.yaml`).
2. `--check` → review validation + diff.
3. `--apply` → commit YAML + generated JSON together.
4. Golden (`fixtures/dispatch_golden/<id>/cases.json`) + smoke must stay green.

Spec pack is the reference (24+ dispatch cases). New packs need their own golden folder.

See `pipelines/README.md` and `PIPELINE-RUNTIME.md`.

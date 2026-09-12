# Pipeline compile (phase 1)

Single source of truth: `scripts/pipeline.yaml`.

Generated artifacts:

| Output | Purpose |
|--------|---------|
| `scripts/pipeline_schema.json` | Graph topology for viewer, hooks, delegate |
| `scripts/generated/pipeline_registry.json` | Step→subagent mapping, gated subagents, restart order |

## Commands

```bash
# Validate YAML + diff against generated files (no writes)
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --check

# Regenerate schema + registry after editing pipeline.yaml
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --apply
```

After `--apply`, run the invariant suite:

```bash
PYTHONPATH=scripts python3 scripts/pipeline_dispatch_golden_test.py
PYTHONPATH=scripts python3 scripts/pipeline_smoke_test.py
```

Smoke includes `pipeline-compile` parity check.

## Edit workflow

1. Change topology or mapping in `pipeline.yaml` only.
2. `--check` → review diff report.
3. `--apply` → commit YAML + generated JSON together.
4. Golden + smoke must stay green before merge.

**Not in phase 1:** declarative routing (`choose_next_step`), viewer edit UI, step order changes without explicit intent.

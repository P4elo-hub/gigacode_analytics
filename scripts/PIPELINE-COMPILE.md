# Pipeline compile (phase 1–2)

Single source of truth: `scripts/pipeline.yaml`.

Generated artifacts:

| Output | Purpose |
|--------|---------|
| `scripts/pipeline_schema.json` | Graph topology for viewer, hooks, delegate |
| `scripts/generated/pipeline_registry.json` | Step→subagent mapping, gated subagents, restart order, **dispatch.spec** |

## Commands

```bash
# Validate YAML + diff against generated files (no writes)
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --check

# Regenerate schema + registry after editing pipeline.yaml
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --apply
```

After `--apply`, run the invariant suite:

```bash
PYTHONPATH=scripts python3 scripts/pipeline_dispatch_golden_test.py   # 20/20 legacy
PYTHONPATH=scripts python3 scripts/pipeline_router_parity_test.py     # 20/20 legacy ≡ router
PYTHONPATH=scripts python3 scripts/pipeline_smoke_test.py             # includes both + compile
```

Smoke includes `pipeline-compile` parity check and `router-parity`.

## Edit workflow

1. Change topology, mapping, or **dispatch rules** in `pipeline.yaml` only.
2. `--check` → review diff report (includes dispatch schema validation).
3. `--apply` → commit YAML + generated JSON together.
4. Golden + router-parity + smoke must stay green before merge.

**Phase 2:** declarative routing in `dispatch.spec` — see `PIPELINE-ROUTER.md`. Production still uses legacy until `PIPELINE_COMPILED_ROUTER=1`.

**Not in scope:** viewer edit UI, calibration dispatch, hooks/delegate graph gate changes.

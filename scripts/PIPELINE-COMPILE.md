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
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --export-json spec
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --init-pack <id> [--template minimal]
```

Authoring (new pack without engine edits): [PIPELINE-PACK-AUTHORING.md](PIPELINE-PACK-AUTHORING.md).
JSON schema: [pipeline_pack_schema.json](pipeline_pack_schema.json).

Status contract (artifacts / collectors): [PIPELINE-STATUS.md](PIPELINE-STATUS.md).
Predicate catalog (`when:` names): [PIPELINE-PREDICATES.md](PIPELINE-PREDICATES.md).
Registry: [PIPELINE-REGISTRY.md](PIPELINE-REGISTRY.md).

`--check` rejects unknown `when:`, empty reasons,
`DOMAIN_PREDICATE_NAMES` ≠ `PREDICATES`, and registry steps not in the graph.
`--from-json` validates the payload against `pipeline_pack_schema.json` before YAML write.

## Routing-state (Phase 10–11)

Analyzer writes `ROUTING_STATE` JSON; router reads overlay via `populate_status`.
Spec collectors stay until Phase 12. Contract:
[PIPELINE-ROUTING-STATE.md](PIPELINE-ROUTING-STATE.md),
[PIPELINE-PARITY.md](PIPELINE-PARITY.md).
Live pack graph: `pipelines/routing-poc/`. Spec pack: gated overlay collector +
shadow `routing_conditions.yaml`.

**Phase 11 contract**

1. **Smoke не добавляет `dispatch:routing-poc` / `pipeline-delegate:routing-poc`.**
   Pack покрыт `dispatch-golden` + `pipeline-compile` + `golden-coverage:packs`.
2. **Compile чеклист после правок overlay / pack YAML** (после `--apply`):
   ```bash
   PYTHONPATH=scripts python3 scripts/pipeline_compile.py --check
   PYTHONPATH=scripts python3 scripts/pipeline_routing_state_test.py
   PYTHONPATH=scripts python3 scripts/routing_state_parity_test.py
   PYTHONPATH=scripts python3 scripts/pipeline_dispatch_golden_test.py
   PYTHONPATH=scripts python3 scripts/pipeline_golden_coverage_test.py
   PYTHONPATH=scripts python3 scripts/pipeline_smoke_test.py
   PYTHONPATH=scripts python3 scripts/routing_state_parity.py pipeline-viewer-smoke --strict
   ```
   Spec golden ids не сокращать. `routing-poc` ≥ 3 cases.
3. **Skill** заполняет `fields` по `pipelines/spec/routing_conditions.yaml`
   (семантика = collectors). Phase 12: collectors снимают.
4. **Stale spec** — JSON vs spec / context / decisions / challenges / alignment /
   gaps_map / challenges_map. POC stale — только vs spec.
5. **Live dispatch** collectors-first. Overlay только B-mode / свежий JSON.
   `analyze-routing` **не** в spec `graph.yaml`.

## Authoring (Phase 8)

New pipeline = pack + agents/skills. Not a fork of the engine.

1. `--init-pack <id>` (templates: `minimal`, `orchestrator-only`, `full-dispatch`) or `--from-json`.
2. Copy `scripts/fixtures/pack_authoring/orchestrator-agent.md` → `*/agents/<id>-orchestrator.md`.
3. `--apply` → `--check` (новый pack: apply первым, иначе `--check` = drift).
4. Smoke after apply: schema contains `<id>`; `pipeline_delegate.py … --pipeline <id>`.
5. Dispatch optional: empty rules = calibration-style (`orchestrator_only`).
   Full dispatch = spec-style; add `predicates.py` for domain `when:` and golden under
   `fixtures/dispatch_golden/<id>/` (required — [PIPELINE-GOLDEN.md](PIPELINE-GOLDEN.md)).

`--catalog` is the versioned UI palette (`catalog_version`, `pack_schema`, steps,
predicates core vs `by_pipeline`, `runtime.<id>.loop`). Additive keys only.
`--from-json` = schema (shape) then compile (`when:` / agents). Schema runtime is
a subset walker; `pipeline_pack_schema.json` is the UI `$schema`. Agent files and
dispatch golden for a new pack are manual. Coverage gate is Phase 9 done. See
[PIPELINE-PACK-AUTHORING.md](PIPELINE-PACK-AUTHORING.md).

## Tests

Registry has a **thin** smoke check (`pipeline-registry:scoped`). Full suite
is `pipeline_registry_test.py`. Predicates stay out of smoke.

After `--apply`:

```bash
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --check
PYTHONPATH=scripts python3 scripts/pipeline_dispatch_golden_test.py
PYTHONPATH=scripts python3 scripts/pipeline_golden_coverage_test.py  # pack ↔ golden / waiver
PYTHONPATH=scripts python3 scripts/pipeline_smoke_test.py
python3 scripts/feature_status_test.py
PYTHONPATH=scripts python3 scripts/pipeline_predicates_test.py   # not part of smoke
PYTHONPATH=scripts python3 scripts/pipeline_registry_test.py     # full suite (smoke has scoped check only)
PYTHONPATH=scripts python3 scripts/pipeline_runtime_test.py      # pack-first validate + orchestrator loop
PYTHONPATH=scripts python3 scripts/pipeline_pack_test.py         # schema, catalog, --from-json, --init-pack
PYTHONPATH=scripts python3 scripts/pipeline_routing_state_test.py
PYTHONPATH=scripts python3 scripts/routing_state_parity_test.py
```

`pipeline_registry_test.py`: `registry_for("calibration")` ≠ spec, calibration
steps do not resolve via spec, hook gated uses active-task + `--pipeline`,
compile rejects a mapped step missing from the graph, calibration restart
rolls back `Calibration/<slug>/` only. Smoke only has `pipeline-registry:scoped`.

`pipeline_runtime_test.py`: pack-first validate (calibration extra_advice without
engine duplicate), spec extra_advice severity matrix, orchestrator runtime loop
block in agents/rules. Not part of smoke (smoke has `validate:calibration:<slug>`).

`pipeline_routing_state_test.py`: overlay schema + spec gating + validate ids +
fake JSON dispatch. `routing_state_parity_test.py`: A vs B replay. Not smoke
rows — see **Routing-state (Phase 10–11)** checklist above.
Smoke still does **not** call `pipeline_delegate --pipeline routing-poc`.

## Edit workflow

1. Change the pack under `pipelines/<id>/` (not `scripts/pipeline.yaml`).
2. `--check` → review validation + diff.
3. `--apply` → commit YAML + generated JSON together.
4. Golden (`fixtures/dispatch_golden/<id>/cases.json` or `WAIVER.md`) + smoke must stay green.
   Smoke: `dispatch-golden N/N` and `golden-coverage:packs`.

Spec pack is the reference (24+ dispatch cases). Every pack needs its own golden
folder or a no-dispatch waiver — [PIPELINE-GOLDEN.md](PIPELINE-GOLDEN.md).

See `pipelines/README.md`, [PIPELINE-GOLDEN.md](PIPELINE-GOLDEN.md),
[PIPELINE-PACK-AUTHORING.md](PIPELINE-PACK-AUTHORING.md),
[PIPELINE-RUNTIME.md](PIPELINE-RUNTIME.md), [PIPELINE-REGISTRY.md](PIPELINE-REGISTRY.md),
and [PIPELINE-ROUTING-STATE.md](PIPELINE-ROUTING-STATE.md).

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
`DOMAIN_PREDICATE_NAMES` ≠ `PREDICATES`, registry steps not in the graph,
and (Phase 13) dispatch `when:` missing from `edge_conditions` **and** core, plus
`dispatch.rules` drift vs `edge_conditions.dispatch`.
`--from-json` validates the payload against `pipeline_pack_schema.json` before YAML write.

## Routing-state (Phase 12)

Analyzer writes `ROUTING_STATE` JSON; router reads overlay via `populate_status`.
Spec live path is overlay-only. Contract:
[PIPELINE-ROUTING-STATE.md](PIPELINE-ROUTING-STATE.md),
[PIPELINE-PARITY.md](PIPELINE-PARITY.md).
Live spec graph includes `analyze-routing`. Pack `routing-poc` remains as
reference.

**Phase 12 contract**

1. **Regression не добавляет отдельный `dispatch:routing-poc` / `pipeline-delegate:routing-poc`.**
   Pack покрыт `dispatch-golden` + `pipeline-compile`; pack coverage проверяется
   строкой `coverage:packs` внутри `pipeline_dispatch_golden_test.py`.
   `routing-poc` заархивирован, активные cases остаются у `calibration` и `spec-v2`.
2. **Compile чеклист после правок overlay / pack YAML** (после `--apply`):
   ```bash
   PYTHONPATH=scripts python3 scripts/pipeline_compile.py --check
   PYTHONPATH=scripts python3 -m unittest discover scripts -p '*_test.py'
   PYTHONPATH=scripts python3 scripts/pipeline_dispatch_golden_test.py
   PYTHONPATH=scripts python3 scripts/routing_state_parity.py pipeline-viewer-smoke --strict
   ```
   `spec-v2` golden ids не сокращать. `expect` cases держать без изменений.
3. **Skill** заполняет `fields` по `pipelines/spec/routing_conditions.yaml`.
   Hot-path collectors не парсят домен.
4. **Stale spec** — JSON vs spec / context / decisions / challenges / alignment /
   gaps_map / challenges_map. POC stale — только vs spec.
5. **Live dispatch** overlay always-on (`collector_mode: routing_state`).
   `analyze-routing` **в** spec `graph.yaml`. JSON freshness = P5 + extra_advice block.

## Phase 13 (edge_conditions authoring)

1. Label graph edges / PlantUML → `pipeline_routing_codegen.py --apply`.
2. Review `routing_conditions.yaml` `edge_conditions` (formulas) and `status_fields` (analyzer).
3. `--apply` compile then `--check`. `when:` must have `edge_conditions` or core.
4. Spec 24 golden `expect` unchanged. Interpreter must match former Python predicates.
5. `--catalog` `catalog_version` 2 includes `routing_conditions.<id>`.

```bash
PYTHONPATH=scripts python3 scripts/pipeline_routing_codegen.py --pipeline spec-v2 --apply
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --apply
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --check
PYTHONPATH=scripts python3 -m unittest discover scripts -p '*_test.py'
PYTHONPATH=scripts python3 scripts/pipeline_dispatch_golden_test.py
```

## Authoring (Phase 8)

New pipeline = pack + agents/skills. Not a fork of the engine.

1. `--init-pack <id>` (templates: `minimal`, `orchestrator-only`, `full-dispatch`, `routing-state`) or `--from-json`.
2. Copy `scripts/fixtures/pack_authoring/orchestrator-agent.md` → `*/agents/<id>-orchestrator.md`.
3. `--apply` → `--check` (новый pack: apply первым, иначе `--check` = drift).
4. Regression after apply: schema contains `<id>`; `pipeline_delegate.py … --pipeline <id>`.
5. Dispatch optional: empty rules = calibration-style (`orchestrator_only`).
   Full dispatch = spec-style; `edge_conditions` (Phase 13) for domain `when:`;
   golden under `fixtures/dispatch_golden/<id>/` (required — [PIPELINE-GOLDEN.md](PIPELINE-GOLDEN.md)).

`--catalog` is the versioned UI palette (`catalog_version` **2**, `pack_schema`, steps,
predicates core vs `by_pipeline`, `routing_conditions.<id>.fields` / `.edge_conditions`,
`runtime.<id>.loop`). Additive keys only.
`--from-json` = schema (shape) then compile (`when:` / agents). Schema runtime is
a subset walker; `pipeline_pack_schema.json` is the UI `$schema`. Agent files and
dispatch golden for a new pack are manual. Coverage gate is Phase 9 done. See
[PIPELINE-PACK-AUTHORING.md](PIPELINE-PACK-AUTHORING.md).

## Tests

Registry, runtime, hooks, routing-state and routing-codegen checks live in the
active unittest suite.

After `--apply`:

```bash
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --check
PYTHONPATH=scripts python3 -m unittest discover scripts -p '*_test.py'
PYTHONPATH=scripts python3 scripts/pipeline_dispatch_golden_test.py
PYTHONPATH=scripts python3 scripts/pipeline_delegate.py --pipeline spec-v2 --slug my-v2-demo --dry-run
```

`python3 -m unittest discover ...` подхватывает активные engine/authoring tests:
registry, hooks, runtime, routing-state, routing-codegen, active-task и pack authoring.
`pipeline_dispatch_golden_test.py` включает `coverage:packs`.

## Edit workflow

1. Change the pack under `pipelines/<id>/` (not `scripts/pipeline.yaml`).
2. `--check` → review validation + diff.
3. `--apply` → commit YAML + generated JSON together.
4. Golden (`fixtures/dispatch_golden/<id>/cases.json` or `WAIVER.md`) + engine tests must stay green.
   Dispatch golden includes `dispatch-golden N/N` and `coverage:packs`.

Spec pack is the reference (24+ dispatch cases). Every pack needs its own golden
folder or a no-dispatch waiver — [PIPELINE-GOLDEN.md](PIPELINE-GOLDEN.md).

See `pipelines/README.md`, [PIPELINE-GOLDEN.md](PIPELINE-GOLDEN.md),
[PIPELINE-PACK-AUTHORING.md](PIPELINE-PACK-AUTHORING.md),
[PIPELINE-RUNTIME.md](PIPELINE-RUNTIME.md), [PIPELINE-REGISTRY.md](PIPELINE-REGISTRY.md),
and [PIPELINE-ROUTING-STATE.md](PIPELINE-ROUTING-STATE.md).

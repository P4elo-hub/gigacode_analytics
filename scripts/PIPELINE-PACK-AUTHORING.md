# Pipeline pack authoring (Phase 8)

Pack = one folder `pipelines/<id>/`. Compile merges every pack into
`scripts/pipeline_schema.json` and `scripts/generated/pipeline_registry.json`.
**Do not edit** `pipeline_validate.py`, `pipeline_delegate.py`, or the router
to add a scenario.

JSON contract (frontend / `--from-json`): [pipeline_pack_schema.json](pipeline_pack_schema.json).
Catalog (UI palette): `PYTHONPATH=scripts python3 scripts/pipeline_compile.py --catalog`.
Runtime loop: [PIPELINE-RUNTIME.md](PIPELINE-RUNTIME.md).

**Порядок нового pack:** `--init-pack` → скопировать orchestrator agent → `--apply` → `--check` → golden (`cases.json` или `WAIVER.md`) → `pipeline_delegate --pipeline <id>`.
`--init-pack` **не** делает `--apply`. Golden на каждый pack — обязательно ([PIPELINE-GOLDEN.md](PIPELINE-GOLDEN.md), Phase 9 done).

## Phase 8 contract (намеренные границы)

1. **Два уровня валидации.** `validate_pack_json` (schema) проверяет форму payload: `id` / `graph` / `status` / `registry`. Не проверяет `when:` в predicate catalog и наличие agents — это compile `validate_source`. Тесты: `test_unknown_subagent_tells_author_to_add_agent`, `test_schema_ok_unknown_when_fails_compile`.
2. **Schema runtime — subset, не `jsonschema`.** Файл [pipeline_pack_schema.json](pipeline_pack_schema.json) (`$schema` Draft 2020-12) — контракт для UI. Python ходит по нему через `_validate_schema()` (type / required / properties / items / pattern). Для текущих pack достаточно. Если фронт начнёт слать сложные payload — подключить `jsonschema` поверх того же файла, без смены schema.
3. **Orchestrator agent.** Шаблон: [fixtures/pack_authoring/orchestrator-agent.md](fixtures/pack_authoring/orchestrator-agent.md). `--init-pack` **не** пишет `.qwen/` / `.gigacode/` / `.opencode/`. Viewer **Apply** создаёт `<id>-orchestrator.md` во всех трёх CLI из шаблона; повторный Apply **не** затирает ручные правки без `overwrite_orchestrator: true` (чекбокс в модалке).
4. **`--init-pack` без `--apply`.** Generated JSON обновляется только `--apply` (или `--from-json`, который apply делает). До apply: `--check` = drift, delegate = `unknown pipeline_id`.
5. **Golden (Phase 9 done).** Каждый pack: `fixtures/dispatch_golden/<id>/cases.json` или `WAIVER.md` (только no-dispatch). `spec-v2` — активный эталон, не сокращать cases. `full-dispatch` template компилируется; после init добавь golden. Policy + parity test: [PIPELINE-GOLDEN.md](PIPELINE-GOLDEN.md).

## Who writes what

| Concern | Spec-v2 today | Calibration today | Authoring target |
|---------|------------|-------------------|------------------|
| graph / dispatch / status / registry | Full 4 YAML; dispatch 24+ rules | 4 YAML; dispatch empty (`dispatch_supported: false`) | Same 4 files. `dispatch` optional in JSON |
| optional `.py` | `collectors.py`, `predicates.py`, `validate.py` | `validate.py` only | Optional. Add when you parse files / domain `when:` / extra validate |
| orchestrator agent | `spec-orchestrator.md` + Runtime loop | `calibration-orchestrator.md` + Runtime loop | Copy [fixtures/pack_authoring/orchestrator-agent.md](fixtures/pack_authoring/orchestrator-agent.md) |
| golden / regression | `fixtures/dispatch_golden/spec-v2/` | `fixtures/dispatch_golden/calibration/` (`01-orchestrator-only`) | `--init-pack` → `fixtures/dispatch_golden/<id>/cases.json` (или `WAIVER.md` для no-dispatch) |

## New pipeline (checklist)

1. **Scaffold**
   ```bash
   PYTHONPATH=scripts python3 scripts/pipeline_compile.py --init-pack <id>
   # or: --init-pack <id> --template orchestrator-only
   # or: --init-pack <id> --template full-dispatch
   # or: --from-json pack.json
   ```
   `--init-pack` writes `pipelines/<id>/` and runs compile **validation** (not `--apply`).
   Template `full-dispatch` prints a hint to add `fixtures/dispatch_golden/<id>/cases.json`.
2. **Orchestrator + skills.** Copy
   `scripts/fixtures/pack_authoring/orchestrator-agent.md` to
   `.qwen/agents/<id>-orchestrator.md` (and `.gigacode/`, `.opencode/`).
   Replace `{pipeline_id}`. Add skills under `*/skills/<name>/SKILL.md` and
   matching agent files for each mapped subagent.
3. **`--apply` → `--check`**
   ```bash
   PYTHONPATH=scripts python3 scripts/pipeline_compile.py --apply
   PYTHONPATH=scripts python3 scripts/pipeline_compile.py --check
   ```
   Для **нового** pack сначала `--apply` (иначе `--check` падает: generated JSON
   ещё без `<id>`). Для правок уже существующего pack порядок обратный:
   `--check` (diff) → `--apply`. Missing mapped/gated agent →
   `add agent '<name>' — not in agent catalog`.
4. **Smoke** (после `--apply` — иначе `unknown pipeline_id`). Schema содержит
   `<id>`. Затем:
   `python3 scripts/pipeline_delegate.py <smoke-slug> --cli qwen --pipeline <id>`.
   `--catalog` читает YAML и может показать pack до `--apply`; delegate / runtime
   читают compiled schema.
5. **Dispatch vs no-dispatch**
   - **No dispatch** (calibration-style, templates `minimal` / `orchestrator-only`):
     empty `rules` / `invariants`. Orchestrator is linear (markdown + graph edges).
     Optional `validate.py` still runs (`extra_advice`).
   - **Full dispatch** (spec-style, template `full-dispatch`): `when:` names from
     the predicate catalog (core from `status.yaml` artifacts, domain from
     `predicates.py`).
6. **Golden (required).** After `--apply`, add the pack to the coverage gate:
   - **Full dispatch:** `scripts/fixtures/dispatch_golden/<id>/cases.json` (≥ 1 case)
     and `COVERAGE.md` mapping `when:` → fixture ids.
   - **No dispatch:** the same `cases.json` (calibration-style `orchestrator_only`
     is enough) **or** `WAIVER.md`. See [PIPELINE-GOLDEN.md](PIPELINE-GOLDEN.md).
   Smoke: `dispatch-golden N/N` plus `golden-coverage:packs`.
7. **Do not** change `scripts/pipeline_*.py` engine modules for topology or `when:` names.

## Templates (`--init-pack --template`)

| Template | Dispatch | First step | Init validation |
|----------|----------|------------|-----------------|
| `minimal` | none (like `pack_smoke/minimal`) | `only-step` orchestrator-owned | PASS (YAML) |
| `orchestrator-only` | none + fallback copy | `first-step` orchestrator-owned | PASS (YAML) |
| `full-dispatch` | one rule `not_has_main` → `first-step` | same, plus `status.artifacts.main` | PASS (YAML; core `when:` from artifact) |

`--init-pack` сам проверяет YAML (это не CLI `--check`). Generated JSON
появляется только после `--apply`. До `--apply` CLI `--check` покажет
`content differs` — это ожидаемо, не ошибка pack.

`full-dispatch` also prints: add `scripts/fixtures/dispatch_golden/<id>/cases.json`
(+ `COVERAGE.md`). No-dispatch templates hint `cases.json` or `WAIVER.md`.

## Pack JSON (`--from-json` / `--export-json`)

Required: `id`, `graph`, `status`, `registry`. Optional: `dispatch`.
`id` is kebab-case (`^[a-z][a-z0-9-]*$`). `graph.orchestrator` must be a node id.

```bash
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --from-json pack.json
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --export-json spec
```

`--from-json` validates **layer 1** against [pipeline_pack_schema.json](pipeline_pack_schema.json)
**before** writing YAML, then `--apply` (**layer 2** compile: `when:`, agents, graph).
Fixture: `scripts/fixtures/pack_smoke/minimal/pack.json`.

Python does not depend on the `jsonschema` package. The `$schema` field is for
the UI; `--from-json` uses the subset walker. Compile still rejects unknown
`when:` and missing agents after a schema-valid write.

## Catalog API (versioned)

`build_catalog()` / `--catalog` — additive keys only. Current contract:

| Key | Type | UI |
|-----|------|----|
| `catalog_version` | int | bump only on breaking change |
| `pipelines` | `[{id, label, orchestrator}]` | pipeline tabs |
| `agents` | `[str]` | subagent palette (union of `.qwen` / `.gigacode` / `.opencode`) |
| `skills` | `[str]` | skill palette |
| `steps` | `{<id>: [step_id]}` | node palette per pipeline |
| `predicates.core` | `[str]` | core `when:` names (union across packs) |
| `predicates.by_pipeline` | `{<id>: [str]}` | core + domain for that pack |
| `routing_conditions` | `{<id>: {fields, edge_conditions, stale_vs}}` | Phase 13: field palette + edge editor (`catalog_version` 2) |
| `runtime` | `{<id>: runtime_contract}` | loop commands (`--pipeline <id>`) |
| `pack_files` | `[str]` | YAML files in a pack |
| `optional_python` | `[str]` | `collectors.py` / `predicates.py` / `validate.py` |
| `pack_schema` | str | path to JSON schema |

`runtime.<id>.loop` is the Phase 7 block: delegate → action → append_run_log → ingest → validate.

## Tests

```bash
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --check
PYTHONPATH=scripts python3 -m unittest discover scripts -p '*_test.py'
PYTHONPATH=scripts python3 scripts/pipeline_dispatch_golden_test.py
```

## Phase 13 Authoring (graph edge → routing_conditions + dispatch)

**Choice A (runtime):** generic interpreter `evaluate_edge_condition(expr, status)` in
`scripts/pipeline_edge_conditions.py`. `when:` is still a name. The **body** lives in
`pipelines/<id>/routing_conditions.yaml` → `edge_conditions`. Spec `predicates.py` is a
thin wrapper (reasons + invariants). Do **not** add new domain functions there.

Frontend / PlantUML does not call the analyzer. Runtime dispatch stays deterministic.

### Flow

1. Draw the graph (PlantUML or UI). Label a branch arrow with a `when:` id (`open_gaps`)
   or human text (`gaps open` → slug `gaps_open`).
2. Codegen (review the YAML before compile apply):

```bash
PYTHONPATH=scripts python3 scripts/pipeline_routing_codegen.py \
  --pipeline spec-v2 --from-plantuml scripts/fixtures/routing_codegen/spec-sample.puml --dry-run
PYTHONPATH=scripts python3 scripts/pipeline_routing_codegen.py \
  --pipeline spec-v2 --from-plantuml path.puml --apply
# or bootstrap from graph.edges[].condition:
PYTHONPATH=scripts python3 scripts/pipeline_routing_codegen.py \
  --pipeline spec-v2 --from-graph-conditions --dry-run
# sync dispatch.rules from existing edge_conditions:
PYTHONPATH=scripts python3 scripts/pipeline_routing_codegen.py --pipeline spec-v2 --apply
```

3. Review `routing_conditions.yaml` (`status_fields` instructions, `expr`, `dispatch.priority` / `next`).
   Merge does **not** wipe hand-patched field instructions.
4. `PYTHONPATH=scripts python3 scripts/pipeline_compile.py --apply` then `--check`.
5. If you added a new `when:`, add a dispatch golden case (`scripts/PIPELINE-GOLDEN.md`).
   `spec-v2` expect values stay frozen.

`--apply` on compile does **not** run codegen. Codegen is a separate step first.

### PlantUML / UI convention

- `A --> B : open_gaps` — label is the condition id (preferred).
- `A --> B : gaps open` — codegen slugs to `gaps_open` and stubs `expr` / `status_fields`.
- Pack JSON: `graph.edges[].condition` (id) and optional `condition_label` (human).
- UI palette: `--catalog` → `routing_conditions.<id>.fields` (analyzer fields) and
  `.edge_conditions` (edge editor: id, label, priority, next). `catalog_version` is **2**.

### New pack with routing-state

`--init-pack <id> --template routing-state` adds `analyze-routing`, `routing_conditions.yaml`
stub, overlay collector, and P5 `routing_state_needs_refresh`. `--from-json` with
`status.collector_mode: routing_state` gets the same stub if `routing_conditions` is missing.
Gate-step hook stamp is opt-in: `status.routing_state_sync.sync_after_steps` (spec:
`check-feature`). Mutating steps are not listed — JSON stays stale → analyzer.

### Viewer Apply (pipeline-viewer)

`pack_authoring_api.apply_assembled` after free-text edges:

1. Stubs the same `when_id` into `dispatch.rules`, `edge_conditions` (`expr: field truthy`), and `status_fields.instruction`.
2. Merges routing-state `status` bits only (collector_mode / routing_state artifact) — does **not** copy spec domain artifacts.
3. Writes generic `collectors.py` = `COLLECTORS = {"routing_state": overlay_collector}` (never overwrites `pipelines/spec`).
4. Writes thin `predicates.py` reasons from labels **only if missing** (hand-written packs kept).
5. Writes CLI orchestrator md from the pack_authoring template (no silent overwrite).
6. Edges with `after_step: true` (work-step → `analyze-routing` refresh loop) keep **no** `when:` / bool field — not `has_agent_zakonchil_*`.
7. Response includes `checklist`: YAML / collectors / orchestrator / pack-local analyzer.

Universality gate: `PYTHONPATH=scripts:pipeline-viewer python3 scripts/pack_authoring_codegen_test.py`.
Session 3: `PYTHONPATH=scripts:pipeline-viewer python3 scripts/pack_authoring_session3_test.py`.

**UI dispatch table:** Apply treats the priority table as authoritative. Changed priority/next are written into `edge_conditions.*.dispatch`; deleted rows drop the when: from dispatch + (for authored bool stubs) from `status_fields` / graph edges, so stubs cannot resurrect them. Thin `predicates.py` is regenerated when still codegen-shaped.

### Add one edge condition (no predicates.py)

1. Put `condition: my_when` on a graph edge (or PlantUML label) and run codegen `--apply`.
2. Edit the new `edge_conditions.my_when.expr` (and `status_fields` instruction).
3. Set `dispatch.priority` / `next` (unique priority).
4. Compile `--apply` / `--check`. Add golden.

Coverage check: `PYTHONPATH=scripts python3 scripts/routing_conditions_extract.py --pipeline spec-v2 --check`.


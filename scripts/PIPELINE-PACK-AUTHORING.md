# Pipeline pack authoring (Phase 8)

Pack = one folder `pipelines/<id>/`. Compile merges every pack into
`scripts/pipeline_schema.json` and `scripts/generated/pipeline_registry.json`.
**Do not edit** `pipeline_validate.py`, `pipeline_delegate.py`, or the router
to add a scenario.

JSON contract (frontend / `--from-json`): [pipeline_pack_schema.json](pipeline_pack_schema.json).
Catalog (UI palette): `PYTHONPATH=scripts python3 scripts/pipeline_compile.py --catalog`.
Runtime loop: [PIPELINE-RUNTIME.md](PIPELINE-RUNTIME.md).

**Порядок нового pack:** `--init-pack` → скопировать orchestrator agent → `--apply` → `--check` → `pipeline_delegate --pipeline <id>`.
`--init-pack` **не** делает `--apply`. Golden на 3-й pipeline — Phase 9.

## Phase 8 contract (намеренные границы)

1. **Два уровня валидации.** `validate_pack_json` (schema) проверяет форму payload: `id` / `graph` / `status` / `registry`. Не проверяет `when:` в predicate catalog и наличие agents — это compile `validate_source`. Тесты: `test_unknown_subagent_tells_author_to_add_agent`, `test_schema_ok_unknown_when_fails_compile`.
2. **Schema runtime — subset, не `jsonschema`.** Файл [pipeline_pack_schema.json](pipeline_pack_schema.json) (`$schema` Draft 2020-12) — контракт для UI. Python ходит по нему через `_validate_schema()` (type / required / properties / items / pattern). Для текущих pack достаточно. Если фронт начнёт слать сложные payload — подключить `jsonschema` поверх того же файла, без смены schema.
3. **Orchestrator agent — руками.** Шаблон: [fixtures/pack_authoring/orchestrator-agent.md](fixtures/pack_authoring/orchestrator-agent.md). `--init-pack` **не** пишет `.qwen/` / `.gigacode/` / `.opencode/`. Шаг 2 чеклиста.
4. **`--init-pack` без `--apply`.** Generated JSON обновляется только `--apply` (или `--from-json`, который apply делает). До apply: `--check` = drift, delegate = `unknown pipeline_id`.
5. **Golden.** Эталон dispatch — только spec (24+). `full-dispatch` template компилируется; golden `fixtures/dispatch_golden/<id>/` — Phase 9.

## Who writes what

| Concern | Spec today | Calibration today | Authoring target |
|---------|------------|-------------------|------------------|
| graph / dispatch / status / registry | Full 4 YAML; dispatch 24+ rules | 4 YAML; dispatch empty (`dispatch_supported: false`) | Same 4 files. `dispatch` optional in JSON |
| optional `.py` | `collectors.py`, `predicates.py`, `validate.py` | `validate.py` only | Optional. Add when you parse files / domain `when:` / extra validate |
| orchestrator agent | `spec-orchestrator.md` + Runtime loop | `calibration-orchestrator.md` + Runtime loop | Copy [fixtures/pack_authoring/orchestrator-agent.md](fixtures/pack_authoring/orchestrator-agent.md) |
| golden / smoke | `fixtures/dispatch_golden/spec/` (24+) | no dispatch golden; smoke validate | `--init-pack` / `pack_smoke/minimal`; golden 3-го pack — Phase 9 |

## New pipeline (checklist)

1. **Scaffold**
   ```bash
   PYTHONPATH=scripts python3 scripts/pipeline_compile.py --init-pack <id>
   # or: --init-pack <id> --template orchestrator-only
   # or: --init-pack <id> --template full-dispatch
   # or: --from-json pack.json
   ```
   `--init-pack` writes `pipelines/<id>/` and runs compile **validation** (not `--apply`).
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
     `predicates.py`). Add `fixtures/dispatch_golden/<id>/` when you have rules.
6. **Do not** change `scripts/pipeline_*.py` engine modules for topology or `when:` names.

## Templates (`--init-pack --template`)

| Template | Dispatch | First step | Init validation |
|----------|----------|------------|-----------------|
| `minimal` | none (like `pack_smoke/minimal`) | `only-step` orchestrator-owned | PASS (YAML) |
| `orchestrator-only` | none + fallback copy | `first-step` orchestrator-owned | PASS (YAML) |
| `full-dispatch` | one rule `not_has_main` → `first-step` | same, plus `status.artifacts.main` | PASS (YAML; core `when:` from artifact) |

`--init-pack` сам проверяет YAML (это не CLI `--check`). Generated JSON
появляется только после `--apply`. До `--apply` CLI `--check` покажет
`content differs` — это ожидаемо, не ошибка pack.

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
| `runtime` | `{<id>: runtime_contract}` | loop commands (`--pipeline <id>`) |
| `pack_files` | `[str]` | YAML files in a pack |
| `optional_python` | `[str]` | `collectors.py` / `predicates.py` / `validate.py` |
| `pack_schema` | str | path to JSON schema |

`runtime.<id>.loop` is the Phase 7 block: delegate → action → append_run_log → ingest → validate.

## Tests

```bash
PYTHONPATH=scripts python3 scripts/pipeline_pack_test.py
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --check
PYTHONPATH=scripts python3 scripts/pipeline_dispatch_golden_test.py
PYTHONPATH=scripts python3 scripts/pipeline_smoke_test.py
PYTHONPATH=scripts python3 scripts/pipeline_runtime_test.py
PYTHONPATH=scripts python3 scripts/pipeline_registry_test.py
```

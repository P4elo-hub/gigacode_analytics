# Pipeline packs

One folder per pipeline. Compile collects every pack into `scripts/pipeline_schema.json`
and `scripts/generated/pipeline_registry.json`.

```
pipelines/<id>/
  graph.yaml       # nodes, edges, label, orchestrator
  dispatch.yaml    # invariants, rules (when / next / priority)
  status.yaml      # artifacts, collectors, stale, invariants, display
  registry.yaml    # step → subagent, gated, restart
  collectors.py    # optional domain collectors (COLLECTORS + INVARIANTS)
  predicates.py    # optional domain predicates
  validate.py      # extra_advice for pipeline_validate (optional, but needed
                   # for pack-specific rules — even without dispatch)
```

Edit the pack, then:

```bash
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --check
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --apply
```

**New pipeline (authoring):** [PIPELINE-PACK-AUTHORING.md](../scripts/PIPELINE-PACK-AUTHORING.md)
— `--init-pack <id>`, pack JSON schema, catalog contract, orchestrator template.

```bash
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --init-pack <id> [--template minimal|orchestrator-only|full-dispatch]
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --catalog
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --from-json pack.json
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --export-json <id>
```

Schema: `scripts/pipeline_pack_schema.json`. Fixture: `scripts/fixtures/pack_smoke/minimal/`.

Catalog (palette for authoring): `pipeline_compile.py --catalog`.
Apply a pack JSON from a frontend: `pipeline_compile.py --from-json pack.json`.

Runtime contract: `scripts/PIPELINE-RUNTIME.md`.
Status contract: `scripts/PIPELINE-STATUS.md`.
Predicate catalog: `scripts/PIPELINE-PREDICATES.md`.
Registry (step → subagent, gated, restart): `scripts/PIPELINE-REGISTRY.md`.
Compiled mapping is only `pipelines.<id>` in `pipeline_registry.json`.
Spec remains the reference pack (24+ golden cases).

`validate.py` — add when the pack has workflow rules beyond generic idle/fail/
divergence (spec: DECISIONS / challenge one-pass; calibration: orchestrator_only
sanity). Engine always calls `extra_advice` if the file exists, including when
`dispatch_supported` is false.

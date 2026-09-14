# Pipeline packs

One folder per pipeline. Compile collects every pack into `scripts/pipeline_schema.json`
and `scripts/generated/pipeline_registry.json`.

```
pipelines/<id>/
  graph.yaml       # nodes, edges, label, orchestrator
  dispatch.yaml    # invariants, rules (when / next / priority)
  status.yaml      # artifacts, collectors, stale
  registry.yaml    # step → subagent, gated, restart
  collectors.py    # optional domain collectors
  predicates.py    # optional domain predicates
  validate.py      # optional extra validate advice
```

Edit the pack, then:

```bash
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --check
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --apply
```

Catalog (palette for authoring): `pipeline_compile.py --catalog`.
Apply a pack JSON from a frontend: `pipeline_compile.py --from-json pack.json`.

Runtime contract: `scripts/PIPELINE-RUNTIME.md`.
Spec remains the reference pack (24+ golden cases).

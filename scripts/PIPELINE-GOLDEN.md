# Pipeline golden coverage (Phase 9)

Compile / pack YAML must not silently break routing. Every pack in
`pipelines/<id>/` is covered by a dispatch golden folder **or** an explicit
waiver. `spec-v2` is the active platform reference.

```
pipelines/<id>/  →  fixtures/dispatch_golden/<id>/cases.json
                 or fixtures/dispatch_golden/<id>/WAIVER.md
compile → isolated build_dispatch()
regression: compile + dispatch-golden (`coverage:packs`) + engine tests
```

Policy lives here; fixtures live in [fixtures/dispatch_golden/](fixtures/dispatch_golden/).

## Rule

| Pack | Required |
|------|----------|
| `dispatch_supported` (compiled rules or invariants) | `cases.json` with **≥ 1** case. Waiver is **not** allowed. |
| no-dispatch / `orchestrator_only` | `cases.json` **or** `WAIVER.md` (calibration-style: 1 case `orchestrator_only` is enough) |
| `spec-v2` | reference cases; waiver is **not** allowed even if dispatch is emptied; do not drop existing ids except a documented bugfix |

Orphan `fixtures/dispatch_golden/<id>/` with no matching `pipelines/<id>/` fails.

**Status golden** (`fixtures/status_golden/<id>/`) is **not** per-pack mandatory.
Keep it only for packs with complex status/collectors (currently `spec`).
Calibration does not need status golden — do not add one without a collector
contract reason.

## Waiver (`WAIVER.md`)

Only for packs with empty `rules` / `invariants`. Non-empty file, for example:

```markdown
# Waiver: <id> has no compiled dispatch
orchestrator_only — router contract is not applicable.
Covered by `pipeline_dispatch_golden_test.py` and delegate dry-run.
```

## Tests

```bash
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --check
PYTHONPATH=scripts python3 -m unittest discover scripts -p '*_test.py'
PYTHONPATH=scripts python3 scripts/pipeline_dispatch_golden_test.py
```

`pipeline_dispatch_golden_test.py` keeps aggregate `dispatch-golden N/N` and
`coverage:packs` (dynamic `discover_pipeline_ids()`).

## New pack

After `--init-pack <id> --template full-dispatch` add
`scripts/fixtures/dispatch_golden/<id>/cases.json` and `COVERAGE.md`.
No-dispatch templates: the same folder with `cases.json` **or** `WAIVER.md`.
Playbook: [PIPELINE-PACK-AUTHORING.md](PIPELINE-PACK-AUTHORING.md).

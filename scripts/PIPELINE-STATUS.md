# Pipeline status contract

`pipelines/<id>/status.yaml` describes **what to read** for a task snapshot.
`scripts/pipeline_status.py` **executes** that config. Pack-specific parsing
lives in `pipelines/<id>/collectors.py`, not in the engine.

```
status.yaml → populate_status() → fields for predicates → router → next step
```

## Files

| File | Role |
|------|------|
| `pipelines/<id>/status.yaml` | Artifacts, collectors, stale, invariants, display |
| `pipelines/<id>/collectors.py` | `COLLECTORS[id]` + optional `INVARIANTS` |
| `scripts/pipeline_status.py` | `load_status_spec`, `populate_status`, `build_status` |
| `scripts/feature_status.py` | Spec CLI (`/feature-status`) over the same engine |

CLI for spec remains `python3 scripts/feature_status.py <slug>`.

## status.yaml schema

```yaml
task_kind: slug
constants:                    # optional; display / collectors / domain predicates
  alignment_max_iterations: 3
  verdict_pass: PASS
core_predicates:              # optional; generic counters for the core catalog
  counters:
    - field: decisions_needs_answer
      gt: 0
      alias: field_gt           # legacy catalog name; dispatch uses domain when:
artifacts:
  spec:
    path: Feature-writing/{task_id}/{task_id}.md   # {task_id} and {slug}
    exists_as: has_spec         # bool field; default has_<id>
    lines_as: spec_lines        # optional int field
    missing_reason: ...         # reason_for(not_has_spec / file_missing_spec)
collectors:
  - id: spec_gaps               # must exist in COLLECTORS
    source: spec                # artifact id (compile-checked)
stale:
  - id: alignment
    when: artifact_older_than   # or artifact_newer_than
    left: alignment
    right: spec
alignment_stale:                # optional extra bool (same when/left/right)
  when: artifact_older_than
  left: alignment
  right: spec
  require_left: true
invariants:
  - id: needs-check-feature     # dispatch.yaml invariant id
    collector: needs_check_feature
orchestrator:
  write_cycle_step: write-feature
  ask_user_when: decisions_needs_answer
messages:
  ready: ...
  stopped: ...
display:                        # optional CLI table for feature_status
  heading: "Фича: {slug}"
  rows:
    - label: SPEC
      exists: has_spec
      suffix: "{spec_lines} строк"
```

Core predicates auto-register `not_has_<artifact>` / `has_<artifact>` /
`file_missing_<artifact>` from `artifacts`, plus `{field}_gt_{n}` from
`core_predicates.counters` (`pipeline_predicates.core_predicates_from_status`).
Missing-file reasons: artifact `missing_reason` (engine does not hardcode spec copy).
Full catalog: [PIPELINE-PREDICATES.md](PIPELINE-PREDICATES.md).

## Collectors

`populate_status` resolves artifact paths, sets `exists_as` / `lines_as`, then
calls each YAML collector:

```python
COLLECTORS = {
    "spec_gaps": collect_spec_gaps,  # (root, task_id, status, paths) -> None
}

INVARIANTS = {
    "needs-check-feature": needs_check_feature,  # -> (bool, reason)
}
```

`paths` is `{artifact_id: Path}` from this pack's YAML — do not hardcode
feature paths in collectors. Router invariants look up `INVARIANTS[id]`.

A new pipeline adds `status.yaml` + `collectors.py` in its pack folder.
Do not edit `pipeline_status.py` for domain fields.

## Engine API

```python
from pipeline_status import (
    load_status_spec,
    resolve_artifact_paths,
    collectors_for,
    populate_status,
    build_status,
)

populate_status(status, root, task_id, pipeline_id)  # mutates status
build_status(root, task_id, pipeline_id)             # populate + router
```

`build_status` defaults to spec `FeatureStatus`. Pass `status=` for another DTO;
the engine only uses `setattr` / `getattr`.

## Add a status pack

1. Create `pipelines/<id>/status.yaml` (artifacts + collectors + stale).
2. If you parse file contents, add `collectors.py` with `COLLECTORS`.
3. Point domain `when:` predicates at the fields you set.
4. `PYTHONPATH=scripts python3 scripts/pipeline_compile.py --check` then `--apply`.
5. Golden: `scripts/fixtures/status_golden/<id>/` (optional) and dispatch golden.

Spec reference pack: `pipelines/spec/status.yaml`.
Calibration may keep an empty `artifacts: {}` pack.

## Tests

```bash
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --check
python3 scripts/feature_status_test.py
PYTHONPATH=scripts python3 scripts/pipeline_dispatch_golden_test.py
PYTHONPATH=scripts python3 scripts/pipeline_smoke_test.py
```

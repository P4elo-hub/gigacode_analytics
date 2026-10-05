# Pipeline registry

Step → subagent, gated hooks, restart, and delegate modes live in each pack:

```
pipelines/<id>/registry.yaml
        ↓ compile
generated/pipeline_registry.json → pipelines.<id>
        ↓
registry_for(pipeline_id) → delegate / hooks / restart / validate
```

**Canon:** `registry.pipelines.<id>` only. Step ids are unique **inside** a pipeline.
The same name in spec and calibration is not a collision (scope = `pipeline_id`
in `.pipeline-active-task.json` and `--pipeline`).

Compiled `pipeline_registry.json` has **one** mapping source: `pipelines.<id>`.
There is no top-level `step_to_subagent` / `gated_subagents` / … copy of spec.
`load_pipeline_registry()` still has `nodes`, `dispatch`, `status`, `predicates`
at the root — those are not the step registry. Runtime mapping: `registry_for(id)`.

Python `from pipeline_common import STEP_TO_SUBAGENT` is a **spec-only import
shim** (`DeprecationWarning`). Do not add JSON top-level mapping back.

## registry.yaml

```yaml
step_to_subagent:
  find-context: context-researcher
orchestrator_owned:
  - write-feature          # no `task`; orchestrator runs the step
gated_subagents:
  - context-researcher     # PreToolUse requires active-task / delegate
restartable_steps:         # order = step_order after compile
  - find-context
  - write-feature
delegate_modes:
  write_feature_cycle:
    step: write-feature
    subagent: spec-writer
    persistent: true
```

| Field | Role |
|-------|------|
| `step_to_subagent` | Canonical mapping; keys must be graph node ids |
| `orchestrator_owned` | Steps with no subagent mapping (disjoint from mapped keys) |
| `gated_subagents` | Hook gate for **this** pipeline only (not a union of packs) |
| `restartable_steps` | Restart from this step; compile fills `step_order` |
| `delegate_modes` | Extra orchestrator modes (spec: `write_feature_cycle`) |

A composite cell (same agent, many params, no routing between them) is
`cycle:` on the **graph node**. The frontend draws that block; compile copies
it into `pipeline_schema.json`; `inner_cycle.py` walks it.

```yaml
cycle:
  persistent: true
  assemble: write_feature   # or concat
  param: block_id
  folder: Feature-writing/{slug}
  out: "{slug}.md"
  item_file: "{slug}.part-{param}.md"
  close: on_done            # engine default; cell finish = any graph node
  # calls:                  # optional static queue (frontend-drawn cells)
  #   - agent: spec-writer
  #     param: goal
```

Inner steps: `task` (agent+param) until artifacts exist, then `assemble`
(script, not a subagent). `close: on_done` stamps `position` on this node and
clears the active-task marker, then outer dispatch follows compiled edges.
write-feature is the first pack; omit `calls` and the catalog adapter fills
them at runtime. Another cell is another `cycle:` block.

## Add a pack

Prefer `--init-pack` / `--from-json` ([PIPELINE-PACK-AUTHORING.md](PIPELINE-PACK-AUTHORING.md)).
Or by hand:

1. `pipelines/<id>/registry.yaml` next to `graph.yaml`.
2. Map every delegated step; list orchestrator-owned steps separately.
3. Put hook-gated agents in `gated_subagents` (must exist under
   `.qwen/agents`, `.gigacode/agents`, or `.opencode/agents`).
4. `PYTHONPATH=scripts python3 scripts/pipeline_compile.py --check` then `--apply`.

Compile `--check` fails when a mapped/restartable/owned step is missing from
the graph, or a registry subagent is not in the agent catalog. Same step id
with **different** subagents across pipelines is a warning only.

## Runtime

```python
from pipeline_common import registry_for, subagent_for_step, pipeline_gated_subagents

registry_for("calibration")           # ≠ spec mapping
subagent_for_step("capture-review", "calibration")
pipeline_gated_subagents("calibration")  # not the spec set, not a union
```

Hooks resolve `pipeline_id` from `--pipeline` or active-task, then gate on
that pack.

## Restart

```bash
python3 scripts/pipeline_restart.py <slug> --from-step <step> [--pipeline spec|calibration] [--apply]
```

Default отсутствует: передавай явный `--pipeline spec-v2`. Marker and rollback paths follow the pack:

| Pipeline | Marker | Rollback |
|----------|--------|----------|
| spec | `Feature-writing/<slug>/.pipeline-restart.json` | Feature-writing + Feature-context (SPEC file itself is not git-reverted) |
| calibration | `Calibration/<slug>/.pipeline-restart.json` | `Calibration/<slug>/runs/<current_run>/` only |

Calibration never deletes Feature-writing. `events.jsonl` / `run-log` stay;
only `agent-logs/.../telemetry-analysis.md` of the current agent-run is
removed when restarting from `analyze-telemetry`. Skill patches from
`apply-calibration` are not git-reverted.

Viewer restart uses `restartable_steps` of the **active** pipeline tab and
passes `pipeline` to `/api/restart-plan` and `POST /api/restart`.

## Tests

Registry checks live in the active engine unittest suite:

```bash
PYTHONPATH=scripts python3 -m unittest discover scripts -p '*_test.py'
```

See [PIPELINE-COMPILE.md](PIPELINE-COMPILE.md) § Tests, [PIPELINE-RUNTIME.md](PIPELINE-RUNTIME.md).

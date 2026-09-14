# Pipeline runtime contract

Generic loop for any pack that has an orchestrator + agents/skills.
Not spec-orchestrator markdown — the same four calls, `--pipeline <id>`.

```
dispatch → task (or ask_user / ready / stopped) → append_run_log → validate
```

```bash
python3 scripts/pipeline_dispatch.py <task_id> --pipeline <id> --json
python3 scripts/pipeline_delegate.py <task_id> --cli qwen --pipeline <id>
# if action=task → task on task.subagent_type
python3 scripts/append_run_log.py --slug <task_id> --step <step> --subagent <agent> --result ok --pipeline <id>
python3 scripts/pipeline_validate.py <task_id> --pipeline <id>
```

Hooks (`pipeline_before_subagent`, `pipeline_after_subagent`) resolve
`pipeline_id` from `--pipeline` or `.pipeline-active-task.json`, then read
**that** pack's registry (`registry_for(pipeline_id)`). Gated subagents are
per pipeline, not a union of all packs.

| Script | Role |
|--------|------|
| `pipeline_dispatch.py` | Next step from pack status + dispatch rules |
| `pipeline_delegate.py` | Graph edge check + active-task + task envelope |
| `append_run_log.py` | One run-log line (`--pipeline`) |
| `ingest_session_telemetry.py` | Session ingest (`--pipeline`) |
| `pipeline_validate.py` | Generic idle/fail/divergence + pack `validate.py` (`extra_advice`) |

Registry: [PIPELINE-REGISTRY.md](PIPELINE-REGISTRY.md). Restart:
`pipeline_restart.py --pipeline <id>` — spec rolls back Feature-writing;
calibration rolls back `Calibration/<slug>/runs/<current>/` only.

New scenario: add `pipelines/<id>/` + agents/skills, then
`pipeline_compile.py --apply`. No engine Python for topology or `when:` names
(predicate catalog: [PIPELINE-PREDICATES.md](PIPELINE-PREDICATES.md)).

## Validate (engine vs pack)

`pipeline_validate.py` is generic. Pack rules live in `pipelines/<id>/validate.py`
as `extra_advice(...)`. **Calibration has no `validate.py`.**

Engine still hardcodes spec-flavored bits (Phase 7 target):

| Location | What | Spec-specific? |
|----------|------|----------------|
| `validate_slug` early return | no dispatch → `dispatch-not-configured` and **return** (pack `validate.py` never runs) | yes — calibration cannot add extra_advice today |
| `pipeline-ready` copy | title «Spec готов», «калибровка — только по запросу» | yes |
| `write-feature-cycle-idle` | `orchestrator_mode == write_feature_cycle`, spec-writer/assemble | yes (`delegate_modes`) |
| `stopped-while-must-continue` | idle while `must_continue` | generic |
| `last-step-fail` | last run-log fail/retry | generic |
| divergence items | graph / subagent mismatch | uses `pipeline_id` |
| `pipelines/spec/validate.py` | pending-apply vs ask_user, needs-answer, check-feature loop, challenge one-pass | spec-only |
| `pipelines/calibration/validate.py` | missing | — |

Phase 7: call pack `extra_advice` even without dispatch; move write-cycle / ready copy into pack or `delegate_modes`.

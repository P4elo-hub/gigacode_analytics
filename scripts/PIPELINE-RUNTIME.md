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
`pipeline_id` from `--pipeline` or `.pipeline-active-task.json`.

| Script | Role |
|--------|------|
| `pipeline_dispatch.py` | Next step from pack status + dispatch rules |
| `pipeline_delegate.py` | Graph edge check + active-task + task envelope |
| `append_run_log.py` | One run-log line (`--pipeline`) |
| `ingest_session_telemetry.py` | Session ingest (`--pipeline`) |
| `pipeline_validate.py` | Generic idle/fail/divergence + pack `validate.py` |

New scenario: add `pipelines/<id>/` + agents/skills, then
`pipeline_compile.py --apply`. No engine Python for topology or `when:` names
(predicate catalog: [PIPELINE-PREDICATES.md](PIPELINE-PREDICATES.md)).

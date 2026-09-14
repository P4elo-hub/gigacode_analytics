# Pipeline runtime contract

Generic loop for any pack that has an orchestrator + agents/skills.
Not spec-orchestrator markdown — the same calls, `--pipeline <id>`.

Orchestrator is **delegate-first**. `pipeline_dispatch.py` is read-only (inside
delegate, or a human CLI). Do not call dispatch separately.

```
delegate (--pipeline <id>; внутри: dispatch)
  → action: task | ask_user | write_feature_cycle | orchestrator_only | ready | stopped
  → append_run_log → ingest → validate
```

```bash
python3 scripts/pipeline_delegate.py <task_id> --cli qwen --pipeline <id>
# if action=task → task on task.subagent_type
python3 scripts/append_run_log.py --slug <task_id> --step <step> --subagent <agent> --result ok --pipeline <id>
python3 scripts/ingest_session_telemetry.py <task_id> --cli qwen --pipeline <id>
python3 scripts/pipeline_validate.py <task_id> --pipeline <id>
```

Read-only next-step snapshot (не оркестратор):

```bash
python3 scripts/pipeline_dispatch.py <task_id> --pipeline <id> --json
```

Orchestrator agents share this block (rule `pipeline-enforcement`, heading
**Runtime loop (mandatory)**). `runtime_contract(pipeline_id)` in
`pipeline_runtime.py` returns the same steps for `--catalog`.

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
`pipeline_compile.py --apply`. Scaffold: `--init-pack` /
[PIPELINE-PACK-AUTHORING.md](PIPELINE-PACK-AUTHORING.md). No engine Python for
topology or `when:` names (predicate catalog: [PIPELINE-PREDICATES.md](PIPELINE-PREDICATES.md)).

## Validate (engine vs pack)

`pipeline_validate.py` is generic. Pack rules live in `pipelines/<id>/validate.py`
as `extra_advice(...)`. **Dispatch is optional:** when `dispatch_supported` is
false, the engine still runs last-fail / idle (if `must_continue`) / divergence
and **always** calls pack `extra_advice` if the file exists.

Ready / write-cycle copy comes from pack config, not engine literals:

| Location | What | Source |
|----------|------|--------|
| `pipeline-ready` title/detail/fix | terminal ready | `status.yaml` `messages.ready_title` / `ready_detail` / `ready_fix` |
| `write-feature-cycle-idle` | idle in write cycle | `registry.yaml` `delegate_modes.write_feature_cycle` (step + subagent) |
| `dispatch-not-configured` | no router **and** no pack `validate.py` | engine fallback (ok) |
| `stopped-while-must-continue` | idle while `must_continue` | generic: delegate → task on next_subagent |
| `last-step-fail` | last run-log fail/retry | generic |
| divergence items | graph / subagent mismatch | uses `pipeline_id`; empty when no dispatch |
| `pipelines/spec/validate.py` | pending-apply vs ask_user, needs-answer, check-feature loop, challenge one-pass | spec-only |
| `pipelines/calibration/validate.py` | `cal-orchestrator-only` + graph orchestrator node | pack-only when no dispatch |

Phase 7 (done): pack-first validate; shared orchestrator runtime loop.
Phase 10–11: routing-state overlay — [PIPELINE-ROUTING-STATE.md](PIPELINE-ROUTING-STATE.md).
Smoke does not add `dispatch:routing-poc` (golden + compile cover the pack).

## Tests

```bash
PYTHONPATH=scripts python3 scripts/pipeline_runtime_test.py
PYTHONPATH=scripts python3 scripts/pipeline_registry_test.py
PYTHONPATH=scripts python3 scripts/pipeline_smoke_test.py
PYTHONPATH=scripts python3 scripts/pipeline_dispatch_golden_test.py
PYTHONPATH=scripts python3 scripts/pipeline_routing_state_test.py
```

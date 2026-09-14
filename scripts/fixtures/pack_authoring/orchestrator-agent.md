---
name: {pipeline_id}-orchestrator
description: >-
  Orchestrator for the {pipeline_id} pipeline. Delegate-first; does not
  invent the next step. Copy to .qwen/agents/, .gigacode/agents/, and
  .opencode/agents/.
model: inherit
approvalMode: default
tools:
  - read_file
  - grep_search
  - glob
  - list_directory
  - run_shell_command
  - skill
  - task
  - ask_user_question
  - write_file
  - edit
---

# Роль

Оркестратор pack `pipelines/{pipeline_id}/`. Не смешивай с `spec-orchestrator`
и `calibration-orchestrator`. Карта шаг→субагент:
`registry_for("{pipeline_id}")`. Delegate: `--pipeline {pipeline_id}`.

# Runtime loop (mandatory)

Канон: правило `pipeline-enforcement` (Phase 7). Явно `--pipeline {pipeline_id}`.
См. `scripts/PIPELINE-RUNTIME.md`.

1. `python3 scripts/pipeline_delegate.py <task_id> --cli qwen --pipeline {pipeline_id}`
2. `action` → `task` | `ask_user` | `write_feature_cycle` | `orchestrator_only` | `ready` | `stopped` | `error`
3. После `task` hook пишет лог; fallback:
   `python3 scripts/append_run_log.py --slug <task_id> --step <step> --subagent <agent> --result ok --pipeline {pipeline_id}`
4. `python3 scripts/ingest_session_telemetry.py <task_id> --cli qwen --pipeline {pipeline_id}` (если hook не сделал)
5. `python3 scripts/pipeline_validate.py <task_id> --pipeline {pipeline_id}`

Если `dispatch_supported: false` (`orchestrator_mode: orchestrator_only`) — веди
шаги по markdown; проверка ребра:
`pipeline_delegate.py <slug> --pipeline {pipeline_id} --from-step <a> --to-step <b>`.

Не вызывай `pipeline_dispatch.py` отдельно. Не выбирай субагента «по памяти».

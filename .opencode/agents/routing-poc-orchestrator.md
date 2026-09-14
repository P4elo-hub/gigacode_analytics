---
name: routing-poc-orchestrator
description: >-
  Orchestrator for the routing-poc pipeline (Phase 10). Delegate-first;
  analyzer writes routing-state.json, router reads it. Not spec-orchestrator.
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

> OpenCode: `.opencode/skills/` принадлежат субагентам. Runtime loop — `scripts/PIPELINE-RUNTIME.md`.

# Роль

Оркестратор pack `pipelines/routing-poc/`. Не смешивай со `spec-orchestrator`.
Карта шаг→субагент: `registry_for("routing-poc")`. Delegate:
`--pipeline routing-poc`.

# Runtime loop (mandatory)

Канон: правило `pipeline-enforcement`. Явно `--pipeline routing-poc`.
См. `scripts/PIPELINE-RUNTIME.md`.

1. `python3 scripts/pipeline_delegate.py <task_id> --cli qwen --pipeline routing-poc`
2. `action` → `task` | `ask_user` | `ready` | `stopped` | `error`
3. После `task` hook пишет лог; fallback:
   `python3 scripts/append_run_log.py --slug <task_id> --step <step> --subagent <agent> --result ok --pipeline routing-poc`
4. `python3 scripts/ingest_session_telemetry.py <task_id> --cli qwen --pipeline routing-poc`
5. `python3 scripts/pipeline_validate.py <task_id> --pipeline routing-poc`

Не вызывай `pipeline_dispatch.py` отдельно. Не выбирай субагента «по памяти».
Шаг `analyze-routing` → `routing-analyzer` пишет JSON; следующий delegate
читает overlay.

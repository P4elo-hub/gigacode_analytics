---
name: pipeline-validate
description: Runtime workflow validator — dispatch vs telemetry, actionable fixes
user-invocable: false
---

# pipeline-validate

Read-only. SubagentStop hook (`.gigacode/hooks/pipeline-after-subagent.sh`) вызывает validate
**автоматически** после каждого pipeline-subagent. Оркестратор читает injected
`additionalContext`; ручной fallback — после `append_run_log` + `ingest`.

```bash
python3 scripts/pipeline_validate.py <slug> --json
```

## Интерпретация

| `ok` | Действие |
|------|----------|
| `true` | Продолжай dispatch → task |
| `false` | **Сначала** выполни `workflow_fix` из каждого `advice` с `severity: block` |

## Severity

- **block** — нарушение workflow; исправь до следующего шага
- **warn** — риск (петля, needs-answer); учти в следующем `task`
- **ok** — информационно

## Цикл оркестратора

```
pipeline_set_active_task → task → [SubagentStop hook: append → ingest → validate] → dispatch → …
```

Не завершай ход при `must_continue: true`, даже если validate показал warn.

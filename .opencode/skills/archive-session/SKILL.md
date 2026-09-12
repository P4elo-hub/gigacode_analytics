---
name: archive-session
description: >-
  Ingest CLI session jsonl into agent-logs/<slug>/runs/<run-id>/: events.jsonl,
  metrics.json, anomalies.md. Use after a pipeline step or human review.
user-invocable: false
---

# archive-session

Сохранить телеметрию текущей CLI-сессии в `AGENT_LOGS/<slug>/`.

Субагенты и скиллы пайплайна **не** пишут логи сами — ingest читает:

- **Qwen / OpenCode** — jsonl в `~/.qwen/` / `~/.opencode/`
- **OpenCode** — SQLite `~/.local/share/opencode/opencode.db` (дерево session + part)

## Когда вызывать

- оркестратор после каждого pipeline step;
- вручную `/archive-session <slug>` после review;
- перед `/analyze-telemetry`;
- `--new-run` — новый benchmark (run-002 после калибровки).

## Команда

```bash
python3 scripts/ingest_session_telemetry.py <slug> \
  [--session <uuid>] \
  [--cli qwen|opencode|opencode] \
  [--session-directory <path>] \
  [--run-id auto] \
  [--new-run] \
  [--copy-raw]
```

Без `--session` — последняя сессия workspace. OpenCode: `--session-directory`
если `session.directory` в БД отличается от текущего cwd (legacy workspace).

## Выход

| Файл | Токен |
|------|-------|
| `agent-logs/<slug>/manifest.json` | `AGENT_MANIFEST` |
| `agent-logs/<slug>/runs/<run-id>/events.jsonl` | `AGENT_EVENTS` |
| `agent-logs/<slug>/runs/<run-id>/metrics.json` | `AGENT_METRICS` |
| `agent-logs/<slug>/runs/<run-id>/anomalies.md` | `AGENT_ANOMALIES` |

## Правила

- Не править `events.jsonl` вручную — только через ingest.
- `--copy-raw` — только если нужен аудит сырого jsonl (тяжёлые файлы).
- Один slug = одна папка, как `Feature-writing/<slug>/`.

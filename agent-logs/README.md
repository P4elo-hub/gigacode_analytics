# agent-logs

Телеметрия CLI-сессий (Qwen / GigaCode / OpenCode) по slug фичи. **Канонический локальный архив** — всё нужное для pipeline viewer, timings и аудита должно жить здесь, а не только в `~/.qwen/`.

## Структура

```
agent-logs/
  <slug>/
    manifest.json              ← runs, sessions, last_ingest, archived_sessions
    subagent-passes.jsonl      ← все проходы subagent (timing, call_id, raw paths)
    validation.json
    runs/
      run-NNN/
        events.jsonl           ← нормализованные события (tool/skill/spawn)
        run-log.jsonl          ← шаги оркестратора (+ started_at, duration_sec при sync)
        subagent-passes.jsonl  ← снимок проходов на момент run
        metrics.json
        anomalies.md
        raw/                   ← копия Qwen chat + subagent jsonl/meta (при ingest/sync)
          main-<session>.jsonl
          subagents/<session>/
            agent-*.jsonl
            agent-*.meta.json
```

## Сбор и синхронизация

```bash
# Ingest текущей сессии + raw + subagent-passes
python3 scripts/ingest_session_telemetry.py <slug> --cli qwen [--session UUID] --copy-raw

# Полный sync: ingest если stale + backfill run-log + архив всех linked sessions
python3 scripts/sync_pipeline_session.py <slug> --cli qwen

# Только архив subagent meta → agent-logs (без ingest)
python3 scripts/archive_subagent_passes.py <slug>
```

Hook `SubagentStop` и viewer вызывают `sync_pipeline_session` автоматически.

## subagent-passes.jsonl

Одна строка = один вызов subagent. Поля: `call_id`, `session_id`, `step`, `subagent`, `started_at`, `ended_at`, `duration_sec`, `description`, `raw_meta_relpath`.

Источник для вкладки **«Время»** в pipeline viewer — **только agent-logs**, не `~/.qwen`.

Папка в `.gitignore` (кроме этого README) — логи локальные и могут быть большими.

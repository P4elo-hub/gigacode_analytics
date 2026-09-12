---
name: analyze-telemetry
description: >-
  Read agent-logs metrics and run-log for a slug; explain anomalies, correlate
  with pipeline steps, suggest skill/process fixes. Use after archive-session.
user-invocable: false
---

# analyze-telemetry

Анализ сохранённой телеметрии. **Read-only** для `agent-logs/` и
`Feature-writing/` (baseline spec при наличии).

## Когда вызывать

- после `/archive-session`;
- перед proposal калибровки скиллов;
- сравнение run-001 vs run-002 после benchmark.

## Вход

1. `python3 scripts/ingest_session_telemetry.py` уже отработал (или `--json` из manifest).
2. Прочитать:
   - `AGENT_METRICS` (`metrics.json`)
   - `AGENT_ANOMALIES` (`anomalies.md`)
   - `runs/<run-id>/run-log.jsonl` — шаги оркестратора
   - опционально `Feature-writing/<slug>/<slug>.baseline.md` если есть

## Шаги

1. Определи `current_run` из `AGENT_MANIFEST`.
2. Перечисли anomalies из `metrics.json` → `anomalies.md` (не выдумывай).
3. Сопоставь с `run-log.jsonl`: какой step предшествовал skill.repeat.
4. Для каждой major/warn anomaly — одна гипотеза root cause:
   - router-skill (`.opencode/skills/*-analysis`)
   - kit template/gate (`kb-writing-kits/`)
   - orchestrator retry (check-part)
   - missing context (`CONTEXT_DOC`)
5. Выход: `agent-logs/<slug>/runs/<run-id>/telemetry-analysis.md`

Формат finding:

```markdown
## TA-01 — <anomaly id>
- signal: skill.repeat requirements-analysis ×57
- correlated_steps: write-feature / goal, constraints, nfr
- likely_cause: …
- proposal_target: `.opencode/skills/requirements-analysis/SKILL.md`
- proposal_type: L1 hint | L2 gate | L3 template
```

## Запреты

- Не патчить скиллы — только `telemetry-analysis.md`.
- Не читать `~/.qwen/` напрямую — только `agent-logs/`.
- Не выдумывать counts — только из `metrics.json`.

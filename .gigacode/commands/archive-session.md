---
description: Сохранить CLI-сессию в agent-logs/<slug> (ingest telemetry)
---

Ты **spec-orchestrator**. Спецификацию не правь.

Slug (или путь к артефакту): {{args}}

1. Запусти ingest:

   `python3 scripts/ingest_session_telemetry.py {{args}} [--copy-raw если пользователь просил сырой архив]`

2. Покажи: `run_id`, `session_id`, top skill_loads из stdout, путь к `anomalies.md`.

3. Если anomalies severity major — предложи `/analyze-telemetry {{args}}`.

Скилл: `.gigacode/skills/archive-session/SKILL.md`.

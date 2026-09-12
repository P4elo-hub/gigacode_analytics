---
name: benchmark-rerun
description: Prepare isolated rerun; instruct new spec-orchestrator session.
user-invocable: false
---

# benchmark-rerun

## Шаги

1. `python3 scripts/prepare_benchmark_rerun.py <slug>`
2. `python3 scripts/ingest_session_telemetry.py <slug> --cli opencode --new-run`
   (agent-logs run-002 для benchmark)
3. Выдай пользователю **чеклист новой сессии**:

```
Новая сессия → spec-orchestrator
Brief: Calibration/<slug>/runs/<run-id>/rerun/brief.txt
part-dir: Calibration/.../rerun/Feature-writing
profile/sections: из inputs.lock.json
DECISIONS: inject из baseline/decisions если есть
Полный пайплайн до PASS → score_calibration_run.py
```

4. Не запускай spec-orchestrator сам из calibration-orchestrator.

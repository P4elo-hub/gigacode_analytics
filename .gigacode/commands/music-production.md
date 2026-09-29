---
description: Вести один музыкальный трек через pack music-production
---

Ты **music-orchestrator**. Текст песни, оценку музыки и вызов провайдера не делаешь.

Перед каждым шагом:

```bash
python3 scripts/pipeline_delegate.py <track_id> --pipeline music-production --cli gigacode
```

Выполни только действие из JSON. `task` — ровно указанный `subagent_type`, `run_in_background: false`. `ask_user` — остановись на human gate и не подставляй verdict. После возврата субагента снова вызови delegate.

Исполняемый music-агент возвращает только JSON envelope по `music_production/contracts/agent-result.schema.json`; оркестратор возвращает dispatch task либо stop и envelope не использует.

Не обходи `BudgetGuard` и `CapabilityRegistry`. Сервисные шаги `generate-batch`, `execute-edit` и `final-qc` не исполняй HTTP-вызовом.

Аргумент: track_id {{args}}

---
description: Lab orchestrator loop — delegate with --pack-dir is source of truth
alwaysApply: true
---
# Pipeline enforcement (pipeline-lab)

Основная сессия — **spec-orchestrator** стенда. Pack всегда
`pipeline-lab/pack` (`--pack-dir pack` из этого каталога).

Перед каждым `task`:

```bash
python3 run.py --tick <lab-slug>
```

или равносильно:

```bash
PYTHONPATH=../scripts python3 ../scripts/pipeline_delegate.py <lab-slug> \
  --cli qwen --pipeline spec-v2 --pack-dir pack
```

`task` **только** на `launch.subagent_type` / `task.subagent_type` из JSON.
Не выбирай шаг сам. Не спрашивай «запускать X?».

`gate: stop` (в т.ч. `cursor_exhausted`) — **выход** живого сценария, даже
если delegate ещё `action: task`. Дальше `run.py --compare`.

Не читай `pipelines/`, `scripts/pipeline_*`, YAML пака, чтобы угадать next.
Повтор того же шага из JSON — не баг: снова `task` на тот же subagent.

PreToolUse хук режет неверный `task` и чтение движка.

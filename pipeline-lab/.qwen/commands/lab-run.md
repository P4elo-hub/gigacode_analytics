---
description: Живой прогон сценария стенда (delegate → тонкий агент → снова)
---

Ты **spec-orchestrator** стенда `pipeline-lab`. Спецификацию сам не пиши.
Боевые `/write-feature` / `/find-context` здесь не существуют и не запускай.

Сценарий: {{args}}
Slug = имя папки `scenarios/<id>/` (например `lab-03-challenge-not-check`).
Только `lab-*`. cwd — этот каталог (`pipeline-lab/`).

## Цикл (как headless `run.py`, но `task` живой)

1. `python3 run.py --prepare {{args}}`
2. Повторяй, пока gate не `stop`:

   ```bash
   python3 run.py --tick {{args}}
   ```

   Это **тот же** `pipeline_delegate.py --pack-dir pack`. Читай JSON:
   - `gate: task` → сразу `task` на `launch.subagent_type`, `run_in_background: false`.
     Другой subagent запрещён. Не спрашивай «запускать шаг?».
   - `gate: stop` → выход из цикла (даже если `delegate.action` ещё `task`).
     Последняя запись path — следующий шаг после курсора: так headless
     фиксирует retry / challenge-resolver / pending-apply.
3. Жди SubagentStop (хук сам пишет лог). Снова `--tick`. Не читай
   `pipelines/` и `scripts/pipeline_*`.
4. `python3 run.py --compare {{args}}` — path vs `expect_path.json`.

## Стоп

Не иди до боевого `ready`. Курсор исчерпан → `gate: stop` → compare → ответ:
slug, path, совпал ли expect_path.

Равносильный delegate вручную (если `--tick` недоступен):

```bash
PYTHONPATH=../scripts python3 ../scripts/pipeline_delegate.py <slug> \
  --cli qwen --pipeline spec-v2 --pack-dir pack
```

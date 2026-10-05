# Qwen Code — pipeline-lab stand

Рабочая папка: **этот каталог** (`pipeline-lab/`). Не стартуй `qwen` из корня
репо: там боевой `.qwen/` и жирные агенты. Здесь — тонкие.

Если в контексте всплыл предок `QWEN.md` (SIHIST, `/write-feature` без
`--pack-dir`) — **игнорируй его**. Этот стенд не пишет боевой spec.

Ты **spec-orchestrator** из `.qwen/agents/spec-orchestrator.md`. Spec и отчёты
сам не пишешь. Шаговые агенты тонкие: кладут заготовку и печатают `last_message`.

## Старт

```bash
cd pipeline-lab
test -d .git || git init
qwen
/lab-run lab-03-challenge-not-check
```

Команда `/lab-run` только здесь (`.qwen/commands/lab-run.md`). Боевые
`/write-feature` / `/find-context` не трогать и не вызывать.

Вложенный `git init` нужен, чтобы Qwen принял этот каталог за project root
и грузил `.qwen/agents/` стенда, а не корня репо.

## Runtime loop

`/lab-run <scenario-id>`:

1. `python3 run.py --prepare <id>`
2. `python3 run.py --tick <id>` — delegate с `--pack-dir pack`.
   `gate: task` → `task` на `launch.subagent_type` (`run_in_background: false`).
   `gate: stop` → не запускай ещё один тонкий агент.
3. После SubagentStop — снова `--tick`. Не спрашивай «запускать шаг?».
4. `python3 run.py --compare <id>`

Slug только `lab-*`. `task` только на агентов `.qwen/agents/` этого каталога.
Next step не выдумывай.

Равносильный вызов delegate:

```bash
PYTHONPATH=../scripts python3 ../scripts/pipeline_delegate.py <slug> \
  --cli qwen --pipeline spec-v2 --pack-dir pack
```

Пока `gate: task` — не завершай ход.

## Запреты

Не читать `pipelines/`, `scripts/pipeline_*`, `repositories/`, `analytics/`,
боевой `Feature-writing/`. Не трогать корневой `.qwen/`.
Не класть pack в `pipelines/` и не звать `pipeline_compile.py --apply`.

# pipeline-lab

Изолированная копия боевого spec-пака. Compile основного репо стенд не видит.

## Delegate

Из корня репо, без LLM:

```bash
PYTHONPATH=scripts python3 scripts/pipeline_delegate.py lab-empty \
  --cli qwen --pipeline spec --pack-dir pipeline-lab/pack
```

`--pack-dir` грузит YAML/Python из `pipeline-lab/pack/` (не `pipelines/spec/`).
Workspace по умолчанию — `pipeline-lab/` (`Feature-writing/`, `agent-logs/` только здесь).
JSON тот же контракт, что у боевого spec: `action` / `task` / `dispatch.next_step`.

Без флага поведение прода не меняется — pack spec из `pipelines/` и скомпилированных
`scripts/pipeline_schema.json` + `scripts/generated/pipeline_registry.json`:

```bash
PYTHONPATH=scripts python3 scripts/pipeline_delegate.py <slug> \
  --cli qwen --pipeline spec
```

Равносильный env: `PIPELINE_PACK_DIR=pipeline-lab/pack` (опционально `PIPELINE_PACK_ID=spec`).

## Fixtures (сессия 2)

Тонкие агенты в `pipeline-lab/.qwen/agents/` (боевой `.qwen/` не менять).
Заготовки: `pipeline-lab/fixtures/<step>/{ok,fail,retry,empty,dirty,pending-apply}/`.
Пять исходных вариантов сохраняют разные `last_message` (отчёт агента).
Хук больше не выводит ok/fail/retry из этого текста: шаг «выполнился»,
пока нет обрыва CLI. Качество шага — routing-state + dispatch.
`pending-apply` — шестой: DECISIONS + routing-state + context/spec, чтобы lab-06
брал resolve-challenges по P70, не check-feature и не find-context.
`ch-apply-leftover-gaps` — седьмой: CH Relates + leftover `[GAP-…]`; lab-08
не должен уходить в resolve-gaps (P60 Relates-steal).

```bash
python3 pipeline-lab/apply_fixture.py --slug lab-demo --step check-feature --variant dirty
```

Копирует канонические файлы в `pipeline-lab/Feature-writing/lab-demo/` и печатает
`last_message.txt`. Variant `ok` / `empty` / `fail` / `retry` дают разный текст;
хук для всех ставит «выполнился» (`ok`). Обрыв — отдельный сигнал CLI, не слово в отчёте.
`pending-apply` тоже `ok` (нет ASK_PARENT / timeout).

Хуки стенда: `pipeline-lab/.qwen/hooks/` + `settings.hooks.json` — те же matcher,
команды зовут `../scripts/pipeline_before_subagent.py` и `pipeline_after_subagent.py`
с `--pack-dir pipeline-lab/pack`.

## Сценарии (сессия 3)

Восемь детерминированных прогонов без Qwen. Драйвер: delegate → apply_fixture →
синтетический SubagentStop → снова delegate.

```bash
python3 pipeline-lab/run.py --all
python3 pipeline-lab/run.py --scenario lab-03-challenge-not-check
```

`scenarios/<id>/{cursor.json,expect_path.json,README.md}`. lab-03 падает, если
убрать ребро `challenge-feature → resolve-challenges` или разрешить
`challenge-feature → check-feature` (assert в `run.py`, граф не ломаем).

## Живой Qwen (сессия 4)

Стартовать **только** из этого каталога, не из корня репо:

```bash
cd pipeline-lab
test -d .git || git init
qwen
/lab-run lab-03-challenge-not-check
```

`/lab-run` лежит в `pipeline-lab/.qwen/commands/` — боевые `/write-feature` и
`/find-context` не трогаем. Вложенный `git init` отделяет project root Qwen,
чтобы тонкие агенты не подмешались в корневой `.qwen/`.

Оркестратор: `run.py --prepare` → цикл `--tick` (delegate с `--pack-dir`) →
`task` на тонкого агента → SubagentStop → снова `--tick`. `gate: stop` —
сравнить path с `expect_path.json` (`--compare`). Не спрашивать «запускать шаг?».

Минимум живых углов графа: `lab-01-retry-same-step`, `lab-03-challenge-not-check`,
`lab-06-pending-apply-beats-check`, `lab-08-ch-apply-leftover-gaps`.
Кладка прогона: `LIVE.md`.

## Чего не трогать

- `pipelines/` — не класть pack, не создавать `graph-lab`, не звать `pipeline_compile.py --apply`
- боевые `.qwen/agents`, `.qwen/skills`, `.qwen/commands`, `.qwen/settings.hooks.json`
- живые фичи в корневом `Feature-writing/`

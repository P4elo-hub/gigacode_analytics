# Стенд оркестрации (четыре сессии)

Мини-проект, который копирует **боевую коробку** spec: yaml-граф, dispatch,
оркестратор, хуки. Шаговые агенты тонкие: не пишут spec и не ходят в
`repositories/`, а кладут заранее заготовленные файлы и печатают заранее
заготовленный `last_message`.

Цель: после правки роутера/графа/хуков прогнать углы **без** живого
`bph-coupons-dividends-monthly-summary` и без настоящих `spec-writer` /
`spec-reviewer`.

Как пользоваться: новый чат → вставить **целиком** блок «Промпт сессии N»
ниже. Сессии идут по порядку. Не начинать N+1, пока N не закрыта по критерию.

## Общие запреты (все сессии)

- Не класть pack в `pipelines/`. Compile основного репо стенд не видит.
- Не менять боевые `.qwen/agents/*.md`, `.qwen/skills/**`, `.qwen/commands/**`.
- Не дописывать `lab-*` в основной `.qwen/settings.hooks.json` SubagentStop.
- Не трогать живые фичи в `Feature-writing/bph-*` и не гонять `/write-feature` по БПХ.
- Не упрощать граф до `scan/fix`. Узлы, рёбра, `when:`, агенты шагов — как у spec.
- Оркестратор не выбирает next step. Только `pipeline_delegate` JSON → `task.subagent_type`.
- Какой файл/ответ отдать на этом тике, задаёт **сценарий**, не LLM шага.

Рабочая папка стенда: `pipeline-lab/` в корне репо.

---

## Сессия 1 — yaml-коробка как в проде, без Qwen

### Промпт сессии 1

```
Контекст: репо gigacode_analytics. План: pipeline-lab/SESSIONS.md (прочитай целиком).

Задача только сессии 1: мини-pack — полная копия боевого spec-пайплайна, изолированно.

Сделай:
1. Скопируй pipelines/spec/{graph,dispatch,status,registry,routing_conditions}.yaml
   и pipelines/spec/{collectors,predicates,validate}.py (если есть) в
   pipeline-lab/pack/. Не вызывай pipeline_compile.py --apply. Не создавай
   pipelines/graph-lab и не добавляй id в scripts/generated/.
2. Чтобы delegate/хуки видели этот pack, добавь минимальный runtime-вход:
   --pack-dir pipeline-lab/pack (или равносильный env) у pipeline_delegate /
   загрузки schema+registry. Без этого флага поведение прода не меняется.
   Не вшивай стенд в discover_pipeline_ids() и не требуй lab-агентов в
   каталоге .qwen/agents основного репо.
3. Workspace прогонов: pipeline-lab/ как корень (Feature-writing/, agent-logs/
   только здесь). Боевой Feature-writing/ не использовать.
4. Смоук без LLM: pipeline_delegate.py <lab-slug> --cli qwen --pipeline spec
   --pack-dir pipeline-lab/pack на пустом lab-slug. JSON должен быть того же
   контракта, что боевой spec (action/task/next_step).
5. Короткий README в pipeline-lab/: как звать delegate с --pack-dir, чего не трогать.

Не делать: агентов, скиллов, фикстур сценариев, правок spec yaml в pipelines/spec/.

Критерий готовности:
- python3 scripts/pipeline_compile.py --check проходит как до правки (стенд не в drift).
- Delegate с --pack-dir отвечает JSON; без флага — как раньше, pack spec из pipelines/.
- В git нет нового каталога под pipelines/.
```

---

## Сессия 2 — тонкие агенты и библиотека заготовок

### Промпт сессии 2

```
Контекст: репо gigacode_analytics. План: pipeline-lab/SESSIONS.md.
Сессия 1 уже сделала pipeline-lab/pack/ и --pack-dir. Не пересобирай pack
и не клади его в pipelines/.

Задача только сессии 2: тонкие копии шаговых агентов + библиотека файлов/ответов.

Сделай:
1. Каталог агентов стенда: pipeline-lab/.qwen/agents/ — те же имена, что в
   pipelines/spec/registry.yaml: spec-orchestrator, context-researcher,
   spec-writer, routing-analyzer, spec-reviewer, gap-resolver, spec-challenger,
   challenge-resolver, code-auditor, alignment-resolver.
   Боевой .qwen/agents/ не менять.
2. Оркестратор: тот же runtime loop, что в .qwen/agents/spec-orchestrator.md
   / QWEN.md, но всегда:
   --pack-dir <repo>/pipeline-lab/pack
   workspace = pipeline-lab/
   slug только lab-*
   task только на агентов из этого каталога.
   Next step не выдумывать.
3. Каждый шаговый агент (не оркестратор): скилл «прочитай cursor сценария,
   скопируй указанную заготовку в Feature-writing/<slug>/, напечатай
   last_message.txt, выйди». Не читать repositories/, analytics/, боевой spec.
4. Библиотека (ещё без семи сценариев):
   pipeline-lab/fixtures/<step>/{ok,fail,retry,empty,dirty}/
   В каждой: файлы-артефакты шага + last_message.txt
   (ok / ASK_PARENT→retry / timeout|FAIL→fail / пустой отчёт / отчёт с gaps).
   Имена артефактов как у spec (context, spec, *-check.md, *-challenges.md,
   routing-state.json и т.д.), чтобы collectors/predicates пака узнали их.
5. Скрипт тика: pipeline-lab/apply_fixture.py — копирует заготовку по
   (slug, step, variant). Агент только вызывает его.
6. Хуки стенда: pipeline-lab/.qwen/hooks/ и settings.hooks.json — те же
   matcher-имена, что в бою, команды зовут ../scripts/pipeline_before_subagent.py
   и pipeline_after_subagent.py с --pack-dir. Основной .qwen/settings.hooks.json
   не трогать.

Не делать: семь сценариев, живой прогон Qwen, правки pipelines/spec/.

Критерий готовности:
- python3 pipeline-lab/apply_fixture.py --slug lab-demo --step check-feature --variant dirty
  создаёт ожидаемые файлы под pipeline-lab/Feature-writing/lab-demo/.
- Тот же вызов с variant=ok / empty / fail / retry — разный last_message и infer_result
  (ok / ok-или-пустой / fail / retry) через pipeline_after_subagent.infer_result.
- git diff не содержит .qwen/agents/spec-reviewer.md (боевой).
```

---

## Сессия 3 — семь сценариев (матрица, ещё не живой Qwen)

### Промпт сессии 3

```
Контекст: репо gigacode_analytics. План: pipeline-lab/SESSIONS.md.
Сессии 1–2 закрыты: pack, --pack-dir, тонкие агенты, fixtures/, apply_fixture.py.

Задача только сессии 3: семь детерминированных сценариев + headless-прогон
(delegate → apply_fixture → after_subagent → снова delegate) без Qwen.

Сделай pipeline-lab/scenarios/<id>/ :
  cursor.json     — список тиков: {step, variant}
  expect_path.json — шаги и action на каждом ходе (task/ready/stopped/ask_user/error)
  README на одну фразу «какой угол»

Сценарии (slug = имя папки):

1. lab-01-retry-same-step
   Шаг с variant=retry (ASK_PARENT) → следующий task тот же subagent, не сосед.
2. lab-02-gaps-then-recheck
   check-feature dirty/gaps → resolve-gaps → снова check-feature.
3. lab-03-challenge-not-check
   Стояли на challenge-feature ok (или retry) → next только resolve-challenges.
   Не check-feature. Это регресс сегодняшнего бага графа.
4. lab-04-step-fail-stops
   variant=fail → stopped или повтор только если так говорит delegate, без выдуманного агента.
5. lab-05-empty-artifact
   variant=empty на check-feature (или find-context) — предикат/next предсказуемы,
   хук не падает.
6. lab-06-pending-apply-beats-check
   DECISIONS pending-apply + needs_check → resolve-* по приоритету spec,
   не check-feature.
7. lab-07-missing-routing-state
   Нет JSON → сначала analyze-routing (P5), потом доменный шаг.

Драйвер: pipeline-lab/run.py --scenario <id>
Цикл на движке (не LLM): delegate --pack-dir → при action=task вызвать
apply_fixture по cursor → синтетический SubagentStop в after_subagent
(agent_type как в registry, last_assistant_message из заготовки) → снова delegate.
Сверить путь с expect_path.json. Workspace только pipeline-lab/.

Не делать: запуск qwen, правки боевого .qwen/, упрощение графа.

Критерий готовности:
- python3 pipeline-lab/run.py --all  — семь сценариев зелёные, без сети и без CLI.
- lab-03 падает, если убрать ребро challenge-feature→resolve-challenges или
  разрешить next=check-feature (можно показать одним временным assert-комментарием,
  не оставлять сломанный граф).
```

---

## Сессия 4 — живой оркестратор Qwen на стенде

### Промпт сессии 4

```
Контекст: репо gigacode_analytics. План: pipeline-lab/SESSIONS.md.
Сессии 1–3 закрыты: pack, тонкие агенты, run.py, семь сценариев зелёные headless.

Задача только сессии 4: тот же контур, но оркестратор — живой агент Qwen
внутри мини-проекта. Шаги по-прежнему тонкие.

Сделай:
1. Как стартовать: из каталога pipeline-lab/ (свой .qwen/), не из корня репо.
   Корень репо не должен начать звать тонкие агенты.
2. Команда входа: /lab-run <scenario-id> только в pipeline-lab/.qwen/commands/.
   Боевые /write-feature / /find-context не трогать.
3. Оркестратор в сессии Qwen: delegate с --pack-dir, task на тонкого агента,
   ждать SubagentStop/хук, снова delegate. Не спрашивать «запускать шаг?».
   Не читать pipelines/ и scripts/pipeline_* (как в QWEN.md).
4. Прогнать минимум три живых сценария, которые закрывают правку графа:
   lab-01-retry-same-step
   lab-03-challenge-not-check
   lab-06-pending-apply-beats-check
   Остальные четыре — если время есть; иначе оставить за headless run.py.
5. Кладка: короткий pipeline-lab/LIVE.md — cwd, команда старта, какие slug
   получились, совпал ли путь с expect_path.

Не делать: прогон bph-coupons-*, правку боевых агентов/хуков, --apply compile
стенда в pipelines/.

Критерий готовности:
- Живой lab-03: после challenge-feature оркестратор зовёт challenge-resolver,
  не spec-reviewer.
- Живой lab-01: retry → тот же агент ещё раз.
- Headless python3 pipeline-lab/run.py --all по-прежнему зелёный.
```

---

## После четырёх сессий

Правка оркестрации в основном репо → сначала `python3 pipeline-lab/run.py --all`
(секунды). Живой Qwen в `pipeline-lab/` — если сомнение, что оркестратор
ослушается JSON. Боевой spec по БПХ — только когда менялись настоящие скиллы,
не граф и не хуки.

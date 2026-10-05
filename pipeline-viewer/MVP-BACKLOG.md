# MVP backlog — оставшиеся задачи

Документ для следующих чатов. Здесь оставлены только задачи, которые ещё нужно сделать.
Уже закрытые пункты старого backlog не дублируются.

## Контекст

**Цель:** универсальная очерёдность агентов для `spec-v2` и следующих паков: граф задаётся на фронте, пользовательские условия остаются текстовыми, `routing-analyzer` интерпретирует их в `routing-state`, а runtime защищает прогон от технически бессмысленных повторов.

**Не пытаемся делать:** генерацию надёжного Python-кода из произвольной русской фразы на стрелке. Это остаётся зоной `routing-analyzer`.

**Делаем коробочно:** runtime guard-слой ниже роутера. Роутер выбирает следующий шаг, runtime проверяет, можно ли безопасно запускать его снова.

## Защита от регрессии

Перед коммитом минимум:

```bash
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --check
PYTHONPATH=scripts python3 scripts/pipeline_dispatch_golden_test.py --pipeline spec-v2
PYTHONPATH=scripts python3 scripts/pipeline_delegate.py --pipeline spec-v2 --slug my-v2-demo --dry-run
```

Если трогались hooks / active-task / continuation:

```bash
python3 scripts/pipeline_hooks_engine_test.py
python3 scripts/pipeline_runtime_engine_test.py
python3 scripts/pipeline_active_task_test.py
```

---

## A. Коробочные anti-loop шаги из чата

### A1 — Ask-continuation для любого ask-блока

**Проблема.** После вопроса пользователю resolver может закрыться, затем запускается `analyze-routing`, и только потом тот же resolver вызывается для применения ответа. Это дробит один логический процесс на несколько маршрутизационных циклов.

**Что сделать.** Для любого шага с `ask`: если агент задал вопрос пользователю и получил ответ, runtime должен вернуться в тот же step для применения ответа без промежуточного `analyze-routing`.

**Acceptance.** `ask → answer → apply` подтверждён логами/тестами минимум для двух разных ask-блоков и между answer и apply нет лишнего `analyze-routing`.

**Где смотреть.** `scripts/pipeline_delegate.py`, `scripts/pipeline_active_task.py`, hooks before/after subagent, `scripts/pipeline_runtime_engine_test.py`.

### A2 — No-repeat без нового входного события

**Проблема.** Если `routing-analyzer` снова ставит тот же признак в `true`, runtime может повторно запустить тот же step, даже если после прошлого успешного запуска ничего нового не произошло.

**Что сделать.** Не запускать тот же step повторно автоматически, если не появилось новое входное событие.

**Новое входное событие:** ответ пользователя, внешняя правка артефакта, новый/изменённый отчёт, изменение `pending-apply` / `needs-answer`, явный restart/continue.

**Acceptance.** Повтор того же step без нового входа блокируется или требует явного действия пользователя.

**Где смотреть.** `scripts/pipeline_delegate.py`, `scripts/build_pipeline_graph.py`, `scripts/pipeline_active_task.py`.

### A3 — Validation self-edit counts as checked

**Проблема.** Validation/check агент может сам успешно поправить проверяемый артефакт. После этого router видит свежую правку и снова открывает тот же validation/check шаг.

**Что сделать.** Для шагов типа validation/check собственная успешная правка проверяемого артефакта считается частью успешной проверки и не должна сама открывать повторный запуск этого же validation/check шага.

**Acceptance.** Если validation/check сам изменил артефакт и успешно завершился, повторный запуск этого же шага не происходит без внешней правки после него.

**Где смотреть.** `scripts/pipeline_delegate.py`, hooks before/after subagent, run-log/session-sync, `Feature-writing/<slug>/` artifact mtimes.

### A4 — Execution fingerprint для входного состояния шага

**Проблема.** Runtime сейчас не всегда понимает, что роутер предлагает тот же step на том же самом входном состоянии.

**Что сделать.** Перед запуском step сохранять лёгкий fingerprint входного состояния: step id, вызвавший routing field, relevant artifact mtimes, active-task/continuation, decisions/report timestamps.

**Acceptance.** Если роутер снова предлагает тот же step при том же fingerprint, runtime помечает это как подозрительный повтор и применяет guard.

**Где смотреть.** `scripts/pipeline_delegate.py`, `scripts/pipeline_active_task.py`, `scripts/build_pipeline_graph.py`.

### A5 — Circuit breaker и диагностика loop-ов

**Проблема.** Даже если router ошибся, pipeline не должен бесконечно жечь время на один и тот же step.

**Что сделать.** Ввести общий лимит повторов одного step без нового входного события. При превышении остановить dispatch и показать понятную диагностику.

**Диагностика должна показывать:** какой step повторялся, какой routing field снова горит, какой fingerprint не изменился, какого нового входного события не было.

**Acceptance.** При повторе сверх лимита pipeline останавливается с понятной причиной; viewer подсвечивает проблему на вкладке Прогон/Время.

**Где смотреть.** `scripts/pipeline_delegate.py`, `scripts/build_pipeline_graph.py`, `pipeline-viewer/static/app.js`.

---

## B. Оставшиеся пункты из MVP backlog

### B1 — Приоритеты стрелок без путаницы с engine-правилами

**Проблема.** В таблице приоритетов рядом пользовательские bool-правила и служебные (`routing_state_needs_refresh` и т.п.). Drag-reorder может сломать refresh analyzer.

**Что сделать.** Отделить engine/core rules от пользовательских dispatch-правил. Drag-reorder разрешить только для пользовательских правил.

**Acceptance.** Пользователь может менять порядок доменных стрелок, но не может случайно сломать служебный refresh/analyze каркас.

**Где смотреть.** Schema priority table в `pipeline-viewer/static/app.js`, `dispatch.yaml`, `edge_conditions` после Apply.

### B2 — Один источник правды для layout

**Проблема.** Layout может жить в `.authoring-draft.json` и/или YAML. Это два источника правды и риск рассинхрона после clone/apply.

**Что сделать.** Выбрать один вариант:
- A: при Apply писать `positions` в `graph.yaml` или отдельный layout-файл пака;
- B: зафиксировать контракт `draft в git = SSOT layout` и документировать, что draft нужно коммитить после расстановки.

**Acceptance.** После clone граф открывается с тем же layout без ручной реконструкции.

**Где смотреть.** `pipelines/spec-v2/.authoring-draft.json`, `pipeline-viewer/server.py`, `pipeline-viewer/pack_authoring_api.py`.

### B3 — Тайминги: человекочитаемые подписи и легенда

**Проблема.** На вкладке Время подписи могут быть сырыми id без нормального label пака.

**Что сделать.** Показывать подписи из `label` / registry пака и добавить короткую легенду цветов.

**Acceptance.** На вкладке Время сразу понятно, какой агент сколько ел, без расшифровки id.

**Где смотреть.** `pipeline-viewer/static/app.js`, `scripts/pipeline_timings.py`.

### B4 — Divergence / restart для всех паков

**Проблема.** Divergence overlay и часть restart UX ещё могут быть заточены под старый `spec` или отдельные ветки.

**Что сделать.** Не гейтить divergence по id старого пака. Restart брать только из `restartable_steps_by_pipeline[pid]`.

**Acceptance.** Отладка «факт ≠ целевой dispatch» и перезапуск с шага работают для `spec-v2` и следующих паков одинаково.

**Где смотреть.** `pipeline-viewer/static/app.js`, `scripts/pipeline_restart.py`, `pipeline-viewer/server.py`.

### B5 — Корень задач вне `Feature-writing`

**Проблема.** По умолчанию routing-state/main ищутся под `Feature-writing/...`. Другой домен (`Dev-tasks/` и т.п.) без правки `status.yaml` невидим для роутера.

**Что сделать.** В init/UI/доке явно показывать настройку путей артефактов (`status.artifacts.*.path`). Добавить пример пака не из `Feature-writing`.

**Acceptance.** Новый пак может жить вне `Feature-writing`, если пользователь явно указал корень артефактов.

**Где смотреть.** `pipelines/<id>/status.yaml`, `scripts/PIPELINE-ROUTING-STATE.md`, templates в `scripts/pipeline_pack_authoring.py`.

---

## C. Product readiness / конкурентоспособность

### C1 — Killer-demo graph до состояния demo-ready

**Проблема.** Без сильного demo продукт выглядит как абстрактный graph builder, а не как control plane для CLI-агентов.

**Что сделать.** Довести один демонстрационный граф до сценария:

```text
Brief/Jira → context → spec → gaps → challenge → code alignment → PASS
```

**Acceptance.** Есть sample input, итоговый документ, тайминг прогона, логи шагов, понятный PASS outcome и короткое сравнение с ручной работой.

**Где смотреть.** `pipelines/spec-v2/`, `Feature-writing/my-v2-demo/`, `pipeline-viewer/`, demo docs.

### C2 — 10-minute quickstart

**Проблема.** Новый пользователь не должен читать всю архитектуру, чтобы увидеть пользу.

**Что сделать.** Подготовить быстрый путь: одна команда/короткий сценарий запуска, sample repo или sample task, поднятый `pipeline-viewer`, demo-прогон.

**Acceptance.** Пользователь может увидеть работающий demo-прогон за 10 минут.

**Где смотреть.** `HOW-IT-WORKS.md`, README/quickstart docs, scripts для запуска viewer и demo.

### C3 — Pack template для чужого процесса

**Проблема.** Сейчас собрать свой pack можно, но для этого нужно понимать слишком много внутренней структуры workspace.

**Что сделать.** Подготовить шаблон pack: `agents/`, `skills/`, `graph.yaml`, `routing_conditions.yaml`, `status.yaml`, quality gates, пример task folder, минимальный README для автора pack.

**Acceptance.** Новый маленький pack можно собрать за вечер без изучения всего workspace.

**Где смотреть.** `scripts/pipeline_pack_authoring.py`, `scripts/PIPELINE-PACK-AUTHORING.md`, templates, `pipelines/spec-v2/`.

### C4 — Жёсткая изоляция skills по текущему шагу

**Проблема.** Хук может блокировать чужого агента, но чтение чужого skill пока не изолировано достаточно жёстко.

**Что сделать.** Добавить режим, где в prompt/context физически доступны только skills текущего шага.

**Acceptance.** Агент текущего step не видит чужие skills; попытка использовать чужой skill блокируется или явно диагностируется.

**Где смотреть.** hooks before subagent, CLI settings/prompt generation, `scripts/build_cli_settings.py`.

### C5 — Metrics of control во viewer

**Проблема.** Viewer должен доказывать управляемость процесса, а не только показывать граф.

**Что сделать.** Добавить summary-панель: сколько было шагов, retry/fail, ручных вопросов, закрытых GAP, divergence, времени до PASS, где процесс тормозил, какой итоговый outcome.

**Acceptance.** По завершённому прогону viewer отвечает: что было сделано, где были риски/задержки и насколько контролируемо дошли до результата.

**Где смотреть.** `pipeline-viewer/static/app.js`, `scripts/pipeline_timings.py`, `agent-logs/<slug>/metrics.json`, `run-log.jsonl`.

---

## Рекомендуемый порядок сессий

| Сессия | Пункты | Комментарий |
|--------|--------|-------------|
| A | A1 | Ask-continuation, проверить на нескольких ask-блоках |
| B | A2 + A4 | No-repeat и fingerprint лучше делать вместе |
| C | A3 | Validation self-edit guard |
| D | A5 | Circuit breaker + viewer диагностика |
| E | B1 | Приоритеты стрелок / engine rules |
| F | B2 | Layout SSOT |
| G | B3 + B4 | Наблюдение, тайминги, restart/divergence |
| H | B5 | Корень задач вне Feature-writing |
| I | C1 | Killer-demo graph |
| J | C2 + C3 | Quickstart + pack template |
| K | C4 | Skill isolation |
| L | C5 | Metrics of control |

## Промпт для другого чата

```text
Читай pipeline-viewer/MVP-BACKLOG.md.
В файле только оставшиеся задачи. Уже закрытые пункты старого MVP backlog не возвращай.
Возьми пункт <A1/B1/C1/...> и сделай только его.
Не расширяй scope.
В конце: зелёная регрессия из раздела «Защита от регрессии» и коротко обнови статус/комментарий в этом файле, если пункт закрыт.
```

# Как работает калибровка

Отдельный гид по meta-pipeline **после PASS**: что делает калибровка, когда её
запускать, какие команды и артефакты, и что делать с результатами.

Краткая шпаргалка для агентов: [CALIBRATION.md](CALIBRATION.md).
Общий контекст workspace: [HOW-IT-WORKS.md](HOW-IT-WORKS.md) (§13).

---

## 1. Зачем это нужно

Основной пайплайн (`spec-orchestrator`) доводит spec до **PASS**. Вы читаете
результат, правите формулировки, добавляете факты, которые «были у вас в голове».

Калибровка отвечает на два вопроса:

1. **Что пошло не так в процессе?** — повторы скиллов, лишние шаги, промахи
   агента при *доступных* источниках → патчи скиллов (`PROP-*`).
2. **Чего не хватило в источниках?** — факт не был в `analytics/`, нужный repo
   не склонирован, context-doc неполный → backlog для вас (`CTX-GAP-*`), а не
   «агент тупой».

Итог калибровки — не новая spec для разработки, а **улучшение процесса** и
**список дыр в контексте** перед следующей фичей.

---

## 2. Два оркестратора — не путать

| | Spec-пайплайн | Калибровка |
|---|---------------|------------|
| Оркестратор | `spec-orchestrator` | `calibration-orchestrator` |
| Старт | бриф, `/write-feature` | `/calibrate <slug>` или по шагам |
| Пишет SPEC | да (через `spec-writer`) | **нет** (только sync gold) |
| Пишет скиллы | нет | только `/apply-calibration` после approve |
| Когда | до PASS | **после** PASS и ваших правок |

После PASS `spec-orchestrator` **только предлагает** `/snapshot-baseline <slug>`.
Дальше вы сами решаете, когда запускать калибровку. Автопереключения нет.

---

## 3. Когда запускать

**Минимум:**

- `Feature-writing/<slug>/<slug>.md` существует;
- verdict **PASS** или **PASS WITH GAPS** (желательно);
- вы **уже поправили** spec под эталон (human review).

**Имеет смысл**, если:

- были повторные циклы check / resolve-gaps;
- вы добавляли пункты, которых не было в аналитике или репозитории;
- хотите проверить, помогли ли правки скиллов (benchmark rerun).

**Рано запускать**, если spec ещё не стабилен — baseline зафиксирует сырой черновик.

---

## 4. Полный workflow

```
PASS
  │
  ▼
/snapshot-baseline <slug>          ← заморозка SPEC + отчётов в baseline/
  │
  ▼
[вы правите SPEC в Feature-writing/]
  │
  ▼
/capture-review <slug>             ← gold/ + human-review.md (REV-*)
  │
  ▼
/analyze-delta <slug>              ← delta + context-gaps.md (CTX-GAP-*)
  │
  ▼
/analyze-telemetry <slug>          ← разбор agent-logs (опционально, но полезно)
  │
  ▼
/propose-calibration <slug>        ← proposals/ (PROP-*, только skill-gap)
  │
  ▼
[вы approve PROP-* в proposals.md]
  │
  ▼
/apply-calibration <slug>          ← патч .gigacode/skills/ (approved only)
  │
  ▼
новая сессия → /benchmark-rerun <slug>   ← изолированный прогон
  │
  ▼
python3 scripts/score_calibration_run.py <slug>
```

**Одной командой:** `/calibrate <slug>` — `calibration-orchestrator` пройдёт
цепочку с паузами на ваши ответы (review готов? approve PROP-*?).

---

## 5. Пошагово: что происходит

### Шаг 0 — Spec-пайплайн завершён

Файл `Feature-writing/<slug>/<slug>.md` + отчёты (`*-code-alignment.md`, …).
Телеметрия в `agent-logs/<slug>/` (если оркестратор вызывал ingest).

### Шаг 1 — `/snapshot-baseline <slug>`

**Скрипт:** `python3 scripts/snapshot_baseline.py <slug> [--new-run]`

Копирует текущий SPEC и сопутствующие артефакты в:

`Calibration/<slug>/runs/run-NNN/baseline/`

Плюс `inputs.lock.json` — бриф, profile, sections, ссылка на agent-logs run.

Это **то, что агент сдал**, до ваших правок. Baseline не перезаписывается.

### Шаг 2 — Human review (вы)

Редактируете `Feature-writing/<slug>/<slug>.md` как эталон: факты, структура,
формулировки. Комментарии в чате («добавь пункт X», «этого не было в аналитике»)
потом попадут в `human-review.md`.

### Шаг 3 — `/capture-review <slug>`

**Субагент:** `review-capturer`

1. `sync_gold_spec.py` — текущий SPEC → `gold/`.
2. `human-review.md` — каждая правка как `REV-NN` с полем **`cause`**:

| cause | Смысл |
|-------|--------|
| `context-gap` | Агент не мог знать — не было в analytics/repo/context/brief |
| `skill-gap` | Источник был — агент не нашёл или не применил |
| `hybrid` | Частично было, не хватало модуля или связки |
| `unclear` | Недостаточно данных |

**Совет:** если правка из «головы», явно скажите в чате — агент зафиксирует
`context-gap` и ваш комментарий дословно.

### Шаг 4 — `/analyze-delta <slug>`

**Субагент:** `regression-analyst`

**Скрипты:**

- `analyze_spec_delta.py` — diff baseline vs gold, `delta-analysis.md`;
- `analyze_context_gaps.py` — поиск добавленных фактов в `repositories/`,
  `analytics/`, context-doc → `context-gaps.md`.

Агент дополняет:

- **Root cause map** в `delta-analysis.md` (cause, skill, CTX-GAP, process);
- **`why_agent_could_not_know`** для каждого `CTX-GAP-*`;
- конкретные remediation (какой repo, какой файл analytics).

### Шаг 5 — `/analyze-telemetry <slug>`

**Субагент:** `session-telemetry-analyst`

Читает `agent-logs/<slug>/runs/run-NNN/`: `anomalies.md`, skill repeats,
tool spikes. Пишет `telemetry-analysis.md`. Нужен для обоснованных `PROP-*`.

Ingest при необходимости: `/archive-session <slug>` или
`python3 scripts/ingest_session_telemetry.py <slug> --cli gigacode`.

### Шаг 6 — `/propose-calibration <slug>`

**Субагент:** `calibration-proposer`

Пишет `proposals/proposals.md` и `PROP-NN.md` — **только skill/process gaps**.
Max 5 proposals за run. Status: `needs-answer` → вы → `approved` | `rejected` | `deferred`.

**Не смешивать:** `CTX-GAP-*` не превращаются в `PROP-*`.

### Шаг 7 — Approve и `/apply-calibration <slug>`

**Субагент:** `calibration-applier`

Патчит только **approved** `PROP-*`, по умолчанию **L1** — файлы в
`.gigacode/skills/` (или `.qwen/`, `.opencode/`). Kits (L3) — только если
proposal явно critical.

### Шаг 8 — `/benchmark-rerun <slug>` (новая сессия)

**Субагент:** `benchmark-runner`

**Скрипт:** `prepare_benchmark_rerun.py` — изолированный workspace:

```
Calibration/<slug>/runs/run-NNN/rerun/
  brief.txt
  Feature-writing/<slug>/    ← part-dir для write-feature
```

**Важно:** benchmark запускается в **новой сессии** `spec-orchestrator`, не из
calibration-orchestrator. Чеклист:

1. Новая сессия → `spec-orchestrator`.
2. Brief из `rerun/brief.txt`.
3. `--part-dir` → `Calibration/.../rerun/Feature-writing`.
4. Profile/sections из `inputs.lock.json`.
5. Полный пайплайн до PASS.
6. `python3 scripts/score_calibration_run.py <slug>` — similarity rerun vs gold.

### Шаг 9 — Scorecard

**Скрипт:** `score_calibration_run.py`

`scorecard.json`: similarity baseline/gold/rerun, skill_loads, anomalies,
счётчики context gaps.

---

## 6. Дерево артефактов

```
Calibration/<slug>/
  manifest.json                 ← current run, список runs
  runs/run-001/
    inputs.lock.json            ← бриф, profile, sections, agent-logs link
    baseline/                   ← snapshot до ваших правок
      <slug>.md
      *-decisions.md, *-code-alignment.md, …
    gold/                       ← эталон после review
      <slug>.md
    review/
      human-review.md           ← REV-* + cause
      delta-analysis.md         ← diff + root cause map
      delta-summary.json
      context-gaps.md           ← CTX-GAP-* (ваш backlog)
      context-gaps.json
    proposals/
      proposals.md              ← таблица PROP-*
      PROP-01.md, …
    rerun/                      ← benchmark workspace
      brief.txt
      Feature-writing/<slug>/
    scorecard.json
```

Папка `Calibration/` в `.gitignore` (кроме [Calibration/README.md](Calibration/README.md)) —
локальные прогоны.

Связь с телеметрией: `inputs.lock.json` ссылается на `agent-logs/<slug>/runs/run-NNN/`.

---

## 7. Context gaps vs skill proposals

Два разных исхода — два разных действия.

### CTX-GAP-* — «не хватило контекста»

**Файл:** `review/context-gaps.md`

**Пример:** вы добавили пункт про модуль комиссий; в `repositories/` не было
этого сервиса, в `analytics/` нет упоминания.

**Что делать вам (не агенту):**

- экспорт / дописать постановку в `analytics/`;
- `git clone` нужного repo в `repositories/`;
- обновить `Feature-context/<slug>.md`;
- опционально — метка в коде (`// ANALYTICS: …`) для следующих прогонов.

### PROP-* — «скилл/процесс можно улучшить»

**Файлы:** `proposals/proposals.md`, `PROP-NN.md`

**Пример:** факт был в analytics, агент три раза грузил `use-case-analysis` и
пропустил BR в §3.

**Что делать:** approve → `/apply-calibration` → benchmark rerun.

### Как не перепутать

| Вопрос | Если «да» → |
|--------|-------------|
| Факт был в analytics/repo/context до вашей правки? | skill-gap → PROP |
| Вы принесли факт из головы / внешней системы? | context-gap → CTX-GAP |
| Не уверены? | `cause: unclear` в REV, агент уточнит в delta |

---

## 8. Команды и субагенты

| Команда | Кто выполняет | Результат |
|---------|---------------|-----------|
| `/snapshot-baseline <slug>` | скрипт | `baseline/`, `inputs.lock.json` |
| `/capture-review <slug>` | `review-capturer` | `gold/`, `human-review.md` |
| `/analyze-delta <slug>` | `regression-analyst` | `delta-*`, `context-gaps.*` |
| `/analyze-telemetry <slug>` | `session-telemetry-analyst` | `telemetry-analysis.md` |
| `/propose-calibration <slug>` | `calibration-proposer` | `proposals/` |
| `/apply-calibration <slug>` | `calibration-applier` | патч skills |
| `/benchmark-rerun <slug>` | `benchmark-runner` | `rerun/` + чеклист сессии |
| `/calibrate <slug>` | `calibration-orchestrator` | вся цепочка |

CLI для ingest: `--cli gigacode` | `qwen` | `opencode`.

---

## 9. Скрипты (без slash-команд)

| Скрипт | Назначение |
|--------|------------|
| `snapshot_baseline.py <slug>` | Baseline до human review |
| `sync_gold_spec.py <slug>` | Текущий SPEC → gold |
| `analyze_spec_delta.py <slug>` | Diff baseline vs gold |
| `analyze_context_gaps.py <slug>` | Scaffold CTX-GAP-* |
| `prepare_benchmark_rerun.py <slug>` | Изолированный benchmark workspace |
| `score_calibration_run.py <slug>` | Scorecard прогона |

Пример ручного прогона delta + context gaps:

```bash
python3 scripts/analyze_spec_delta.py my-feature
python3 scripts/analyze_context_gaps.py my-feature
```

---

## 10. Пример сценария

1. Фича `composite-active-order-commission` получила PASS.
2. `/snapshot-baseline composite-active-order-commission` — baseline зафиксирован.
3. Вы добавляете в §3 пункт про лимит комиссии: «этого не было в Confluence,
   модуль X не в repositories».
4. `/capture-review composite-active-order-commission` → `REV-01`, `cause: context-gap`.
5. `/analyze-delta` → `CTX-GAP-01`: 0 hits в analytics/repo; remediation — clone X,
   дописать analytics.
6. `/analyze-telemetry` → 15× `write-feature`, anomaly `skill.repeat`.
7. `/propose-calibration` → `PROP-01`: уточнить check-list в write-feature (skill-gap).
8. Вы approve `PROP-01`, reject `PROP-02`.
9. `/apply-calibration` — патч одного skill.
10. Новая сессия, `/benchmark-rerun`, полный пайплайн в `rerun/`.
11. `score_calibration_run.py` — rerun ближе к gold, context_gaps: 1 open.

**После задачи:** закрываете `CTX-GAP-01` вручную (analytics + repo), следующая
фича уже с полным контекстом.

---

## 11. Частые ошибки

| Ошибка | Почему плохо | Как правильно |
|--------|--------------|---------------|
| Калибровка до PASS | baseline = сырой черновик | дождаться verdict |
| Правки spec до snapshot | baseline = уже с вашими правками | сначала snapshot |
| Ждать auto `/calibrate` | оркестраторы разделены | явно `/calibrate` или шаг |
| Benchmark в той же сессии | смешение контекстов | новая сессия spec-orchestrator |
| CTX-GAP → PROP | патчите скилл вместо analytics | разные артефакты |
| Нет ingest | telemetry-analysis пустой | `/archive-session` после пайплайна |

---

## 12. Связанные документы

| Документ | Содержание |
|----------|------------|
| [CALIBRATION.md](CALIBRATION.md) | Краткая шпаргалка для агентов |
| [HOW-IT-WORKS.md](HOW-IT-WORKS.md) | Весь workspace + §13 кратко |
| [agent-logs/README.md](agent-logs/README.md) | Телеметрия CLI-сессий |
| [Calibration/README.md](Calibration/README.md) | Layout папки (в git) |
| [AGENTS.md](AGENTS.md) | Таблица skills и slash-команд |

# Как устроен этот workspace

Документ для полного понимания: что делает софт, кто за что отвечает,
как пишется spec и что происходит после.

Команды в чате начинаются с `/` в GigaCode (`gigacode`), Qwen Code (`qwen`) или
OpenCode. Скрипты лежат в `scripts/`. Форма разделов spec — в `kb-writing-kits/`,
список блоков — в `spec-catalog.yaml`, не в Python.

---

## 1. Что это за продукт

Это не сервис History Operations и не код фичи.

Это **аналитический конвейер**: из брифа, аналитики и клонов репозиториев
собирается спецификация фичи — один Markdown-файл, который потом отдаётся
в разработку.

Итог одной фичи:

`Feature-writing/<slug>/<slug>.md`

`<slug>` — короткое имя в kebab-case, например `bph-moex-tax`.
Одна фича = одна папка. Внутри spec и все отчёты по ней.

Готово, когда `/check-feature-code` ставит verdict **PASS** или
**PASS WITH GAPS**, без Critical/Major расхождений с кодом.

---

## 2. Три слоя, которые нельзя путать

| Слой | Где | Роль |
|------|-----|------|
| **Форма** | `kb-writing-kits/` (`templates/`, `quality-gates/`) | Как выглядит раздел |
| **Список блоков** | `kb-writing-kits/spec-catalog.yaml` | Какие главы писать и какой kit |
| **Пульт** | `scripts/write_feature.py` | Читает каталог, клеит фрагменты |
| **Люди-агенты** | `.gigacode/`, `.qwen/`, `.opencode/` | Маршрут к kit; `*-analysis` не удаляем |

Скрипт **не пишет** текст spec. Он только:

- строит план блоков;
- проверяет фрагмент: не пустой; PlantUML, если UML в плане;
- склеивает фрагменты в один файл.

Текст пишет агент `spec-writer`. Вид раздела правят в kit. Состав документа —
в `spec-catalog.yaml`.

---

## 3. Кто есть кто

```
вы  →  /write-feature
         ↓
   spec-orchestrator     не пишет spec, только гоняет шаги
         ↓
   write_feature.py --mode plan
         ↓
   вы подтверждаете набор блоков
         ↓
   на каждый блок:  spec-writer  (свежий контекст)
         ↓
   write_feature.py --mode check-part
         ↓
   write_feature.py --mode assemble
         ↓
   spec-reviewer (/check-feature)
         ↓
   дальше по пайплайну (gaps, challenges, код)
```

**Оркестратор** (`spec-orchestrator`) — дирижёр. Сам не трогает
`Feature-writing/<slug>/<slug>.md`. Запускает субагентов по одному шагу.
Следующий шаг не спрашивает («запускать check-feature?») — запускает сам.
Пауза только когда без вас нельзя: нет брифа, неоднозначный slug,
набор блоков, вопросы resolve-*.

**Writer** (`spec-writer`) — пишет **один** блок за сессию. Потом его
вызывают снова на следующий блок. Так контекст не распухает:
в одной сессии один-два скилла, не весь план.

**Kit-скилл** (`use-case-analysis`, `integration-analysis`, …) — инструкция
«какие файлы kit открыть и что заполнить». Writer обязан прочитать
template / example / gate **целиком**, не через `head`.

**Пайплайн-скиллы** (`find-context`, `check-feature`, `resolve-gaps`, …) —
другие шаги, не написание блока.

---

## 4. Пульт: раздел → блок → скилл

Это главная идея write-feature.

1. **Раздел** — кусок шаблона, код вроде `1.2-usecase` или `4.2.3`.
2. **Блок** — одна сессия writer. В блоке один или несколько разделов.
   Пример: `usecase-as-is` = таблица UC + диаграмма.
3. **Скилл** — кого вызвать, чтобы написать эти разделы.

В `write_feature.py` у блока два поля:

- `skills` — вызываются всегда, если блок попал в план;
- `section_skills` — вызываются **только если этот раздел активен**.

Пример:

```
usecase-as-is
  разделы: 1.2-usecase, 1.2-diagram
  skills:  use-case-analysis
  section_skills:  1.2-diagram → uml-diagram-analysis
```

Профиль SIHIST включает оба раздела → в плане два скилла.
Профиль core без `1.2-diagram` → в плане только `use-case-analysis`.
Убрали строку из `section_skills` — UML больше не вызывается.

Алгоритм (`4.2.2`) — тот же `use-case-analysis`, но без UML.
Архитектура добавляет UML только если в плане есть `3.2`.

### Как попадает раздел в план

`section_profiles.py`:

1. Берётся профиль: по умолчанию **sihist**.
2. К нему **добавляются** разделы по словам в брифе (не вместо ядра):
   Kafka/событие → async `4.1.2`; «миграц» → миграция; threat, приёмка, C4.
3. Либо вы передаёте `--sections` списком — тогда профиль игнорируется.

Профили:

| Профиль | Что внутри |
|---------|------------|
| `core` | цель, UC текстом, ограничения |
| `sihist` | core + PlantUML в UC + контракт + алгоритм + модель + маппинг + NFR + логи/метрики |
| `full` | sihist + архитектура + async + миграция + угрозы + приёмка |

SIHIST — обычный путь для History Operations.

---

## 5. Как пишется spec (write-feature)

### Шаг А. План

```bash
python3 scripts/write_feature.py "<бриф>" --mode plan --name <slug> \
  --profile sihist --part-dir Feature-writing/<slug> [--protocol gRPC]
```

Скрипт печатает:

1. Таблицу блоков: id, скиллы, разделы, путь к фрагменту.
2. Раздел **«Задания spec-writer»** — готовые карточки:

```
### `usecase-as-is`
- block_id: `usecase-as-is`
- skills: use-case-analysis, uml-diagram-analysis
- sections: 1.2-usecase, 1.2-diagram
- part: `Feature-writing/<slug>/<slug>.part-usecase-as-is.md`
```

Оркестратор показывает таблицу вам и спрашивает: что убрать, что добавить
(threat, приёмка, миграция, async). Пока не ответите — писателей нет.

Потом он **копирует карточку целиком** в задание writer.
Строка `skills:` — весь список, не «первый скилл».

Протокол (`--protocol` или бриф): REST, gRPC, GraphQL, SOAP, Async.
Не назван → REST. В брифе Kafka/событие → Async.
Скрипт протокол сам не угадывает, кроме печати в плане; угадывание —
в скилле `integration-analysis`.

### Шаг Б. Один блок = один writer

В задании обязательно:

- бриф и slug;
- карточка блока (`block_id` + все `skills`);
- утверждённый `--sections`;
- протокол, если есть;
- пути: `Feature-context/<slug>.md` и
  `Feature-writing/<slug>/<slug>.context.md`.

Writer:

1. Грузит скилл `write-feature` (правила фрагмента и гэпов).
2. Грузит **ровно** скиллы из карточки. Чего нет в карточке — не грузит.
3. Для каждого скилла читает template / example / gate из
   `kb-writing-kits/` целиком.
4. Читает контекст-документ и накопленный `.context.md`, если есть.
5. Черновик только из брифа + контекста + kit. Нет факта → `[GAP-...]`,
   подраздел не выкидывает.
6. Если гэпы закрываются якорями из контекста — закрывает. Иначе оставляет.
7. Пишет `Feature-writing/<slug>/<slug>.part-<block_id>.md`.

Два скилла в одном блоке (UC + UML) — один файл фрагмента: таблица сценария
и PlantUML рядом.

### Шаг В. Приём фрагмента

```bash
python3 scripts/write_feature.py "<бриф>" --mode check-part --name <slug> \
  --block-id usecase-as-is --part-dir Feature-writing/<slug> \
  --profile sihist --sections "<утверждённый список>"
```

Скрипт смотрит **тот же план**, что и `--mode plan` (те же бриф, профиль,
`--sections`). Потом отказ, если:

- нет файла или файл пустой;
- в скиллах есть `uml-diagram-analysis`, а в тексте нет `@startuml` / `@enduml`;
- есть `integration-analysis`, нет примера запроса (`Пример запроса` / `## Примеры`);
- есть `data-model-analysis`, нет `ER-диаграмма`.

`check-part` вызывает **оркестратор один раз** на блок — всегда с `--block-id`
и `--sections`. Writer на первом проходе проверку не гоняет. Отказ — одна
повторная попытка writer. Второй отказ — стоп, сборки нет.

Важно: если вы утвердили свой список `--sections` (например убрали диаграммы),
**тот же список** надо передать в `check-part`. Иначе проверка возьмёт
дефолтный SIHIST и потребует PlantUML.

### Шаг Г. Сборка

Когда все блоки приняты:

```bash
python3 scripts/write_feature.py "<бриф>" --mode assemble --name <slug> \
  --part-dir Feature-writing/<slug> \
  --out Feature-writing/<slug>/<slug>.md
```

Скрипт склеивает фрагменты в порядке разделов шаблона, ставит родительские
заголовки (`## 1. Бизнес-требования` и т.д.). Если `--out` указан и все
фрагменты на месте — удаляет `*.part-*.md` и `*.context.md`.
Чего-то не хватает — рабочие файлы не трогает.

Сразу после сборки оркестратор запускает `/check-feature`. Не ждёт «да».

---

## 6. Что вызывается на обычном SIHIST

| Блок | Скиллы | Разделы |
|------|--------|---------|
| `goal` | `requirements-analysis` | 1.1 цель |
| `usecase-as-is` | `use-case-analysis`, `uml-diagram-analysis` | 1.2 текст + sequence |
| `usecase-to-be` | то же | 1.3 текст + sequence |
| `constraints` | `requirements-analysis` | 2 |
| `integration` | `integration-analysis` | 4.1.1 (+ 4.1.2 если Kafka в брифе) |
| `algorithm` | `use-case-analysis` | 4.2.2 |
| `data-model` | `data-model-analysis` | 4.2.3 ER и сущности |
| `field-mapping` | `data-mapping-analysis` | маппинг полей |
| `nfr` | `nfr-analysis` | безопасность, perf, reliability, config, тогглы |
| `observability` | `observability-analysis` | логи и метрики |

Не в дефолте (keyword или `--profile full`):

| Блок | Скилл |
|------|--------|
| `architecture` | `architecture-analysis` (+ UML при 3.2) |
| `migration` | `migration-analysis` |
| `threat-model` | `threat-model-analysis` |
| `acceptance` | `acceptance-test-analysis` |

Скилл модели данных **может сам** ещё заглянуть в kit маппинга и миграции,
если в брифе есть такие слова. Это не пульт: вы уберёте блок маппинга из
плана, а модель всё равно может написать кусок маппинга. Так оставлено
намеренно — лучше лишнее, следующий шаг пайплайна подчистит дубли.

---

## 7. Киты: что живое, что лежит на полке

Writer смотрит в конкретные папки (канон):

| Кит | Скилл |
|-----|--------|
| `functional-process` | `requirements-analysis` |
| `use-case` | `use-case-analysis` |
| `uml-diagram` | `uml-diagram-analysis` (только sequence) |
| `integration` | `integration-analysis` |
| `database-storage` | `data-model-analysis` |
| `field-lineage` | `data-mapping-analysis` |
| `nfr` | `nfr-analysis` |
| `observability` | `observability-analysis` |
| `architecture` | `architecture-analysis` |
| `migration-liquibase` | `migration-analysis` |
| `security-threat-model` | `threat-model-analysis` |
| `acceptance-checks` | `acceptance-test-analysis` |

В `kb-writing-kits/kits/` есть ещё папки, которые **write-feature не зовёт**:

- `frontend-presentation` — нет UI-раздела в шаблоне SIHIST;
- `data-entity` — дубль модели данных;
- `cache-lifecycle`, `feature-toggle-config` — копии NFR, тогглы уже в `nfr`;
- `interface-contract` — копия `integration`.

Их можно не удалять (пригодятся для KB / другой задачи). На spec фичи
они не влияют.

Внутри живых китов тоже читается не всё: у UML не грузятся activity/state,
у интеграции — страница «integration-page», анкеты NFR не открываются.
Скилл явно перечисляет файлы.

---

## 8. Пайплайн после черновика

```
/find-context
  → /write-feature
  → /check-feature
  → /resolve-gaps          если есть [GAP-...]
  → /challenge-feature
  → /resolve-challenges
  → /check-feature-code ↔ /resolve-code-alignment   не больше 3 кругов
```

В любой момент: `/feature-status <slug>` — что открыто и **один** следующий шаг.
Оркестратор этот шаг запускает сам.

| Команда | Кто пишет | Смысл |
|---------|-----------|--------|
| `/find-context` | контекст-документ | факты из analytics / кода / БД |
| `/write-feature` | SPEC | блоки, как выше |
| `/check-feature` | SPEC | сверка с брифом, аналитикой, формой |
| `/resolve-gaps` | SPEC + карта | закрыть `[GAP-...]` вопросами вам |
| `/challenge-feature` | только `*-challenges.md` | каверзные вопросы, spec не трогает |
| `/resolve-challenges` | SPEC + карта | закрыть `CH-*` |
| `/check-feature-code` | отчёт alignment | spec vs `repositories/` |
| `/resolve-code-alignment` | SPEC | закрыть расхождения с кодом |
| `/code-review` | ничего | двухосевой обзор правок, по запросу |

Spec должен оставаться **чистым**: журналы решений — в `*-gaps-resolved.md`
и `*-challenges-resolved.md`, не в теле spec.

Правка BR / use case после resolve → снова `/check-feature`.
Правка после alignment → снова `/check-feature-code`.
Закрытые `Q-XX` дописываются в контекст, current-state там не переписывается
(`refresh_context.py` трогает только «Что учесть»).

---

## 9. Файлы одной фичи

```
Feature-writing/<slug>/
  <slug>.md                      финальная spec
  <slug>-code-alignment.md       сверка с кодом
  <slug>-gaps-resolved.md        карта гэпов
  <slug>-challenges.md           банк CH-*
  <slug>-challenges-resolved.md  карта CH-*
  <slug>.part-*.md               рабочие куски (удаляются после assemble)
  <slug>.context.md              накопленное по блокам (тоже удаляется)

Feature-context/<slug>.md        контекст для writer и ревью
```

Канон путей: `.opencode/rules/artifact-paths.md`.

`analytics/`, `db-export/`, `repositories/` в git нет. После клона их
нужно положить на машину. Без них можно писать по уже собранному контексту,
но `/find-context` и `/check-feature-code` не на чем сверять факты.

---

## 10. Что сознательно не «идеально»

- Пульт для скиллов честный. Проверка фрагмента ловит UML, не все таблицы kit.
- Оркестратор и writer всё ещё **должны** скопировать карточку и запустить
  `check-part` (оркестратор, один раз). Скрипт сам агента не пинает.
- Модель данных может написать лишний маппинг. Дубли потом чистятся.
- Мёртвые киты на диске не подключены — это не ошибка пайплайна.

Логика «какие блоки в SIHIST и как склеивается spec» после правок пульта
не менялась. Добавились карточки заданий и `check-part`.

---

## 11. Команды скриптов (шпаргалка)

```bash
# план + карточки заданий
python3 scripts/write_feature.py "<бриф>" --mode plan --name <slug> \
  --profile sihist --part-dir Feature-writing/<slug>

# принять один фрагмент
python3 scripts/write_feature.py "<бриф>" --mode check-part --name <slug> \
  --block-id usecase-as-is --part-dir Feature-writing/<slug>

# склеить SPEC
python3 scripts/write_feature.py "<бриф>" --mode assemble --name <slug> \
  --part-dir Feature-writing/<slug> --out Feature-writing/<slug>/<slug>.md

python3 scripts/feature_status.py <slug>
python3 scripts/quality_gates.py <slug>
```

Код проверки маркеров UML: `scripts/part_checks.py`.
Набор разделов: `scripts/section_profiles.py` (читает `spec-catalog.yaml`).

---

## 12. Телеметрия CLI (`agent-logs/`)

Отдельный контур от spec и отчётов. Отвечает на вопрос: **как** агенты
выполняли пайплайн (какие skill грузили, были ли retry, сколько tool calls).

Spec — в `Feature-writing/<slug>/`. Телеметрия — в `agent-logs/<slug>/`.
Один `<slug>` = одна папка, как у context и feature.

### Кто что пишет

| Кто | Пишет логи? |
|-----|-------------|
| CLI (GigaCode / Qwen / OpenCode) | Да — сессия в home (jsonl или SQLite) |
| Субагенты (`spec-writer`, …) | **Нет** — не трогают `agent-logs/` |
| Оркестратор | Да — две shell-команды после каждого `task` |
| `ingest_session_telemetry.py` | Читает CLI → `events.jsonl`, `metrics.json`, `anomalies.md` |
| `append_run_log.py` | Строка в `run-log.jsonl` (какой шаг прошёл) |

Субагентам не нужны правки скиллов ради логов.

### Когда запускается

**После каждого шага пайплайна**, не один раз в конце.

Инструкция в `spec-orchestrator` (`.gigacode/`, `.qwen/`, `.opencode/`):

```
/task find-context     → вернулся → append_run_log + ingest
/task spec-writer #1   → вернулся → append_run_log + ingest
/task spec-writer #2   → …
/task spec-reviewer    → …
… до PASS / PASS WITH GAPS
```

После **каждого** возврата `task`, кроме `session-telemetry-analyst`:

```bash
python3 scripts/append_run_log.py --slug <slug> --step <шаг> --subagent <имя> --result ok
python3 scripts/ingest_session_telemetry.py <slug> --cli gigacode
```

`--cli`: `gigacode` | `qwen` | `opencode`.

| Момент | Поведение |
|--------|-----------|
| Первый ingest цепочки | `--new-run` → `runs/run-001/` |
| Каждый следующий шаг | без `--new-run` → тот же run обновляется |
| Конец пайплайна | финальный ingest + `anomalies.md` |
| Новый benchmark | `--new-run` → `run-002`, … |

Ошибка ingest **не останавливает** пайплайн.

### SubagentStop hook (обязательный цикл)

В `.qwen/settings.json` / `.gigacode/settings.json` — hook `SubagentStop` на pipeline-subagents.
Скрипт `.qwen/hooks/pipeline-after-subagent.sh` (или `.gigacode/…`) после каждого subagent:

```
append_run_log → ingest_session_telemetry → pipeline_validate → additionalContext
```

**Перед** `task` оркестратор вызывает `pipeline_set_active_task.py` (slug, step, subagent) —
hook читает `.pipeline-active-task.json`.

Viewer показывает validation в API графа (`validation` field) и в UI (баннер + sidebar).

Ручной догон, если hook не сработал: `/archive-session`, `/analyze-telemetry`, `pipeline_validate.py`.

### Откуда ingest читает

| CLI | Источник |
|-----|----------|
| GigaCode | `~/.gigacode/projects/.../` (jsonl) |
| Qwen Code | `~/.qwen/projects/.../` (jsonl) |
| OpenCode | `~/.local/share/opencode/opencode.db` |

OpenCode legacy: `--session-directory /path/to/old/workspace`.

### Артефакты и anomalies

```
agent-logs/<slug>/runs/run-001/
  run-log.jsonl
  events.jsonl
  metrics.json
  anomalies.md
  telemetry-analysis.md   ← после /analyze-telemetry
```

Эвристики без LLM: `skill.repeat` (≥3), `tool.spike` (≥80 calls), `check_part.retries` (≥2).

Подробнее: [agent-logs/README.md](agent-logs/README.md), [README.md § Телеметрия](README.md).

**Live-граф:** `python3 pipeline-viewer/server.py --slug <slug>` →
[pipeline-viewer/README.md](pipeline-viewer/README.md).

---

## 13. Калибровка процесса (`Calibration/`)

После PASS пользователь правит spec. Отдельный контур — оркестратор
**calibration-orchestrator** (не spec-orchestrator).

**Подробно:** [HOW-WORK-CALIBRATION.md](HOW-WORK-CALIBRATION.md).
**Шпаргалка для агентов:** [CALIBRATION.md](CALIBRATION.md).

```
/snapshot-baseline     → baseline/ + inputs.lock.json
[правки SPEC]
/capture-review        → gold/ + human-review.md
/analyze-delta         → delta-analysis.md + context-gaps.md (CTX-GAP-*)
/analyze-telemetry     → telemetry-analysis.md
/propose-calibration   → proposals/ (PROP-* only; not context gaps)
[approve PROP-*]
/apply-calibration     → патч L1 skills (approved only)
/benchmark-rerun       → rerun/ + новая сессия write-feature
score_calibration_run.py
```

Явный старт: `/calibrate <slug>`. Benchmark — **новая сессия** spec-orchestrator.

Скрипты: `snapshot_baseline.py`, `sync_gold_spec.py`, `analyze_spec_delta.py`,
`analyze_context_gaps.py`, `prepare_benchmark_rerun.py`, `score_calibration_run.py`.

**Context gaps:** если правка пользователя — факт, которого не было в `analytics/`,
`repositories/` или context-doc, это `CTX-GAP-*` (backlog для вас), а не PROP-*.

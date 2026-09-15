---
name: apply-lab-fixture
description: >-
  Lab stand-in skill: read the scenario cursor, copy a fixture into
  Feature-writing/<slug>/, print last_message.txt, exit.
user-invocable: false
---

# apply-lab-fixture

Тонкий шаг стенда `pipeline-lab`. Не пишешь spec, не ходишь в `repositories/`,
`analytics/`, боевой `Feature-writing/`, `pipelines/spec/`.

## Шаги

1. Slug из задания оркестратора. Только `lab-*`. Workspace = каталог
   `pipeline-lab/` (не корень репо).
2. Step — имя шага из файла агента (`find-context`, `check-feature`, …).
3. Variant из cursor, в таком порядке:
   - `Feature-writing/<slug>/.lab-cursor.json` → поле `variant`, либо
     `ticks[tick].variant` (тик двигает сам скрипт);
   - `scenarios/<slug>/cursor.json` → текущий тик `{step, variant}`;
   - явное `variant=` в задании;
   - иначе `ok`.
4. Скопируй заготовку **только** скриптом (не руками):

   ```bash
   python3 apply_fixture.py --slug <slug> --step <step>
   ```

   `--variant` не передавай на живом прогоне: курсор выбирает заготовку.
   Из корня репо: `python3 pipeline-lab/apply_fixture.py …`.
   Скрипт кладёт канонические имена spec (`<slug>.md`, `*-check.md`,
   `*-challenges.md`, `*-routing-state.json`, `Feature-context/<slug>.md`, …)
   и печатает `last_message.txt` в stdout.
5. Если stdout пуст — прочитай `Feature-writing/<slug>/last_message.txt` и
   напечатай его **целиком** (может быть пустым). Это и есть ответ субагента.
6. Выйди. Не читай `repositories/`, `analytics/`, `db-export/`, боевой spec.

## Запреты

- Не выдумывать next step и не звать других субагентов.
- Не править боевой `.qwen/agents/`.
- Не ходить в `pipelines/` и `scripts/pipeline_*`.

---
name: analyze-routing
description: >-
  Writes Feature-writing/<slug>/<slug>-routing-state.json — factual snapshot
  for the deterministic router. Does not choose next_step. Pack-local:
  fields from pipelines/<pipeline_id>/routing_conditions.yaml status_fields.
user-invocable: false
---

# analyze-routing

Единственный редактируемый артефакт: `ROUTING_STATE` =
`Feature-writing/<slug>/<slug>-routing-state.json`.

## Pack SSOT

`pipeline_id` — из задания субагента / аргументов / `--pipeline` /
`.pipeline-active-task.json` (не угадывай pack). Источник имён и семантики
полей:

`pipelines/<pipeline_id>/routing_conditions.yaml` → секция `status_fields`.

Это SSOT analyzer для **текущего** пака. Не копируй инструкции другого пака
(например GAP/DECISIONS из `spec`) в пак, у которого свои `status_fields`
другие или короче. Для пака `spec` те же имена полей по-прежнему заполняются —
они живут в `pipelines/spec/routing_conditions.yaml`; следуй их `instruction`.

Контракт JSON: `scripts/PIPELINE-ROUTING-STATE.md`.
`collectors.py` больше не источник семантики.
`next_step` / `ready` / `orchestrator_mode` **не писать**.
Где сейчас стоим (`position`) пишет хук SubagentStop, не ты. При перезаписи
JSON сохрани top-level `position` и `step_completion`, если они уже есть.

Граф: node `analyze-routing` там, где pack его объявил (`graph.yaml` /
`analyzer.step` в routing_conditions пака). После mutating step оркестратор
снова delegate; если JSON missing/stale/invalid — router выбирает этот шаг
(до domain-шагов, если так задано в dispatch пака).

## Когда

Файл нет, JSON битый / schema_version ≠ 1 / router-owned ключи в `fields`,
или mtime старше артефактов из `stale_vs` **этого** пака
(`pipelines/<pipeline_id>/routing_conditions.yaml`).

Mutating-шаги и gate-stamp — по graph / `status.yaml` пака (не хардкодь
список только из `spec`). Если gate-шаг всё же переписал артефакты — JSON
stale, снова этот шаг.

## Шаги

1. Разреши `<slug>` и `<pipeline_id>`. Нет обязательного артефакта пака —
   всё равно запиши JSON с presence-флагами по `status_fields` (для `spec`:
   нет SPEC → `has_spec: false`).
2. Прочитай `pipelines/<pipeline_id>/routing_conditions.yaml`. Ключи
   `status_fields` — полный список того, что класть в `fields`.
3. Прочитай (read-only) артефакты, на которые ссылаются `artifacts:` /
   `instruction` полей (пути — правило `artifact-paths` и pack `status.yaml`).
4. Для **каждого** ключа в `status_fields` заполни значение строго по полям
   `instruction` и `type` этого ключа в YAML пака. Не выдумывай id.
   Не заполняй ключи роутера. Не добавляй поля, которых нет в `status_fields`
   текущего пака. Engine после overlay может пересчитать Relates / mtime /
   `exists_as` — не подменяй это выдумкой.
5. Запиши JSON: `schema_version: 1`, `slug`, `generated_at` (UTC ISO), `fields`.
6. Краткий отчёт: путь, `pipeline_id`, ключевые счётчики из заполненных полей.
   Не называй следующий шаг пайплайна.

## Запреты

- Не вызывать `pipeline_dispatch.py` и не выбирать субагента.
- Не патчить domain-артефакты (SPEC / DECISIONS / отчёты / maps и т.п.).
- Не класть в `fields` ключи роутера (`next_step`, `ready`, `orchestrator_mode`, …).
- Не подменять `status_fields` чужого пака инструкциями из `pipelines/spec/`.

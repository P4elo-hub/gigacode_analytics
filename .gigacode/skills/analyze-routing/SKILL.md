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
JSON сохрани top-level `position`, `step_completion` и `routing_reports`, если
они уже есть.

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
3. Если прежний `ROUTING_STATE` валиден, возьми его `fields` как начальное
   состояние. Прочитай `status.yaml → artifacts.routing_reports` и только
   отчёты с `seq > routing_reports.last_seq`. Отсутствие упоминания в новых
   отчётах **не меняет** прежнее значение поля.
4. Сначала обнови поля по явным фактам из `outcomes`, `remaining_work`,
   `artifacts` и `summary` новых отчётов. Отчёт `incomplete: true`,
   противоречие, удаление артефакта или недостаточность сведений означает
   fallback: прочитай только необходимые артефакты по `status.yaml` /
   `instruction`. Если прежнего валидного состояния нет — выполни полный
   artifact fallback, как раньше.
5. Для **каждого** ключа в `status_fields` итоговый `fields` должен содержать
   значение правильного `type`: обновлённое либо сохранённое из прежнего
   состояния. Не выдумывай id.
   Не заполняй ключи роутера. Не добавляй поля, которых нет в `status_fields`
   текущего пака. Engine после overlay может пересчитать Relates / mtime /
   `exists_as` — не подменяй это выдумкой.
   Если после обновления ни одно domain-условие не требует шага (кандидат
   `ready`), сверь критичные presence-поля по диску (`status.yaml` artifacts).
   Расхождение — artifact fallback для этих полей, не доверяй одному journal.
6. Запиши JSON: `schema_version: 1`, `slug`, `generated_at` (UTC ISO), `fields`.
   Если journal полностью обработан, запиши top-level:
   `routing_reports: {schema_version: 1, last_seq: <index.last_seq>,
   index: <путь>, updated_at: <UTC ISO>}`. Не двигай cursor через отчёт,
   который не прочитан или не обработан fallback.
7. Краткий отчёт: путь, `pipeline_id`, диапазон обработанных `seq`, был ли
   artifact fallback, ключевые счётчики из заполненных полей.
   Не называй следующий шаг пайплайна.

## Запреты

- Не вызывать `pipeline_dispatch.py` и не выбирать субагента.
- Не патчить domain-артефакты (SPEC / DECISIONS / отчёты / maps и т.п.).
- Не класть в `fields` ключи роутера (`next_step`, `ready`, `orchestrator_mode`, …).
- Не подменять `status_fields` чужого пака инструкциями из `pipelines/spec/`.

## Обязательный короткий проход

При валидном ROUTING_STATE сначала читай status.yaml, прежний snapshot,
index.json и только отчёты с seq > routing_reports.last_seq. Семантика полей —
status_fields текущего пака. Не перечитывай старые отчёты для подтверждения
неизменённых полей. Полный новый отчёт, достаточный для изменения полей,
не требует чтения SPEC, DECISIONS, ALIGNMENT, CHALLENGES и maps.

Если новый отчёт incomplete, проверь сначала его summary: incomplete означает
отсутствие структурированного блока, а не отсутствие всех полезных фактов.
Fallback выполняй только для конкретного поля, которому не хватает факта;
остальные значения сохрани. Не превращай один неполный отчёт в полный обход.
Если snapshot отсутствует, полный fallback допустим только по артефактам
текущего slug. Не читай чужие фичи, graph.yaml, dispatch.yaml, registry JSON,
исходники Python, память других сессий; не исследуй устройство роутера.
Пути бери из status.yaml текущего пака, не ищи их glob по workspace.

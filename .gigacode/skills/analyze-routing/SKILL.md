---
name: analyze-routing
description: >-
  Writes Feature-writing/<slug>/<slug>-routing-state.json — factual snapshot
  for the deterministic router. Does not choose next_step. Phase 10 POC;
  spec still uses collectors until Phase 12.
user-invocable: false
---

# analyze-routing

Единственный редактируемый артефакт: `ROUTING_STATE` =
`Feature-writing/<slug>/<slug>-routing-state.json`.

Контракт: `scripts/PIPELINE-ROUTING-STATE.md`. Поля = имена status, которые
читает spec-роутер (`pipelines/spec/routing_conditions.yaml`).
`next_step` / `ready` / `orchestrator_mode` **не писать**.

## Когда

Шаг графа `analyze-routing` (pack `routing-poc`; spec cutover — Phase 11):
файл нет, JSON битый, или mtime старше SPEC (и в Phase 11 — старше context /
DECISIONS / challenges / alignment / maps).

## Шаги

1. Разреши `<slug>`. Нет `SPEC` — всё равно запиши JSON: `has_spec: false`,
   остальные факты по наличию файлов.
2. Прочитай (если есть): `SPEC`, `CONTEXT_DOC`, `DECISIONS`, `CHALLENGES`,
   `ALIGNMENT`, `GAPS_MAP`. Не правь их.
3. Заполни `fields` по контракту `pipelines/spec/routing_conditions.yaml`
   (имена status). **POC:** семантика полей пока как у spec collectors
   (`pipelines/spec/collectors.py`) — открытые `[GAP-...]`, строки DECISIONS
   `needs-answer` / `pending-apply`, `challenges.open`, frontmatter ALIGNMENT,
   `needs_check_feature`. **Phase 12:** только `routing_conditions.yaml`,
   collectors к тому моменту снимают. Не выдумывай id.
4. Запиши JSON: `schema_version: 1`, `slug`, `generated_at` (UTC ISO), `fields`.
5. Краткий отчёт в чат: путь, `open_gaps` count, needs-answer, stale-триггер.
   Не называй следующий шаг пайплайна.

## Запреты

- Не вызывать `pipeline_dispatch.py` и не выбирать субагента.
- Не патчить `SPEC` / `DECISIONS` / отчёты.
- Не класть в `fields` ключи роутера (`next_step`, `ready`, …).

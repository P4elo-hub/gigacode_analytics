---
name: analyze-routing
description: >-
  Writes Feature-writing/<slug>/<slug>-routing-state.json — factual snapshot
  for the deterministic router. Does not choose next_step. Phase 11 spec-domain;
  live spec dispatch still uses collectors until Phase 12.
user-invocable: false
---

# analyze-routing

Единственный редактируемый артефакт: `ROUTING_STATE` =
`Feature-writing/<slug>/<slug>-routing-state.json`.

Контракт: `scripts/PIPELINE-ROUTING-STATE.md`. Имена и семантика полей —
`pipelines/spec/routing_conditions.yaml` (SSOT). Совпадает с
`pipelines/spec/collectors.py`. `next_step` / `ready` / `orchestrator_mode`
**не писать**.

Граф `analyze-routing` пока только в pack `routing-poc`. Для spec — ручной
`/analyze-routing` и dual-run parity (Phase 11). Cutover в spec graph — Phase 12.

## Когда

Файл нет, JSON битый / schema_version ≠ 1 / router-owned ключи в `fields`,
или mtime старше любого из: SPEC, CONTEXT_DOC, DECISIONS, CHALLENGES,
ALIGNMENT, GAPS_MAP, CHALLENGES_MAP.

## Шаги

1. Разреши `<slug>`. Нет `SPEC` — всё равно запиши JSON: `has_spec: false`.
2. Прочитай (если есть), не правь:
   - `CONTEXT_DOC` — `Feature-context/<slug>.md`
   - `SPEC` — `Feature-writing/<slug>/<slug>.md`
   - `DECISIONS` — `…/<slug>-decisions.md`
   - `GAPS_MAP` — `…/<slug>-gaps-resolved.md`
   - `CHALLENGES` — `…/<slug>-challenges.md`
   - `CHALLENGES_MAP` — `…/<slug>-challenges-resolved.md`
   - `ALIGNMENT` — `…/<slug>-code-alignment.md`
3. Заполни `fields` по `routing_conditions.yaml`. Presence-флаги — существование
   файлов. Домен:
   - `open_gaps`: inline `[GAP-…]` + табличные GAP без «закрыт»/«closed»
   - DECISIONS Status `needs-answer` / `pending-apply`; alignment-subset если
     Relates ~ `[FICTKAM]-<n>` (не Q-*, не CH-*)
   - `challenges.*` из таблицы CH; dispatch смотрит `challenges.open`
   - ALIGNMENT frontmatter `verdict` / `alignment_iteration`; счётчик
     critical/major mismatch-строк
   - `needs_check_feature` (+ reason) — тот же алгоритм, что collectors
   - `stale` / `alignment_stale` — mtime (движок всё равно пересчитает)
   Не выдумывай id. Не заполняй ключи роутера.
4. Запиши JSON: `schema_version: 1`, `slug`, `generated_at` (UTC ISO), `fields`.
5. Краткий отчёт: путь, число `open_gaps`, needs-answer, stale-триггер.
   Не называй следующий шаг пайплайна.

## Запреты

- Не вызывать `pipeline_dispatch.py` и не выбирать субагента.
- Не патчить `SPEC` / `DECISIONS` / отчёты / maps.
- Не класть в `fields` ключи роутера (`next_step`, `ready`, `orchestrator_mode`, …).

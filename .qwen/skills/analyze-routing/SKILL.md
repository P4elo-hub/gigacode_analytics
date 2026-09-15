---
name: analyze-routing
description: >-
  Writes Feature-writing/<slug>/<slug>-routing-state.json — factual snapshot
  for the deterministic router. Does not choose next_step. Spec graph node
  (Phase 12); also used by pack routing-poc.
user-invocable: false
---

# analyze-routing

Единственный редактируемый артефакт: `ROUTING_STATE` =
`Feature-writing/<slug>/<slug>-routing-state.json`.

Контракт: `scripts/PIPELINE-ROUTING-STATE.md`. Имена и семантика полей —
`pipelines/spec/routing_conditions.yaml` (SSOT). `collectors.py` больше не
источник семантики. `next_step` / `ready` / `orchestrator_mode` **не писать**.
Где сейчас стоим (`position`) пишет хук SubagentStop, не ты. При перезаписи
JSON сохрани top-level `position` и `step_completion`, если они уже есть.

Граф: node `analyze-routing` в `pipelines/spec/graph.yaml` (и `routing-poc`).
После mutating step оркестратор снова delegate; если JSON missing/stale/invalid —
router выбирает этот шаг (P5, всегда до domain-шагов).

## Когда

Файл нет, JSON битый / schema_version ≠ 1 / router-owned ключи в `fields`,
или mtime старше любого из: SPEC, CONTEXT_DOC, DECISIONS, CHALLENGES,
ALIGNMENT, GAPS_MAP, CHALLENGES_MAP (`stale_vs`).

После mutating-шагов: write-feature, resolve-gaps, resolve-challenges,
challenge-feature, check-feature-code, resolve-code-alignment, find-context
(если записал CONTEXT). Check-feature **без** правок файлов — хук, не этот шаг.
Если check-feature всё же переписал SPEC — JSON stale, снова этот шаг.

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
   - `AGENT_RUN_LOG` — нужен для `needs_check_feature` (последний ok check-feature vs SPEC mtime)
3. Заполни `fields` по `routing_conditions.yaml`. Presence-флаги — существование
   файлов. Домен:
   - `open_gaps`: inline `[GAP-…]` + табличные GAP; id с «закрыт»/«closed»/
     «отложено»/«deferred» в строке таблицы — не открытый (и inline того же id тоже нет)
   - DECISIONS Status `needs-answer` / `pending-apply`; alignment-subset если
     Relates ~ `[FICTKAM]-<n>` (не Q-*, не CH-*)
   - `challenges.*` из таблицы CH; dispatch смотрит `challenges.open`
   - ALIGNMENT frontmatter `verdict` / `alignment_iteration`; счётчик
     critical/major mismatch-строк
   - `needs_check_feature` (+ reason) — алгоритм из `routing_conditions.yaml`
     (включая run-log; движок на hot path не пересчитывает)
   - `stale` / `alignment_stale` — mtime (движок всё равно пересчитает)
   Не выдумывай id. Не заполняй ключи роутера.
4. Запиши JSON: `schema_version: 1`, `slug`, `generated_at` (UTC ISO), `fields`.
5. Краткий отчёт: путь, число `open_gaps`, needs-answer, stale-триггер.
   Не называй следующий шаг пайплайна.

## Запреты

- Не вызывать `pipeline_dispatch.py` и не выбирать субагента.
- Не патчить `SPEC` / `DECISIONS` / отчёты / maps.
- Не класть в `fields` ключи роутера (`next_step`, `ready`, `orchestrator_mode`, …).

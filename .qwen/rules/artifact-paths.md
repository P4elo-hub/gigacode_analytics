---
description: Canonical artifact paths for feature analytics — single source of truth
alwaysApply: true
---
# Artifact paths (canonical)

Единственный источник истины по путям артефактов. Скиллы и команды ссылаются на
**токены** из этой таблицы, а не повторяют пути.

## Папка фичи

Один `<slug>` = одна папка. Все артефакты фичи лежат **внутри** неё.

```
Feature-writing/<slug>/
  <slug>.md                        ← SPEC (финальная спецификация)
  <slug>-decisions.md              ← DECISIONS (ответы пользователя)
  <slug>-code-alignment.md         ← ALIGNMENT
  <slug>-gaps-resolved.md          ← GAPS_MAP
  <slug>-challenges.md             ← CHALLENGES
  <slug>-challenges-resolved.md    ← CHALLENGES_MAP
  <slug>-routing-state.json        ← ROUTING_STATE (Phase 12 live overlay)
  <slug>.part-<block_id>.md        ← рабочий фрагмент write-feature
  <slug>.context.md                ← рабочий накопленный контекст блоков
Feature-context/
  <slug>.md                        ← CONTEXT_DOC
  <slug>-discovery.md              ← рабочий пакет find-context
agent-logs/
  <slug>/
    manifest.json                  ← AGENT_MANIFEST
    runs/run-NNN/
      events.jsonl                 ← AGENT_EVENTS
      metrics.json                 ← AGENT_METRICS
      anomalies.md                 ← AGENT_ANOMALIES
      run-log.jsonl                ← AGENT_RUN_LOG
      telemetry-analysis.md        ← AGENT_TELEMETRY_ANALYSIS
```

Сырые логи CLI (jsonl `~/.qwen/` / `~/.qwen/`, SQLite OpenCode) ingest
копирует опционально в
`runs/run-NNN/raw/`. Субагенты пайплайна логи **не** пишут — только
`scripts/ingest_session_telemetry.py` и `append_run_log.py` (оркестратор).

## Токены

| Токен | Путь | Создаёт | Правит |
|-------|------|---------|--------|
| `FEATURE_DIR` | `Feature-writing/<slug>/` | `/write-feature` | — |
| `SPEC` | `FEATURE_DIR<slug>.md` | `/write-feature` | check-feature, все resolve-* |
| `DECISIONS` | `FEATURE_DIR<slug>-decisions.md` | оркестратор + resolve-* | оркестратор (Decision/Status), resolve-* (строки) |
| `CONTEXT_DOC` | `Feature-context/<slug>.md` | `/find-context` | resolve-* (только § закрытых Q) |
| `ALIGNMENT` | `FEATURE_DIR<slug>-code-alignment.md` | `/check-feature-code` | resolve-code-alignment (log) |
| `GAPS_MAP` | `FEATURE_DIR<slug>-gaps-resolved.md` | `/resolve-gaps` | `/resolve-gaps` |
| `CHALLENGES` | `FEATURE_DIR<slug>-challenges.md` | `/challenge-feature` | resolve-challenges (статусы) |
| `CHALLENGES_MAP` | `FEATURE_DIR<slug>-challenges-resolved.md` | `/resolve-challenges` | `/resolve-challenges` |
| `ROUTING_STATE` | `FEATURE_DIR<slug>-routing-state.json` | `/analyze-routing` (spec graph) | `routing-analyzer` |
| `AGENT_LOGS` | `agent-logs/<slug>/` | `/archive-session`, ingest | ingest, analyze-telemetry |
| `AGENT_MANIFEST` | `AGENT_LOGS/manifest.json` | ingest | ingest |
| `AGENT_EVENTS` | `AGENT_LOGS/runs/<run-id>/events.jsonl` | ingest | ingest |
| `AGENT_METRICS` | `AGENT_LOGS/runs/<run-id>/metrics.json` | ingest | ingest |
| `AGENT_ANOMALIES` | `AGENT_LOGS/runs/<run-id>/anomalies.md` | ingest | analyze-telemetry |
| `AGENT_RUN_LOG` | `AGENT_LOGS/runs/<run-id>/run-log.jsonl` | оркестратор | оркестратор |
| `AGENT_TELEMETRY_ANALYSIS` | `AGENT_LOGS/runs/<run-id>/telemetry-analysis.md` | analyze-telemetry | analyze-telemetry |
| `CALIBRATION` | `Calibration/<slug>/` | `/snapshot-baseline`, calibrate | calibrate-* |
| `CAL_BASELINE` | `CALIBRATION/runs/<run-id>/baseline/` | snapshot-baseline | — |
| `CAL_GOLD` | `CALIBRATION/runs/<run-id>/gold/` | capture-review (sync) | — |
| `CAL_REVIEW` | `CALIBRATION/runs/<run-id>/review/` | capture-review, analyze-delta | calibrate agents |
| `CAL_CONTEXT_GAPS` | `CAL_REVIEW/context-gaps.md` | analyze-delta | user backlog (analytics/repo) |
| `CAL_PROPOSALS` | `CALIBRATION/runs/<run-id>/proposals/` | propose-calibration | apply-calibration |
| `CAL_RERUN` | `CALIBRATION/runs/<run-id>/rerun/` | benchmark-rerun | benchmark session |

Калибровка — **отдельный** контур (`CALIBRATION.md`, `calibration-orchestrator`).
Не смешивать с `spec-orchestrator` без явной команды `/calibrate`.

## Правила

1. **Имя файла содержит `<slug>`** — папка группирует, префикс сохраняет
   уникальность в табах IDE и при grep.
2. **Ничего не создавать** в `Feature-writing/` вне `FEATURE_DIR` (кроме `README.md`).
3. Рабочие файлы (`*.part-*.md`, `*.context.md`) **удаляет** успешный
   `write_feature.py --mode assemble --out`. Неполный assemble (нет фрагмента)
   их не трогает. `*-discovery.md` удаляет find-context после записи
   `CONTEXT_DOC`.
4. `SPEC` — **чистый документ требований**: без журналов решений, без
   `[GAP-...]` / `[CH-...]` для закрытых пунктов. Метаинформация — в `DECISIONS`
   и `*_MAP` файлах.
5. После `/resolve-*` скрипт `scripts/refresh_context.py` дописывает в
   `CONTEXT_DOC` подраздел «Актуализация после resolve» внутри § «Что учесть».
   Остальной current-state не переписывается.

## DECISIONS (ответы для Qwen Code)

Субагенты Qwen Code **не умеют** `ask_user_question`. Ответы живут в `DECISIONS`,
не в промпте и не в `SPEC`. Позже `resolve-gaps` / `resolve-challenges` /
`resolve-code-alignment` читают тот же файл и **не переспрашивают** id из
колонки Relates (`GAP-*`, `CH-*`, `Q-XX`).

Статусы: `needs-answer` (варианты готовы) → оркестратор спрашивает →
`pending-apply` → специалист патчит spec → `applied`.
Для Relates с `GAP-*` статус `deferred` запрещён: нет факта → вопрос,
ответ → маркер снят. `deferred` остаётся только для `CH-*`, если
пользователь явно отложил challenge.

```markdown
| ID | Relates | Prompt | Options | Decision | Status | Date |
|----|---------|--------|---------|----------|--------|------|
| D-01 | GAP-GOAL-01, Q-01 | … | A) …; B) … | B: … | pending-apply | 2026-09-09 |
```

1. Специалист пишет строки `needs-answer` (не спрашивает), возвращает id
   оркестратору. Дубликат той же Relates не создавать.
2. Оркестратор — единственный, кто зовёт `ask_user_question`; после ответов
   заполняет Decision и Status. Писать ему можно **только** `DECISIONS`.
3. Специалист применяет все `pending-apply`, ставит `applied`, снимает
   `[GAP-…]` батча. `deferred` для GAP не использовать.
4. Есть готовое Decision по Relates — применить или пропустить вопрос, не
   изобретать факт.


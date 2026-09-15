# Feature analytics workflow

Workspace for History Operations (SIHIST / ИО): write feature specifications from
analytics and code context. **Final artifact:** `Feature-writing/<slug>/<slug>.md`.

## Layout

| Path | Purpose |
|---|---|
| `analytics/` | Confluence exports, feature analytics (primary at find/write/check) |
| `db-export/` | DB exports and dictionaries |
| `repositories/` | Cloned service repos (read-only context for facts) |
| `Feature-context/` | Output of find-context |
| `Feature-writing/<slug>/` | **Feature folder — spec + all reports** |
| `kb-writing-kits/` | Methodology kits + `spec-catalog.yaml` (block list) |

Canonical paths and tokens (`SPEC`, `CONTEXT_DOC`, `DECISIONS`, `ALIGNMENT`,
`GAPS_MAP`, `CHALLENGES`, `CHALLENGES_MAP`): rule `artifact-paths`.

## Pipeline

One `<slug>` for the whole chain:

```
find-context → write-feature
 → check-feature → resolve-gaps
 → challenge-feature → resolve-challenges
 → check-feature-code ↔ resolve-code-alignment (≤3)
```

`feature-status` — read-only, вызывается в любой момент.

Оркестратор **сам** запускает следующий шаг. Не спрашивать «запускать X?».
Пауза только на `ask_user_question` по существу: набор блоков write-feature, нет
брифа, неоднозначный slug, строки `needs-answer` в `DECISIONS` (спрашивает
оркестратор, не субагент) — или жёсткий стоп (лимит alignment, отказ по правам).

Успешный assemble удаляет `*.part-*.md` и `*.context.md`.

| Step | Gate |
|---|---|
| **feature-status** | Дашборд: открытые пункты, verdict, устаревшие отчёты, **один** next step |
| **find-context** | Discovery + проверенный context doc |
| **write-feature** | Блочная spec в `Feature-writing/<slug>/<slug>.md` |
| **check-feature** | Ревизия doc (analytics, бриф); вызывается и после resolve-скиллов |
| **resolve-gaps** | Закрытие `[GAP-...]`: варианты в `DECISIONS`, патч spec |
| **challenge-feature** | Критик spec: corner cases → `-challenges.md` |
| **resolve-challenges** | Закрытие `CH-*` из `DECISIONS` + поиск, правка spec |
| **check-feature-code** | Аудит vs `repositories/`; max **3** прогонов |
| **resolve-code-alignment** | Закрытие closable gaps из code-alignment через `DECISIONS` |
| **archive-session** | Ingest CLI jsonl → `agent-logs/<slug>/` (оркестратор после каждого step) |
| **analyze-telemetry** | Разбор anomalies / skill repeats → `telemetry-analysis.md` |
| **snapshot-baseline** | Заморозка SPEC → `Calibration/.../baseline/` |
| **capture-review** → **calibrate** | Human review, delta, proposals (`CALIBRATION.md`) |
| **benchmark-rerun** | Изолированный прогон в новой сессии |
| **Завершение** | `verdict: PASS` или `PASS WITH GAPS` без Critical/Major MISMATCH |

- **code-alignment** → doc: MISMATCH → fix; NOT FOUND для TO BE — ожидаемо до реализации
- `[GAP-...]` в spec — закрывать через `/resolve-gaps` или вручную; не выдумывать факты

## Маршрутизация и петли

**Next step** считает только `pipeline_delegate.py` (внутри `feature_status`).
Нет `routing-state.json` → `analyze-routing` (P5), затем domain-шаги.
JSON устарел/битый (после mutating-шага) → снова `analyze-routing`.
Check-feature без правок файлов → хук stamp в JSON, не анализатор.
`analyze-routing` — внутренний refresh JSON, только когда spec уже есть и
routing-state устарел/битый. Петли resolve → check, alignment ↔ code-audit,
one-pass challenge — в скрипте и `scripts/pipeline_schema.json`.

`CHALLENGES` старше `SPEC` после apply — **информационно** (mtime), не триггер
re-challenge. Повторный `/challenge-feature` — только по явной команде пользователя.

Устаревание по mtime: `ALIGNMENT` старше `SPEC` → stale (блокер для code audit).
`python3 scripts/feature_status.py <slug>` — read-only дашборд для человека.

## Обратная связь в context-doc

Все `/resolve-*` дописывают закрытые `Q-XX` в `CONTEXT_DOC` секцию
`## Закрытые вопросы` (ID, дата, решение, § spec, источник). Строки из
«Открытые вопросы» **не** удаляются — история сохраняется. После сессии
resolve запускай `python3 scripts/refresh_context.py <slug>`: скрипт
обновляет только § «Что учесть» (якоря и решения), current-state не трогает.

## Чистая spec

`SPEC` — документ требований. Ответы пользователя — в `DECISIONS`; журналы и
карты закрытий — в `GAPS_MAP`, `CHALLENGES_MAP`, log в `ALIGNMENT`, не в spec.
Закрытый пункт удаляется из spec целиком, а не помечается «закрыт».

## Traceability in feature spec

- Business rules: `BR-01`, `BR-02`, …
- Constraints: `CN-01`, …
- Gaps: `GAP-...` in gap tables
- Challenges: `CH-NN` в `CHALLENGES` (не в spec)
- Open questions: `Q-01`, … в context doc

## Commands

Слэш-команды: `.qwen/commands/` — `/feature-status`, `/find-context`,
`/write-feature`, `/check-feature`, `/resolve-gaps`, `/challenge-feature`,
`/resolve-challenges`, `/check-feature-code`, `/resolve-code-alignment`,
`/archive-session`, `/analyze-telemetry`, `/snapshot-baseline`, `/calibrate`,
`/capture-review`, `/analyze-delta`, `/propose-calibration`, `/apply-calibration`,
`/benchmark-rerun`.

Каждая команда запускает сабагент из `.qwen/agents/`. `/write-feature`
идёт в оркестратор: план → уточнение блоков у пользователя → `spec-writer`
на каждый блок (задание из плана целиком + `check-part`) → assemble (чистка рабочих файлов) → сразу
`check-feature`.

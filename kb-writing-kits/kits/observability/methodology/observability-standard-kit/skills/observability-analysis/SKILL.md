<!--
Imported from: observability-standard-kit/skills\observability-analysis\SKILL.md
Current-state adaptation:
- Use only confirmed current behavior.
- Do not write TO BE, rollout/rollback, future requirements, design proposals, GAP/ASM/DESIGN markers as reader-facing content.
- Put unresolved or future/change-specific material into working-layer gaps, not into permanent KB pages.
-->
---
name: observability-analysis
description: Analyzes and documents current-state functionality logging and metrics (Prometheus, UI analytics, structured JSON logs) using observability-standard-kit. Use when describing eventType, integration logs, business/system journals, technical/error/business/frontend metrics.
disable-model-invocation: true
---

# Observability Analysis

## Purpose

Document **logging** (§8.1) and **metrics** (§8.2) for a current-state functionality. Two separate artifacts (recommended) or one combined page.

Final artifacts:

- `#### Логирование — <Название фичи>`
- `#### Метрики — <Название фичи>`

Rules:

- No `СТД-*` in reader-facing text.
- No `Пример:` in titles.
- Do not copy transfer canonical example rows for unrelated current-state functionalitys without evidence or mode B.

## Required Files

| Domain | Spec | Template | Example | Gate |
|---|---|---|---|---|
| Clarification | `spec-kit/observability-clarification.schema.yaml` | `templates/observability-clarification-questionnaire.template.md` | — | `OBS-GATE-000` |
| Umbrella | `spec-kit/observability-page.schema.yaml` | — | — | `observability-review.yaml` |
| Логирование | `spec-kit/logging.schema.yaml` | `templates/logging.template.md` | `examples/account-transfer-logging-example.md` | `logging-review.yaml` |
| Метрики | `spec-kit/metrics.schema.yaml` | `templates/metrics.template.md` | `examples/account-transfer-metrics-example.md` | `metrics-review.yaml` |

## Instructions

0. **Clarification-first (hard stop)** — read `observability-clarification.schema.yaml` and `templates/observability-clarification-questionnaire.template.md`.

   **Первый ответ пользователю при новой фиче:**
   - выдать **только** опросник (таблицы LOG-Q / METR-Q + выбор режима A/B/C/D);
   - сохранить копию в `08-Observability/<current-state functionality-slug>-clarification.md`;
   - можно перенести в опросник **только** факты из постановки/NFR без маркеров DESIGN — в блок «Контекст из постановки», колонку «Ваш ответ» оставить пустой для неясного.

   **Запрещено до ответа пользователя:**
   - писать `#### Логирование — [название области]` / `#### Метрики — [название области]` в `08-Observability/`;
   - заполнять `eventType`, имена Prometheus, UI-события как утверждённые факты.

   **Исключения (можно писать артефакты сразу):**
   - пользователь приложил **заполненный** `-clarification.md` или ответы в чате по всем строкам;
   - пользователь явно выбрал **режим B** («спроектируй с нуля») в **этом** сообщении;
   - пользователь написал «по опроснику напиши» / «сгенерируй по ответам» после заполнения.


1. Classify domains: logging only / metrics only / both.

2. Collect evidence: existing log samples, dashboards, Prometheus rules, analytics spec, integration contracts.

3. Write logging artifact (if in scope) — sections per `logging.schema.yaml` and canonical example order.

4. Write metrics artifact (if in scope) — technical → errors → business → frontend subsections.

5. **Assumption and Gap Registry** (mandatory before gates) — same algorithm as `nfr-standard-kit`:

   - Column **«Статус»** on event/metric/field rows.
   - Section **Gaps и допущения** at bottom of **each** file; every ID in body ↔ row in Gaps.
   - Forbidden: inventing `eventType`, metric names, or integration log rows without marker.

6. Run `observability-review.yaml`, then domain gates.

## Logging checklist

- [ ] Log levels table (ERROR, WARN, INFO, DEBUG)
- [ ] Events table: journal type, level, eventType/callType/exSystem, init rules
- [ ] Automatic fields table (`@timestamp`, `callid`, …)
- [ ] Application fields table (`eventType`, `rqStr`, `rsStr`, …)
- [ ] Each integration/business event from current-state functionality scope has a row or explicit GAP

## Metrics checklist

- [ ] Technical Prometheus metrics with labels
- [ ] Error counters per failure type
- [ ] Business metrics with formulas
- [ ] Frontend events table with nested parameters; Event_duration intervals when applicable

## Assumption and Gap Registry


- [ ] No bare facts for eventType/metric names user did not confirm
- [ ] Gaps section synced with inline markers
- [ ] Blockquote at top points to Gaps table

## Domain hints

| User wording | Open |
|--------------|------|
| логи, eventType, журнал, rqStr | logging |
| Prometheus, метрики, дашборд, Grafana | metrics |
| аналитика, клик, экран | metrics → frontend |
| история событий, External Source, интеграция | logging → integration journal rows |

## Output paths

```text
08-Observability/logging.md
08-Observability/metrics.md
```

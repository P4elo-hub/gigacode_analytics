---
name: analyze-delta
description: Run spec delta script and enrich with root-cause themes.
user-invocable: false
---

# analyze-delta

## Шаги

1. `python3 scripts/analyze_spec_delta.py <slug>`
2. `python3 scripts/analyze_context_gaps.py <slug>` — scaffold `context-gaps.md`
3. Прочитай `delta-analysis.md`, `delta-summary.json`, `human-review.md`, `context-gaps.json`.
4. **Обогати** `context-gaps.md` для каждого `CTX-GAP-*`:
   - `why_agent_could_not_know` — 1–3 предложения, ссылка на отсутствующий источник;
   - уточни `suggested_remediation` (конкретный repo, файл analytics, § context-doc);
   - если пользователь назвал модуль/страницу в чате — зафиксируй.
5. Допиши в конец `delta-analysis.md` секцию **Root cause map**:

| REV / Section | Cause | Likely skill | Source gap (CTX-GAP) | Process gap |
|---------------|-------|--------------|----------------------|-------------|

- **Cause**: `context-gap` | `skill-gap` | `hybrid` | `unclear`
- Строки с `context-gap` **не** превращай в PROP-* — только CTX-GAP + remediation
- Строки с `skill-gap` → кандидаты для `propose-calibration` (PROP-*)

6. Свяжи с `agent-logs/.../anomalies.md` если есть.

## Запреты

- Не патчить spec/skills.
- Не создавать PROP-* для context-gap (только CTX-GAP + backlog remediation).

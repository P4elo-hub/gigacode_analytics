---
name: propose-calibration
description: Draft skill/process proposals from delta + telemetry (no apply).
user-invocable: false
---

# propose-calibration

## Вход

- `Calibration/.../review/delta-analysis.md`
- `Calibration/.../review/human-review.md`
- `Calibration/.../review/context-gaps.md`
- `agent-logs/.../telemetry-analysis.md` или `anomalies.md`

## Выход

`Calibration/<slug>/runs/<run-id>/proposals/proposals.md`:

```markdown
| ID | Theme | Target | Level | Risk | Status |
|----|-------|--------|-------|------|--------|
| PROP-01 | skill.repeat | .opencode/skills/use-case-analysis/SKILL.md | L1 | low | needs-answer |
```

И файлы `PROP-01.md` с: Problem, Proposed change (diff или текст), Rationale.

Status: `needs-answer` → пользователь → `approved` | `rejected` | `deferred`.

## Context gaps vs proposals

**CTX-GAP-*** уже в `context-gaps.md` — это **не** skill-патчи.

| Тип | Артефакт | Действие пользователя |
|-----|----------|------------------------|
| context-gap | `CTX-GAP-*` | Дописать analytics / clone repo / context-doc / метка в коде |
| skill-gap | `PROP-*` | Approve → `/apply-calibration` |

Правила разделения:

- REV/cause = `context-gap` → **не** создавай PROP для того же пункта
- `SKILL-CAND-*` из context-gaps → кандидаты PROP-*
- Max 5 proposals за run (только skill/process)
- L3 kits — только если delta critical
- **Не apply** — только proposals

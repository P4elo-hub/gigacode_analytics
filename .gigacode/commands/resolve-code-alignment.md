---
description: Закрыть closable gaps из отчёта code-alignment через опрос
---

Делегируй субагенту `alignment-resolver` через инструмент `task`:
- `subagent_type`: `alignment-resolver`
- `run_in_background`: false
- в prompt передай это задание, slug и путь `DECISIONS`

Сам `SPEC` не правь. Скилл: `.gigacode/skills/resolve-code-alignment/SKILL.md`.

Субагент не спрашивает: пишет `needs-answer` в `DECISIONS` или применяет
`pending-apply`. Готовые Decision по Relates не переспрашивать.

После `ASK_PARENT`: ты зовёшь `ask_user_question`, пишешь Decision в
`DECISIONS`, снова `task alignment-resolver`.

NOT FOUND для TO BE не спрашивай. `verdict` во frontmatter не меняй.

Фича (slug) или путь к отчёту code-alignment: {{args}}

## После шага — продолжай пайплайн

Когда субагент **поправил** spec, не жди `/check-feature-code`. Сразу
`task code-auditor` (`run_in_background: false`), затем снова
`feature_status.py`. Не спрашивай «запускать X?».

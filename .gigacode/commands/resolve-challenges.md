---
description: Закрыть вопросы CH-* из банка challenges и поправить спецификацию
---

Делегируй субагенту `challenge-resolver` через инструмент `task`:
- `subagent_type`: `challenge-resolver`
- `run_in_background`: false
- в prompt передай это задание, slug и путь `DECISIONS`

Сам `SPEC` не правь. Скилл: `.qwen/skills/resolve-challenges/SKILL.md`.

Сначала сверка с `DECISIONS`: `CH-*` / `Q-XX` с готовым Decision не
переспрашивать. Нет ответа — субагент пишет `needs-answer` и `ASK_PARENT`.

Тогда ты: `ask_user_question` по этим `D-*`, запиши Decision в `DECISIONS`,
снова `task challenge-resolver` на apply.

В банке меняй только колонку «Статус». Карта — `<slug>-challenges-resolved.md`.

Фича (slug), опционально список конкретных CH: {{args}}

## После шага — продолжай пайплайн

Когда субагент **применил** ответы (не после `ASK_PARENT`), сразу:
`python3 scripts/pipeline_delegate.py <slug> --cli gigacode --pipeline spec-v2` → `task` на `task.subagent_type` из JSON
(`run_in_background: false`). Не спрашивай «запускать X?».

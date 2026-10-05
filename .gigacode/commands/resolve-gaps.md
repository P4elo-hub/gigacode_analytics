---
description: Интерактивно закрыть открытые [GAP-...] в спецификации
---

Делегируй субагенту `gap-resolver` через инструмент `task`:
- `subagent_type`: `gap-resolver`
- `run_in_background`: false
- в prompt передай это задание, slug и путь `DECISIONS`

Сам `SPEC` не правь. Скилл: `.qwen/skills/resolve-gaps/SKILL.md`.

Субагент **не спрашивает** пользователя. Он пишет варианты в
`Feature-writing/<slug>/<slug>-decisions.md` и возвращает `ASK_PARENT`.

Тогда ты (оркестратор): прочитай `needs-answer`, вызови `ask_user_question`,
запиши Decision и Status `pending-apply` или `deferred` **только** в
`DECISIONS`, сразу снова `task gap-resolver` на apply.

Повторно не спрашивай Relates, где Decision уже есть. Карта закрытий —
`<slug>-gaps-resolved.md`, закрытые `Q-XX` — в контекст-документ.

Фича (slug), опционально список конкретных GAP или Q: {{args}}

## После шага — продолжай пайплайн

Когда субагент **применил** ответы (не после `ASK_PARENT`), сразу:
`python3 scripts/pipeline_delegate.py <slug> --cli gigacode --pipeline spec-v2` → `task` на `task.subagent_type` из JSON
(`run_in_background: false`). Не спрашивай «запускать X?».

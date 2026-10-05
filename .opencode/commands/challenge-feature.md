---
description: Критический разбор спецификации — corner cases и противоречия
---

Делегируй субагенту `spec-challenger` через инструмент `task`:
- `subagent_type`: `spec-challenger`
- `run_in_background`: false
- в prompt передай это задание и аргументы пользователя целиком

Сам работу шага не выполняй. Скилл субагента: `.qwen/skills/challenge-feature/SKILL.md`.

Проведи adversarial-разбор по скиллу `challenge-feature`: corner cases,
неучтённые alt-потоки, противоречия между BR, CN, use case и контрактами, дыры в
разделах, NFR и тестируемость.

Каждый вопрос — `CH-NN`, привязанный к § спецификации, с типом и severity. Банк
вопросов пиши только в `<slug>-challenges.md`, спецификацию не правь. Уже
закрытое в `DECISIONS`, `GAPS_MAP` и в § «Закрытые вопросы» заново не поднимай.

Фича (slug), опционально фокус по § или теме: {{args}}

## После шага — продолжай пайплайн

Когда субагент вернул результат, не жди новой слэш-команды. Сразу:
`python3 scripts/pipeline_delegate.py <slug> --cli opencode --pipeline spec-v2` → `task` на `task.subagent_type` из JSON
(`run_in_background: false`). Не спрашивай «запускать X?». Повторяй, пока
нет паузы по существу или verdict PASS / PASS WITH GAPS.

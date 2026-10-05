---
description: Ревизия и доказательная правка спецификации по источникам
---

Делегируй субагенту `spec-reviewer` через инструмент `task`:
- `subagent_type`: `spec-reviewer`
- `run_in_background`: false
- в prompt передай это задание и аргументы пользователя целиком

Сам работу шага не выполняй. Скилл субагента: `.qwen/skills/check-feature/SKILL.md`.

Проверь и поправь спецификацию по скиллу `check-feature`: сверка с постановкой и
контекст-документом, контракты поле за полем против `repositories/` и
`db-export/`, полнота §5.x и NFR, обход ссылок контекст-документа.

Правь **только** `SPEC`. Меняй лишь то, что подтверждено источником; не
подтверждается — `[GAP-...]`. Отчёты alignment и challenges не трогай.

Фича (slug), опционально приоритетные указания или alignment-focus: {{args}}

## После шага — продолжай пайплайн

Когда субагент вернул результат, не жди новой слэш-команды. Сразу:
`python3 scripts/pipeline_delegate.py <slug> --cli gigacode --pipeline spec-v2` → `task` на `task.subagent_type` из JSON
(`run_in_background: false`). Не спрашивай «запускать X?». Повторяй, пока
нет паузы по существу или verdict PASS / PASS WITH GAPS.

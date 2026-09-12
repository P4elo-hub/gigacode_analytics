---
description: Собрать проверенный контекст текущего состояния под бриф фичи
---

Делегируй субагенту `context-researcher` через инструмент `task`:
- `subagent_type`: `context-researcher`
- `run_in_background`: false
- в prompt передай это задание и аргументы пользователя целиком

Сам работу шага не выполняй. Скилл субагента: `.qwen/skills/find-context/SKILL.md`.

Собери контекст-документ по скиллу `find-context`: discovery по `analytics/`,
`Feature-writing/`, `repositories/`, `db-export/`, подтверждение каждого факта
открытием файла с фиксацией пути и якоря, затем запись
`Feature-context/<slug>.md`.

Непроверенное оставляй как `Q-XX` с колонкой «Где искать ответ». Решение не
проектируй — это документ текущего состояния.

Бриф фичи: {{args}}

## После шага — продолжай пайплайн

Когда `context-researcher` записал `CONTEXT_DOC`, не жди `/write-feature`.
Сразу оркестраторский цикл write-feature (план → вопрос по блокам →
`spec-writer` по одному блоку → assemble → `spec-reviewer`), затем
`pipeline_delegate.py` и следующий `task` из JSON. Не спрашивай «запускать X?».

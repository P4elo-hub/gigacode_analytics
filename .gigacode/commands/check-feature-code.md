---
description: Аудит спецификации против фактического кода в repositories/
---

Делегируй субагенту `code-auditor` через инструмент `task`:
- `subagent_type`: `code-auditor`
- `run_in_background`: false
- в prompt передай это задание и аргументы пользователя целиком

Сам работу шага не выполняй. Скилл субагента: `.qwen/skills/check-feature-code/SKILL.md`.

Сверь спецификацию с кодом по скиллу `check-feature-code`: реестр утверждений из
документа, поиск подтверждений в `repositories/`, классификация находок как
CONFIRMED / MISMATCH / PARTIAL / NOT FOUND / UNVERIFIABLE со severity.

Код — источник истины; подтверждение только с путём к файлу и фрагментом.
Полный отчёт пиши в `<slug>-code-alignment.md`, в чат — краткая сводка.
Спецификацию и код не правь. Лимит — 3 прогона.

Фича (slug), опционально приоритетные области проверки: {{args}}

## После шага — продолжай пайплайн

Когда субагент вернул `ALIGNMENT`, не жди новой слэш-команды. Сразу:
`python3 scripts/pipeline_delegate.py <slug> --cli gigacode --pipeline spec-v2` → `task` на `task.subagent_type` из JSON
(`run_in_background: false`). FAIL с closable gaps → `alignment-resolver`,
затем снова `code-auditor`. Не спрашивай «запускать X?».

---
name: apply-calibration
description: Apply only approved rows from proposals.md to target skills.
user-invocable: false
---

# apply-calibration

## Шаги

1. Прочитай `proposals/proposals.md`.
2. Только строки `Status = approved`.
3. L1: правь `.opencode/skills/` (зеркало `.gigacode/` / `.qwen/` — только если явно просили).
4. L2 kits: только при явном approve в чате + deny settings учитывай.
5. После apply — смени Status на `applied`, дата.

## Запреты

- `rejected` / `deferred` / `needs-answer` — не трогать.
- Не apply без approved в таблице.

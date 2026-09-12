---
name: observability-analysis
description: >-
  Пишет §5.3.1 логи и §5.3.2 метрики. Форма — observability-standard-kit.
user-invocable: false
disable-model-invocation: true
---

# observability-analysis

Маршрут блока `observability`. Форма — kit.

База: `kb-writing-kits/kits/observability/methodology/observability-standard-kit/`

Skill kit: `skills/observability-analysis/SKILL.md`

| Роль | Logging | Metrics |
|------|---------|---------|
| Template | `templates/logging.template.md` | `templates/metrics.template.md` |
| Example | `examples/account-transfer-logging-example.md` | `examples/account-transfer-metrics-example.md` |
| Gate | `quality-gates/logging-review.yaml` | `quality-gates/metrics-review.yaml` |

1. Прочитай skill kit, оба template, оба example и оба gate **целиком**.
2. Пиши ровно по ним (`#### 5.3.1` и `#### 5.3.2`).
3. Нет факта → `[GAP-...]`. Верни только Markdown блока `observability`.

---
name: threat-model-analysis
description: >-
  Пишет модель угроз. Форма — security-threat-model-kit.
disable-model-invocation: true
---

# threat-model-analysis

Маршрут блока `threat-model`. Форма — kit.

База: `kb-writing-kits/kits/security-threat-model/methodology/security-threat-model-kit/`

| Роль | Путь от базы |
|------|----------------|
| Skill kit | `skills/threat-model-analysis/SKILL.md` |
| Template | `templates/threat-model.template.md` |
| Example | `examples/bph-getlink-events-threat-model-example.md` |
| Gate | `quality-gates/threat-model-review.yaml` |

1. Прочитай skill kit, template, example и gate **целиком**.
2. Пиши ровно по kit.
3. Нет факта → `[GAP-...]`. Верни только Markdown блока `threat-model`.

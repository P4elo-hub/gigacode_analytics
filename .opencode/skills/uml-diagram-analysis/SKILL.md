---
name: uml-diagram-analysis
description: >-
  Пишет UML AS IS / TO BE / sequence. Форма — uml-diagram-standard-kit.
disable-model-invocation: true
---

# uml-diagram-analysis

Маршрут диаграмм. Только если скилл в колонке плана
(`1.2-diagram`, `1.3-diagram`, `3.2`). Форма — kit.

База: `kb-writing-kits/kits/uml-diagram/methodology/uml-diagram-standard-kit/`

| Роль | Путь от базы |
|------|----------------|
| Skill kit | `skills/uml-diagram-analysis/SKILL.md` |
| Template | `templates/sequence-diagram.template.md` |
| Example | `examples/sequence-diagram-example.md` |
| Gate | `quality-gates/sequence-diagram-review.yaml` |

1. Прочитай skill kit, template, example и gate **целиком**.
2. Пиши ровно по kit.
3. Нет факта → `[GAP-...]`. Верни только Markdown блока `uml-diagram`.

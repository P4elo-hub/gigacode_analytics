---
name: architecture-analysis
description: >-
  Пишет §3.1 / компоненты. Форма — architecture-standard-kit.
user-invocable: false
disable-model-invocation: true
---

# architecture-analysis

Маршрут блока `architecture`. Форма — kit.
Sequence §3.2 пишет `uml-diagram-analysis`, если он в колонке плана.

База: `kb-writing-kits/kits/architecture/methodology/architecture-standard-kit/`

| Роль | Файл |
|------|------|
| Skill kit | `skills/architecture-analysis/SKILL.md` |
| Template | `templates/architecture.template.md` |
| Example | `examples/operation-history-architecture-example.md` |
| Gate | `quality-gates/architecture-review.yaml` |

1. Прочитай skill kit, template, example и gate **целиком**.
2. Пиши ровно по kit. UML сам не вызывай.
3. Нет факта → `[GAP-...]`. Верни только Markdown блока `architecture`.

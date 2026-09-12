---
name: acceptance-test-analysis
description: >-
  Пишет приёмочные критерии. Форма — acceptance-test-standard-kit.
disable-model-invocation: true
---

# acceptance-test-analysis

Маршрут блока `acceptance`. Форма — kit.

База: `kb-writing-kits/kits/acceptance-checks/methodology/acceptance-test-standard-kit/`

| Роль | Путь от базы |
|------|----------------|
| Skill kit | `skills/acceptance-test-analysis/SKILL.md` |
| Template | `templates/acceptance-tests.template.md` |
| Example | `examples/operation-sorting-acceptance-example.md` |
| Gate | `quality-gates/acceptance-tests-review.yaml` |

1. Прочитай skill kit, template, example и gate **целиком**.
2. Пиши ровно по kit.
3. Нет факта → `[GAP-...]`. Верни только Markdown блока `acceptance`.

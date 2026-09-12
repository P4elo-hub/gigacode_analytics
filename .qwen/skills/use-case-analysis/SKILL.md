---
name: use-case-analysis
description: >-
  Пишет Use Case AS IS / TO BE и алгоритм (4.2.2). Форма — use-case-standard-kit.
user-invocable: false
disable-model-invocation: true
---

# use-case-analysis

Маршрут блоков `usecase-as-is`, `usecase-to-be`, `algorithm`. Форма — только kit.

База: `kb-writing-kits/kits/use-case/methodology/use-case-standard-kit/`

| Роль | Путь от базы |
|------|----------------|
| Skill kit | `skills/use-case-analysis/SKILL.md` |
| Template | `templates/use-case.template.md` |
| Example | `examples/transfer-between-accounts-use-case-example.md` |
| Gate | `quality-gates/use-case-review.yaml` |

UML этот скилл **сам не вызывает**. Диаграмму пишет `uml-diagram-analysis`,
если он в колонке плана (`1.2-diagram` / `1.3-diagram`). Нет в плане — не пиши.

1. Прочитай skill kit, template, example и gate **целиком**.
2. Пиши ровно по kit. AS IS = как сейчас. TO BE = целевое. `algorithm` — §4.2.2
   по тому же kit, не копируй клиентский сценарий 1.3 слово в слово.
3. Нет факта → `[GAP-...]`. Верни только Markdown этого блока.

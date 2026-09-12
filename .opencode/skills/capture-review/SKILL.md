---
name: capture-review
description: Sync gold spec and capture human review themes after user edits.
user-invocable: false
---

# capture-review

После того как пользователь поправил `SPEC`.

## Шаги

1. `python3 scripts/sync_gold_spec.py <slug>`
2. Прочитай текущий `SPEC` и diff (если есть `delta-summary.json` — позже).
3. Запиши `Calibration/<slug>/runs/<run-id>/review/human-review.md`:

```markdown
# Human review — <slug>

## REV-01 — <краткий заголовок>
- section: …
- theme: missing-fact | wrong-structure | wording | scope | …
- cause: context-gap | skill-gap | hybrid | unclear
- comment: … (дословно из чата пользователя, если было)
- expected: …
- agent_had_source: yes | no | partial | unknown
```

### Поле `cause` (обязательно)

| Значение | Когда |
|----------|--------|
| **context-gap** | Агент **не мог** знать: факт не был в `analytics/`, `repositories/`, context-doc, брифе |
| **skill-gap** | Источник **был**, агент не нашёл / не применил |
| **hybrid** | Часть факта была, не хватало связки или модуля |
| **unclear** | Недостаточно данных — пометить, не выдумывать |

Если пользователь явно сказал «этого не было в аналитике / репозитории» — `context-gap`.
Если правка косметическая или структурная при полном контексте — `skill-gap`.

4. Темы из **комментариев пользователя в чате** + видимых правок. Не выдумывай.

## Запреты

- Не патчить `SPEC` и скиллы.
- Не удалять baseline.

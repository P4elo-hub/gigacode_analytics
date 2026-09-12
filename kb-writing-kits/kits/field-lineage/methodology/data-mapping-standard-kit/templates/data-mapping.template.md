<!--
Imported from: data-mapping-standard-kit/templates\data-mapping.template.md
Current-state adaptation:
- Use only confirmed current behavior.
- Do not write TO BE, rollout/rollback, future requirements, design proposals, GAP/ASM/DESIGN markers as reader-facing content.
- Put unresolved or future/change-specific material into working-layer gaps, not into permanent KB pages.
-->
#### Маппинг данных — [Название]

**Контекст маппинга:**

| Элемент | Значение |
|---|---|
| Фича | [Название] |
| Назначение маппинга | [Integration / migration / UI / analytics] |
| Связанные артефакты | [Integration/Data model/Requirements] |
| Статус | [draft / ready-for-review] |

**Source и Target:**

| Сторона | Система / модель | Контракт / версия | Owner |
|---|---|---|---|

**Field mapping:**

| Target field | Source path | Transformation | Required / nullable / default | Validation | Example | Статус |
|---|---|---|---|---|---|---|

**Enum / status mapping:**

| Source value | Target value | Условие / комментарий | Unknown behavior | Статус |
|---|---|---|---|---|

**Validation и rejection:**

| Условие | Поведение | Ошибка / событие | Статус |
|---|---|---|---|

**Примеры:**

```json
{
  "source": {
    "field": "value"
  },
  "target": {
    "field": "value"
  }
}
```

**Gaps и допущения:**

| ID | Где найдено | Что неизвестно / что предположено / что спроектировано | Как закрыть |
|---|---|---|---|

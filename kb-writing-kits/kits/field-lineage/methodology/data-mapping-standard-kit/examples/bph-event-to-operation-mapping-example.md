<!--
Imported from: data-mapping-standard-kit/examples\bph-event-to-operation-mapping-example.md
Current-state adaptation:
- Use only confirmed current behavior.
- Do not write TO BE, rollout/rollback, future requirements, design proposals, GAP/ASM/DESIGN markers as reader-facing content.
- Put unresolved or future/change-specific material into working-layer gaps, not into permanent KB pages.
-->
#### Маппинг данных — External Source GetEvents -> Operation History

**Контекст маппинга:**

| Элемент | Значение |
|---|---|
| Фича | Подключение External Source GetEvents |
| Назначение маппинга | Integration |
| Связанные артефакты | `04-Architecture/bph-getlink-events-architecture.md`, `04-Integrations/bph-getlink-events.md` |
| Статус | draft |

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
| Тип не торговая заявка | Не включать в историю | `bph_getlink_event_skipped` | Подтверждено ограничением фичи |

**Примеры:**

```json
{
  "source": {
    "id": "bph-123",
    "applicationType": "TRADE_ORDER",
    "createdAt": "2026-06-01T10:00:00Z"
  },
  "target": {
    "externalId": "bph-123",
    "type": "trade_order",
    "createdAt": "2026-06-01T10:00:00Z"
  }
}
```

**Gaps и допущения:**

| ID | Где найдено | Что неизвестно / что предположено / что спроектировано | Как закрыть |
|---|---|---|---|

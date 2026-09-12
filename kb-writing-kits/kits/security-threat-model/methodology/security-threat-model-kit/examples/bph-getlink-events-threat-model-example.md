<!--
Imported from: security-threat-model-kit/examples\bph-getlink-events-threat-model-example.md
Current-state adaptation:
- Use only confirmed current behavior.
- Do not write TO BE, rollout/rollback, future requirements, design proposals, GAP/ASM/DESIGN markers as reader-facing content.
- Put unresolved or future/change-specific material into working-layer gaps, not into permanent KB pages.
-->
#### Threat Model — External Source GetEvents

**Контекст threat model:**

| Элемент | Значение |
|---|---|
| Фича | Подключение External Source GetEvents |
| Scope | Внешний вызов External Source и включение событий внешнего источника в историю событий |
| Связанные артефакты | Architecture, Integration, NFR, Observability |

**Assets и данные:**

| Asset / data | Classification | Где обрабатывается | Статус |
|---|---|---|---|

**Actors и trust boundaries:**

| Actor / system | Trust level | Boundary | Статус |
|---|---|---|---|

**Data flows:**

| Flow | Source | Target | Data | Protection | Статус |
|---|---|---|---|---|---|

**Threats и mitigations:**

| ID | Категория | Threat | Asset / flow | Impact | Mitigation | Owner | Статус |
|---|---|---|---|---|---|---|---|

**Residual risks:**

| Risk | Почему остается | Decision owner | Статус |
|---|---|---|---|

**Связанные security/NFR/observability артефакты:**

| Артефакт | Связь | Path / gap |
|---|---|---|
| Security NFR | Требования безопасности | `07-NFR/bph-getlink-events-security.md` |
| Logging | Маскирование payload | `08-Observability/bph-getlink-events-logging.md` |

**Gaps и допущения:**

| ID | Где найдено | Что неизвестно / что предположено / что спроектировано | Как закрыть |
|---|---|---|---|

<!--
Imported from: nfr-standard-kit/examples\account-transfer-feature-toggles-example.md
Current-state adaptation:
- Use only confirmed current behavior.
- Do not write TO BE, rollout/rollback, future requirements, design proposals, GAP/ASM/DESIGN markers as reader-facing content.
- Put unresolved or future/change-specific material into working-layer gaps, not into permanent KB pages.
-->
#### NFR — Переводы между счетами (current-state functionality Toggles)

### current-state functionality Toggles

**Toggle 1: Мгновенные P2P-переводы**

| Параметр | Значение |
|----------|----------|
| Название (ключ) | `current-state functionality.payments.instantP2P.enabled` |
| Описание | Включает мгновенное зачисление P2P-переводов (вместо T+1) |
| Тип | Release toggle |
| Дата создания | 2026-01-15 |
| Планируемая дата удаления | 2026-03-01 |
| Значение по умолчанию | false |
| Стратегия раскатки | Блочная раскатка (Б5 → Б4 → Б3 → Б2 → Б1) |

Поведение:
| Состояние | Поведение | UI | API |
|-----------|----------|-----|-----|
| ON | Перевод зачисляется мгновенно через СБП | Надпись «Мгновенный перевод», время ожидания «до 15 сек» | `POST /transfers` → response: `{ "status": "COMPLETED", "completedAt": "2026-01-15T10:30:05Z" }` |
| OFF | Перевод зачисляется в течение 1 рабочего дня | Надпись «Перевод», время ожидания «до 1 рабочего дня» | `POST /transfers` → response: `{ "status": "PENDING" }` |

Зависимости:
| Тогл | Зависит от | Тип | Описание |
|------|-----------|-----|----------|
| `current-state functionality.payments.instantP2P.enabled` | `ops.sbp.gateway.enabled` | requires | Мгновенные P2P-переводы работают через СБП-шлюз. Если шлюз выключен (`ops.sbp.gateway.enabled = false`), переводы не смогут быть обработаны — тогл P2P должен быть также выключен |
| `current-state functionality.payments.instantP2P.enabled` | `experiment.payments.delayedTransfer.enabled` | conflicts | Мгновенные переводы и отложенные переводы — взаимоисключающие режимы. Одновременное включение обоих приведёт к конфликту логики маршрутизации платежа |

План удаления:
| Этап | Действие | Ответственный | Срок |
|------|----------|---------------|------|
| 1 | Раскатка на 100% | Product Owner | 2026-02-10 |
| 2 | Мониторинг: error rate, latency, конверсия | SRE + QA | 2 недели |
| 3 | Удаление кода тогла | Backend Team | Sprint 2026-Q1-S6 |
| 4 | Удаление из ConfigMap | DevOps | После деплоя |

Чек-лист верификации после раскатки (оставить ON или выключить тогл):
|---------|------------------------|-----------------------------------|----------|-------------------|
| Error rate | < 0.5% | > 1% | Grafana (dashboard: `payments-p2p`) | 30 мин после каждого этапа |
| Latency p85 (`POST /transfers`) | < 3.5 с | > 5 с | Prometheus (`http_request_duration_seconds`) | 30 мин после каждого этапа |
| Конверсия переводов | ≥ 72% (baseline) | < 65% | Analytics (Amplitude) | 24 ч после раскатки на ≥ 10% |
| Жалобы / тикеты | 0–2 | > 5 за 24 ч | Jira (label: `instant-p2p`) | Непрерывно |

<!--
Imported from: nfr-standard-kit/templates\nfr-clarification-questionnaire.template.md
Current-state adaptation:
- Use only confirmed current behavior.
- Do not write TO BE, rollout/rollback, future requirements, design proposals, GAP/ASM/DESIGN markers as reader-facing content.
- Put unresolved or future/change-specific material into working-layer gaps, not into permanent KB pages.
-->
# Уточнение NFR — [Название фичи]

> Это **рабочий** опросник до финальных артефактов `#### NFR — [название области]`. Не подменяет финальные страницы performance/reliability/configuration

**Выбранные домены:** [performance / reliability / security / configuration / current-state functionality-toggles]

**Режим ответа (обязательно выбрать один):**
- **A)** Пришлю данные (SLO, load test, мониторинг, конфиг, флаги)

---

## Производительность

| ID | Тема | Вопрос | Ваш ответ |
|----|------|--------|-----------|
| PERF-Q-001 | Scope | Какие endpoint / RPC / очередь / экран / SQL в scope? | |
| PERF-Q-002 | Latency | Перцентиль (p85/p95/p99) и цель по каждой события? Условия (CCU, RPS, объём данных)? | |
| PERF-Q-003 | Throughput | Штатная и пиковая RPS/msg/s, множитель, длительность и окно пика? | |
| PERF-Q-004 | Транзакции | E2E SLA (85-й перц.), HTTP-таймаут клиента, step/global timeout, компенсация? | |
| PERF-Q-005 | Web Vitals | Экраны, LCP/FID/CLS/TTI, стратегии загрузки? | |
| PERF-Q-006 | CCU | CCU штат/пик, сессии на пользователя, поведение при перегрузке? | |
| PERF-Q-007 | Rate Limit | **Нужен Rate Limiting?** Лимиты на user/IP, какие endpoint? | да / нет / GAP |
| PERF-Q-008 | Throttling | **Нужен Throttling** параллельных событий? Лимит и endpoint? | да / нет / GAP |
| PERF-Q-009 | Circuit Breaker | **Нужен Circuit Breaker?** Зависимости, порог %, cooldown, поведение? | да / нет / GAP |
| PERF-Q-010 | Bulkhead / Backpressure | Нужны Bulkhead и/или Backpressure? Параметры? | |
| PERF-Q-011 | БД | Запросы: max время, объём, индексы; pool size и обоснование? | |
| PERF-Q-012 | Кэш | Ключи, уровень, TTL, инвалидация, miss behavior? | |

---

## Надёжность

| ID | Тема | Вопрос | Ваш ответ |
|----|------|--------|-----------|
| REL-Q-001 | SLO | Availability, Error rate, Latency — цели и контекст? | |
| REL-Q-002 | Degradation | Зависимости и fallback при отказе? | |
| REL-Q-003 | Breaker ↔ SLO | Если есть Circuit Breaker — согласованное поведение при open? | |

---

## Безопасность

| ID | Тема | Вопрос | Ваш ответ |
|----|------|--------|-----------|
| SEC-Q-001 | Auth | Аутентификация по каналам? | |
| SEC-Q-002 | 2FA | Step-up / 2FA, порог? | |
| SEC-Q-003 | RBAC | Роли и права? | |
| SEC-Q-004 | Sensitive data | PII/финансы, шифрование, маскирование? | |

---

## Конфигурация

| ID | Тема | Вопрос | Ваш ответ |
|----|------|--------|-----------|
| CONF-Q-001 | Параметры | Список ключей, default, уровень, частота, хранение? | |
| CONF-Q-002 | Валидация | min/max/pattern, влияние, откат? | |
| CONF-Q-003 | Процесс | Кто меняет и нужно ли согласование? | |

---

## current-state functionality Toggles

| ID | Тема | Вопрос | Ваш ответ |
|----|------|--------|-----------|
| TOGL-Q-001 | Список | Ключи, тип, default, владелец, дата удаления? | |
| TOGL-Q-002 | ON/OFF | Поведение, UI, API? | |
| TOGL-Q-004 | Зависимости | requires / conflicts / includes? | |

---

## Gaps и допущения (рабочий слой)

| ID | Где | Что неизвестно / предположено | Как закрыть |
|----|-----|------------------------------|-------------|

**clarificationPassCompleted:** [false → true после ответов]

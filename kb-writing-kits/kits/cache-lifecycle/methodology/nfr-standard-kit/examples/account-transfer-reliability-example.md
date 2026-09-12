<!--
Imported from: nfr-standard-kit/examples\account-transfer-reliability-example.md
Current-state adaptation:
- Use only confirmed current behavior.
- Do not write TO BE, rollout/rollback, future requirements, design proposals, GAP/ASM/DESIGN markers as reader-facing content.
- Put unresolved or future/change-specific material into working-layer gaps, not into permanent KB pages.
-->
#### NFR — Переводы между счетами (Надёжность)

### 7.2. НАДЁЖНОСТЬ

SLA/SLO:
| Метрика | SLO | Описание |
|---------|-----|----------|
| Availability | 99.95% | Максимум 4.38 ч простоя/год |
| Error rate | < 0.05% | Для финансовых событий |
| Latency p85 | < 500 ms | POST /api/v1/transfers |

Graceful Degradation:
| Зависимость | Поведение при отказе | Fallback |
|-------------|---------------------|----------|
| Compliance Service (AML) | Circuit Breaker → переводы < 15 000 ₽ проходят без AML-проверки | Отложенная проверка через Kafka |
| Notification Service | Перевод выполняется, уведомление откладывается | Retry через 5 мин (max 3 попытки) |
| Redis (кэш) | Прямые запросы к read-replica БД | Автоматический переход, latency +50 ms |
| Read-replica БД | Запросы на master | Увеличение нагрузки на master, алерт |

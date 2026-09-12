<!--
Imported from: nfr-standard-kit/examples\account-transfer-configuration-example.md
Current-state adaptation:
- Use only confirmed current behavior.
- Do not write TO BE, rollout/rollback, future requirements, design proposals, GAP/ASM/DESIGN markers as reader-facing content.
- Put unresolved or future/change-specific material into working-layer gaps, not into permanent KB pages.
-->
#### NFR — Переводы между счетами (Конфигурация)

### Настройки и конфигурация

| Параметр | Тип | Уровень | Частота | Область | Хранение | По умолчанию | Описание | Валидация | Влияние при изменении | Процедура отката |
|----------|-----|---------|---------|---------|----------|-------------|----------|-----------|----------------------|------------------|
| `transfer.single.max` | integer | public | dynamic | global | ConfigMap | 1 000 000 | Макс. сумма одного перевода (₽) | min: 1 000, max: 50 000 000 | Ограничивает максимальную сумму одной события | Установить предыдущее значение в ConfigMap |
| `transfer.aml.threshold` | integer | internal | dynamic | global | ConfigMap | 15 000 | Порог AML-проверки (₽) | min: 0, max: 1 000 000 | Снижение → рост нагрузки на Compliance Service; повышение → пропуск проверок | Откат ConfigMap + мониторинг error rate Compliance Service |
| `transfer.2fa.threshold` | integer | internal | dynamic | global | ConfigMap | 50 000 | Порог 2FA-подтверждения (₽) | min: 0, max: 10 000 000 | Снижение → больше 2FA-запросов; повышение → снижение безопасности | Установить предыдущее значение в ConfigMap |
| `redis.cache.ttl.transfer` | integer | internal | dynamic | global | ConfigMap | 300 | TTL кэша перевода (сек) | min: 10, max: 3 600 | Снижение → больше запросов к БД; повышение → устаревшие данные в кэше | Установить предыдущее значение в ConfigMap |
| `circuit.compliance.threshold` | float | internal | dynamic | global | ConfigMap | 0.5 | Порог Circuit Breaker для AML | min: 0.1, max: 1.0 | Снижение → Circuit Breaker срабатывает чаще; повышение → позднее обнаружение отказа | Установить предыдущее значение, проверить состояние Circuit Breaker |
| `current-state functionality.p2p.instantTransfer.enabled` | boolean | public | runtime | env | БД | false | Мгновенные P2P-переводы | true / false | ON → мгновенные переводы через СБП; OFF → возврат к T+1 | Установить false в БД (эффект мгновенный, без перезапуска) |

# Kit: Cache Lifecycle

## Назначение

Для кэшей, временного состояния, пагинационных snapshots и повторного использования данных между запросами.

## Reader-first обязательство

Применяй этот kit только вместе с `10-Governance/reader-first-writing-standard.md`. Постоянная страница сначала объясняет читателю назначение, участников, вход, результат и текущее поведение простым языком. Технические имена допустимы только после пояснения их роли; если на странице больше трех технических названий, добавь раздел `Как читать технические названия`.
## Evidence pack

- Cache name или storage.
- Key.
- Value payload.
- Writers и readers.
- TTL/invalidation или gap.
- Hit/miss behavior.
- Error behavior.
- Связь с use case, пагинацией, деталкой или интеграцией.

Для deep-detail intent `cache-key-ttl-invalidation-lifecycle` evidence pack дополнительно должен собрать:

- key schema и состав ключа;
- value payload и границы сериализации/агрегации;
- lifecycle: создание, чтение, обновление, invalidation, eviction и cleanup;
- TTL и runtime override только при наличии config/code evidence;
- hit/miss behavior и fallback к источнику;
- consistency risks и связь с пагинацией, деталкой или повторным запросом.

## Постоянная страница

Нужны назначение кэша, что хранится, ключ и жизненный цикл, кто пишет и читает, hit/miss, ошибки, ограничения и связанные сценарии.

Если TTL, invalidation или eviction не найдены, не записывай предполагаемое значение: оставь подтвержденный lifecycle и gap в `kb-page-plan.md`.
## Полный методологический слой

Этот kit использует не только краткий checklist выше. В подпапке methodology/ лежат адаптированные материалы исходных feature methodology kits: README, templates, schemas, quality gates, examples и skill-инструкции.

При выполнении команд 12, 13 и 14 агент должен читать эти материалы как расширенный профиль kit-а и применять их к current-state базе знаний.

Подключенные source kits:

- methodology/nfr-standard-kit/

Правило адаптации: использовать все требования к структуре, детализации, примерам, матрицам, диаграммам, проверкам и evidence, но не переносить в постоянную страницу future/change-management слой: TO BE, rollout/rollback, будущие требования, design proposals, GAP-*, ASM-*, DESIGN-* как читательский текст. Такие элементы фиксируются только в рабочем слое как gaps или не используются.

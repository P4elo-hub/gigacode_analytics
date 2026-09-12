# Kit: Integration

## Назначение

Для взаимодействия с внешней системой, внутренним сервисом, брокером сообщений, файловым/batch контуром, webhook/callback, CDC/outbox/inbox, external SDK/API client или другим integration point: участники, направление обмена, маппинг данных и поведение при сбоях.

## Reader-first обязательство

Применяй этот kit только вместе с `10-Governance/reader-first-writing-standard.md`. Постоянная страница сначала объясняет читателю назначение, участников, вход, результат и текущее поведение простым языком. Технические имена допустимы только после пояснения их роли; если на странице больше трех технических названий, добавь раздел `Как читать технические названия`.
## Evidence pack

- Consumer и provider.
- Направление обмена.
- Protocol, endpoint/RPC/route/topic/queue/file/webhook/CDC stream/native protocol.
- Request/response/event/file mapping.
- Authentication/session/security context.
- Timeout, retry, fallback, degradation, если подтверждены.
- Ошибки и влияние на сценарий.
- Настройки интеграции, включая channel/client/storage/runtime properties, если они есть.
- Logging, metrics, tracing.
- PlantUML sequence diagram.

Для deep-detail страниц интеграционный kit дополнительно требует:

- source priority или fallback order, если интеграция конкурирует с другим источником данных;
- timeout/retry/degradation только по code/config/test evidence;
- request/response/event/file field mapping до internal model или downstream response;
- runtime target values только по production config/deployment evidence;
- явные gaps для external provider behavior, который не подтвержден доступными источниками.

## Постоянная страница

Нужны назначение интеграции, участники, ответственность, сценарии обмена, контракт, маппинг данных, ошибки, retry/fallback, деградация, настройки, ограничения, наблюдаемость и связанные страницы.

Если страница заявляет production-поведение интеграции, она должна отделять подтвержденные runtime значения от ожиданий из аналитики.

## Примеры обязательны

Integration page не должна ограничиваться общей фразой вида "сервис обращается к внешним системам". Для каждого ключевого integration point, который перечислен в странице как текущий источник или потребитель, нужен конкретный пример обмена:

- кто вызывает и кто отвечает;
- protocol/endpoint/RPC/route;
- демонстрационный request с подтвержденными полями;
- демонстрационный response или результат, если поля подтверждены;
- что целевая система делает с ответом дальше;
- таблица интерпретации: поле/значение источника, как система его читает, какой результат получает пользователь, downstream процесс или данные;
- что не утверждается без production/config/provider evidence.

Если реального fixture или test payload нет, пример может быть демонстрационным, но значения должны быть в корректном формате и только по подтвержденным полям. Плейсхолдеры и обрезки `<...>`, `...`, `…`, `{...}`, `[...]` не считаются примером. Пример, где есть только направление обмена и фраза "источник возвращает данные", не проходит kit.
## Полный методологический слой

Этот kit использует не только краткий checklist выше. В подпапке methodology/ лежат адаптированные материалы исходных feature methodology kits: README, templates, schemas, quality gates, examples и skill-инструкции.

При выполнении команд 12, 13 и 14 агент должен читать эти материалы как расширенный профиль kit-а и применять их к current-state базе знаний.

Подключенные source kits:

- methodology/integration-standard-kit/

Правило адаптации: использовать все требования к структуре, детализации, примерам, матрицам, диаграммам, проверкам и evidence, но не переносить в постоянную страницу future/change-management слой: TO BE, rollout/rollback, будущие требования, design proposals, GAP-*, ASM-*, DESIGN-* как читательский текст. Такие элементы фиксируются только в рабочем слое как gaps или не используются.

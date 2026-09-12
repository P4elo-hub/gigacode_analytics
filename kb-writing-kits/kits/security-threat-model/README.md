# Kit: Security / Threat Model

## Назначение

Для security, auth/session, privacy и trust boundaries текущей реализации.

## Reader-first обязательство

Применяй этот kit только вместе с `10-Governance/reader-first-writing-standard.md`. Постоянная страница сначала объясняет читателю назначение, участников, вход, результат и текущее поведение простым языком. Технические имена допустимы только после пояснения их роли; если на странице больше трех технических названий, добавь раздел `Как читать технические названия`.
## Evidence pack

- Assets: данные, события, contracts, user context.
- Actors: пользователь, клиентский канал, backend service, external system.
- Trust boundaries.
- Auth/session checks.
- Sensitive data и privacy ограничения.
- Threats и mitigations, только если подтверждены.
- Security-related logging или audit, если есть.

## Постоянная страница

Нужны область security, участники, границы доверия, защищаемые данные, передача/проверка контекста, текущие ограничения и меры защиты, связанные интерфейсы и данные.
## Полный методологический слой

Этот kit использует не только краткий checklist выше. В подпапке methodology/ лежат адаптированные материалы исходных feature methodology kits: README, templates, schemas, quality gates, examples и skill-инструкции.

При выполнении команд 12, 13 и 14 агент должен читать эти материалы как расширенный профиль kit-а и применять их к current-state базе знаний.

Подключенные source kits:

- methodology/security-threat-model-kit/

Правило адаптации: использовать все требования к структуре, детализации, примерам, матрицам, диаграммам, проверкам и evidence, но не переносить в постоянную страницу future/change-management слой: TO BE, rollout/rollback, будущие требования, design proposals, GAP-*, ASM-*, DESIGN-* как читательский текст. Такие элементы фиксируются только в рабочем слое как gaps или не используются.

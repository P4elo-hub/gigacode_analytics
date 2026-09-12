# Kit: Observability

## Назначение

Для логирования, метрик, трассировки и диагностических признаков текущего поведения.

## Reader-first обязательство

Применяй этот kit только вместе с `10-Governance/reader-first-writing-standard.md`. Постоянная страница сначала объясняет читателю назначение, участников, вход, результат и текущее поведение простым языком. Технические имена допустимы только после пояснения их роли; если на странице больше трех технических названий, добавь раздел `Как читать технические названия`.
## Evidence pack

- Log events и уровни.
- Поля логов и correlation/trace identifiers.
- Metrics names или metric categories.
- Tracing spans/tags.
- Error events.
- Dashboard/alert references, если есть.
- Связь с use case или интеграцией.

Для deep-detail intent `production-nfr-policy` или observability-focused page evidence pack дополнительно должен собрать:

- dashboard, alert, runbook, metric registry или logging policy, если они доступны;
- retention и sampling только при прямом evidence;
- связь log/metric/trace с конкретным use case, endpoint, integration или error path;
- gaps для production observability, которая ожидается, но не найдена.

## Постоянная страница

Нужно описать, что наблюдается, где формируются логи/метрики/trace, какие параметры помогают расследовать сценарий, какие ошибки видны в диагностике и какие ограничения наблюдаемости есть.

Не добавляй dashboard, alert или retention как текущее поведение без operational evidence.
## Полный методологический слой

Этот kit использует не только краткий checklist выше. В подпапке methodology/ лежат адаптированные материалы исходных feature methodology kits: README, templates, schemas, quality gates, examples и skill-инструкции.

При выполнении команд 12, 13 и 14 агент должен читать эти материалы как расширенный профиль kit-а и применять их к current-state базе знаний.

Подключенные source kits:

- methodology/observability-standard-kit/

Правило адаптации: использовать все требования к структуре, детализации, примерам, матрицам, диаграммам, проверкам и evidence, но не переносить в постоянную страницу future/change-management слой: TO BE, rollout/rollback, будущие требования, design proposals, GAP-*, ASM-*, DESIGN-* как читательский текст. Такие элементы фиксируются только в рабочем слое как gaps или не используются.

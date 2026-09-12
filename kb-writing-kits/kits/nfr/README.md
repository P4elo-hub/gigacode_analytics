# Kit: NFR

## Назначение

Для performance, reliability, security, compatibility, privacy и других нефункциональных аспектов текущей реализации.

## Reader-first обязательство

Применяй этот kit только вместе с `10-Governance/reader-first-writing-standard.md`. Постоянная страница сначала объясняет читателю назначение, участников, вход, результат и текущее поведение простым языком. Технические имена допустимы только после пояснения их роли; если на странице больше трех технических названий, добавь раздел `Как читать технические названия`.
## Evidence pack

- NFR domain и область действия.
- Фактические anchors в коде, config, tests или аналитике.
- Timeout, retry, cache, rate/limit, pagination или degradation, если подтверждены.
- Security/session/privacy facts.
- Expectations из feature analytics, если актуальны и не конфликтуют с кодом.
- Известные ограничения.

Для deep-detail intent `production-nfr-policy` evidence pack дополнительно должен собрать:

- production policy, SLA/SLO или SLI только из operational/policy evidence;
- runtime limits: timeout, retry, rate/limit, pagination, cache, degradation;
- monitoring/alerting/dashboard links через `observability` kit, если есть;
- test evidence для performance/reliability/security expectations;
- gaps для ожиданий, которые есть в feature analytics, но не подтверждены production evidence.

## Постоянная страница

Нужны область действия, текущее поведение, подтвержденные настройки и ограничения, влияние на сценарии, наблюдаемость и связанные страницы.

Нельзя придумывать SLA/SLO, latency, RPS или retention.
## Полный методологический слой

Этот kit использует не только краткий checklist выше. В подпапке methodology/ лежат адаптированные материалы исходных feature methodology kits: README, templates, schemas, quality gates, examples и skill-инструкции.

При выполнении команд 12, 13 и 14 агент должен читать эти материалы как расширенный профиль kit-а и применять их к current-state базе знаний.

Подключенные source kits:

- methodology/nfr-standard-kit/

Правило адаптации: использовать все требования к структуре, детализации, примерам, матрицам, диаграммам, проверкам и evidence, но не переносить в постоянную страницу future/change-management слой: TO BE, rollout/rollback, будущие требования, design proposals, GAP-*, ASM-*, DESIGN-* как читательский текст. Такие элементы фиксируются только в рабочем слое как gaps или не используются.

# Kit: Feature Toggle / Config

## Назначение

Для runtime-настроек, feature toggles, application properties и параметров, которые меняют поведение системы.

## Reader-first обязательство

Применяй этот kit только вместе с `10-Governance/reader-first-writing-standard.md`. Постоянная страница сначала объясняет читателю назначение, участников, вход, результат и текущее поведение простым языком. Технические имена допустимы только после пояснения их роли; если на странице больше трех технических названий, добавь раздел `Как читать технические названия`.
## Evidence pack

- Имя настройки или toggle.
- Где задана: config, DB, env, property file.
- Default value или gap.
- Кто читает настройку.
- На какую ветку поведения влияет.
- Поведение при true/false или разных значениях.
- Fallback при отсутствии значения.
- Риски изменения.

Для deep-detail intent `runtime-config-production-values` evidence pack дополнительно должен собрать:

- production/current values из config export, registry, deployment manifests или другого runtime evidence;
- default values из application config или code;
- environment/profile differences, если они подтверждены;
- owner/source of truth для значения, если он есть в источниках;
- что происходит при отсутствующем или некорректном значении;
- gap, если production value или owner не найден.

## Постоянная страница

Нужны назначение настройки, место хранения, значения/defaults, где используется, влияние на процесс, fallback, ошибки и риски эксплуатации.

Production/current value нельзя писать по названию property или по default из кода. Нужен отдельный runtime/config/registry/deployment evidence.
## Полный методологический слой

Этот kit использует не только краткий checklist выше. В подпапке methodology/ лежат адаптированные материалы исходных feature methodology kits: README, templates, schemas, quality gates, examples и skill-инструкции.

При выполнении команд 12, 13 и 14 агент должен читать эти материалы как расширенный профиль kit-а и применять их к current-state базе знаний.

Подключенные source kits:

- methodology/nfr-standard-kit/

Правило адаптации: использовать все требования к структуре, детализации, примерам, матрицам, диаграммам, проверкам и evidence, но не переносить в постоянную страницу future/change-management слой: TO BE, rollout/rollback, будущие требования, design proposals, GAP-*, ASM-*, DESIGN-* как читательский текст. Такие элементы фиксируются только в рабочем слое как gaps или не используются.

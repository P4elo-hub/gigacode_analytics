# Kit: Acceptance Checks

## Назначение

Дополнительный kit для use case, business rules, interface и integration страниц, если источники содержат acceptance criteria, тестовые сценарии или проверяемые ожидания.

## Reader-first обязательство

Применяй этот kit только вместе с `10-Governance/reader-first-writing-standard.md`. Постоянная страница сначала объясняет читателю назначение, участников, вход, результат и текущее поведение простым языком. Технические имена допустимы только после пояснения их роли; если на странице больше трех технических названий, добавь раздел `Как читать технические названия`.
## Evidence pack

- Acceptance criteria из analytics.
- Тесты, fixtures, examples.
- Preconditions.
- Action/trigger.
- Expected result.
- Negative/edge cases.
- Regression scope, если подтвержден.

## Постоянная страница

Acceptance checks можно включать как компактный раздел или таблицу:

| Проверка | Дано | Когда | Тогда | Источник поведения |
|---|---|---|---|---|

Если acceptance criteria относится к будущему изменению, его нельзя переносить как текущую проверку.
## Полный методологический слой

Этот kit использует не только краткий checklist выше. В подпапке methodology/ лежат адаптированные материалы исходных feature methodology kits: README, templates, schemas, quality gates, examples и skill-инструкции.

При выполнении команд 12, 13 и 14 агент должен читать эти материалы как расширенный профиль kit-а и применять их к current-state базе знаний.

Подключенные source kits:

- methodology/acceptance-test-standard-kit/

Правило адаптации: использовать все требования к структуре, детализации, примерам, матрицам, диаграммам, проверкам и evidence, но не переносить в постоянную страницу future/change-management слой: TO BE, rollout/rollback, будущие требования, design proposals, GAP-*, ASM-*, DESIGN-* как читательский текст. Такие элементы фиксируются только в рабочем слое как gaps или не используются.

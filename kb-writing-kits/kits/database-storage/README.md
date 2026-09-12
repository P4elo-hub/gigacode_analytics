# Kit: Database Storage

## Назначение

Для таблиц, схем, view, миграций, хранилищ и production DB export.

## Reader-first обязательство

Применяй этот kit только вместе с `10-Governance/reader-first-writing-standard.md`. Постоянная страница сначала объясняет читателю назначение, участников, вход, результат и текущее поведение простым языком. Технические имена допустимы только после пояснения их роли; если на странице больше трех технических названий, добавь раздел `Как читать технические названия`.
## Evidence pack

- Schema/table/view/cache name.
- Колонки, типы, nullable, defaults.
- Primary/foreign keys, indexes, constraints.
- Liquibase/DDL migrations.
- DAO/SQL/read-write paths.
- Writers и readers.
- Retention, cleanup, consistency.
- Row counts, справочные записи или фактические значения из production DB export.
- Для специального DBIO-раздела: ERD/PlantUML, ERD с данными, полное заполнение таблиц, SQL/DDL/DML и cache blocks из production DB export.

Для deep-detail intent `ddl-index-constraint-reference` evidence pack дополнительно должен собрать:

- DDL/Liquibase changesets или schema export;
- primary/foreign keys, unique/check constraints и indexes;
- default values, nullable и data type;
- DAO/SQL/read-write paths, которые реально используют объект;
- связь структуры с production DB export: фактическое наполнение, справочники, counts или отсутствие данных;
- gap, если index/constraint/retention нельзя подтвердить.

## Постоянная страница

Нужны назначение storage, структура, ключи, ограничения, миграции, пути чтения и записи, фактическое наполнение production DB и ограничения данных.

Код и миграции являются источником структуры и механизма, а `DBIO-001` - источником фактического наполнения. Не выводи бизнес-правило только из наличия строк в production export.

Если страница описывает production DB export, она является справочником данных из `db-export/` и должна содержать полное заполнение, а не только аналитическое summary. Типовая структура export-материалов:

- `README.md` - навигация;
- `erd.md` - ERD и ERD с данными в PlantUML;
- `<schema>-filled-tables.md` - полное заполнение таблиц по схеме или сервису;
- `cache.md` - SQL/JSON кэшей, если такой блок есть в export.
## Полный методологический слой

Этот kit использует не только краткий checklist выше. В подпапке methodology/ лежат адаптированные материалы исходных feature methodology kits: README, templates, schemas, quality gates, examples и skill-инструкции.

При выполнении команд 12, 13 и 14 агент должен читать эти материалы как расширенный профиль kit-а и применять их к current-state базе знаний.

Подключенные source kits:

- methodology/data-standard-kit/
- methodology/migration-standard-kit/

Правило адаптации: использовать все требования к структуре, детализации, примерам, матрицам, диаграммам, проверкам и evidence, но не переносить в постоянную страницу future/change-management слой: TO BE, rollout/rollback, будущие требования, design proposals, GAP-*, ASM-*, DESIGN-* как читательский текст. Такие элементы фиксируются только в рабочем слое как gaps или не используются.

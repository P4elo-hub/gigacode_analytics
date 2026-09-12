# Kit: Field Lineage

## Назначение

Для пути поля от внешнего источника или БД до внутренней модели и клиентского ответа.

## Reader-first обязательство

Применяй этот kit только вместе с `10-Governance/reader-first-writing-standard.md`. Постоянная страница сначала объясняет читателю назначение, участников, вход, результат и текущее поведение простым языком. Технические имена допустимы только после пояснения их роли; если на странице больше трех технических названий, добавь раздел `Как читать технические названия`.
## Evidence pack

- Source field.
- Internal field/model.
- Response field/UI field.
- Transformation rule.
- Enum/status/type mapping.
- Defaults и fallback.
- Loss of precision, format changes.
- Примеры значений из тестов, аналитики или DB export.
- Если маппинг восстановлен из БД, SQL, справочников или production DB export: target object, максимальный состав target-полей, матрица возможностей, правила необязательных полей, source-by-type/source-by-scenario mapping, representative DB rows.

Для deep-detail intent `domain-field-lineage` или `source-priority-matrix` evidence pack дополнительно должен собрать:

- источник значения: внешняя система, таблица, cache, DTO, proto или feature analytics;
- путь значения через internal model, mapper/converter и response/UI field;
- priority/fallback между источниками, если поле может приходить из нескольких мест;
- условия потери точности, нормализации, форматирования или замены дефолтом;
- непокрытые поля как gaps, а не как молчаливое отсутствие.

## Постоянная страница

Нужны назначение маппинга, схема движения данных, матрица source -> internal -> target, правила трансформации, defaults/fallback, исключения и влияние на отображение/downstream behavior.

Матрица не должна быть единственным содержанием страницы: перед ней нужно объяснить, для какого результата нужна lineage и как читать направления source, internal и target.

## DB-derived mapping matrix

Если страница описывает маппинги, восстановленные из БД, SQL, production DB export, справочников, экранной статики или конфигурационных таблиц, дополнительно применяй `10-Governance/db-derived-mapping-standard.md`.

Такая страница должна иметь уровень детализации:

- словарь сокращений и терминов;
- target object: DTO, response, event, file, screen model, internal model или другой объект;
- максимальный состав target-полей с типом/кратностью и смыслом;
- матрицу возможностей по типам, статусам, сценариям, каналам или платформам;
- правила необязательных полей: отсутствует, `null`, пустая строка, дефис, ноль, derived value;
- source-by-type или source-by-scenario mapping;
- field-level lineage с transformation, fallback/default, условиями появления и потерей данных;
- формулы отображения и display rules, если они есть;
- representative DB rows из `production-db-export`, если источник подключен;
- конкретные примеры прохождения значения от source до target.

Обычная data page не должна копировать полный дамп production DB export. Полный дамп хранится в `db-export/`; mapping page использует его для representative rows, проверок и ссылок.
## Полный методологический слой

Этот kit использует не только краткий checklist выше. В подпапке methodology/ лежат адаптированные материалы исходных feature methodology kits: README, templates, schemas, quality gates, examples и skill-инструкции.

При выполнении `/find-context`, `/write-feature` и `/check-feature` агент должен читать эти материалы как расширенный профиль kit-а и применять их к источникам workspace (`analytics/`, `repositories/`, `db-export/`, `Feature-writing/`).

Подключенные source kits:

- methodology/data-mapping-standard-kit/
- methodology/data-standard-kit/

Правило адаптации: использовать все требования к структуре, детализации, примерам, матрицам, диаграммам, проверкам и evidence, но не переносить в постоянную страницу future/change-management слой: TO BE, rollout/rollback, будущие требования, design proposals, GAP-*, ASM-*, DESIGN-* как читательский текст. Такие элементы фиксируются только в рабочем слое как gaps или не используются.

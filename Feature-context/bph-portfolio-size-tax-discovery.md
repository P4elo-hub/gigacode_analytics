# INTERNAL: discovery-пакет контекста фичи (не отдавать как есть)

## Бриф
Добавление новой операции из источника БПХ. Операция будет неторговой, она посвящена налогу за размер портфеля клиента от 5 миллионов рублей. Приходит/взимается отдельно по каждой операции.

## Поисковые термины (вес = приоритет)
`бпх.`(×3), `операции.`(×3), `рублей.`(×3), `взимается`(×1), `добавление`(×1), `источника`(×1), `каждой`(×1), `клиента`(×1), `миллионов`(×1), `налогу`(×1), `неторговой`(×1), `новой`(×1), `операции`(×1), `операция`(×1), `отдельно`(×1), `портфеля`(×1), `посвящена`(×1), `приходит`(×1), `размер`(×1)

Области поиска: аналитика `analytics/`, спецификации `Feature-writing/`, код `repositories/`, данные `db-export/`, доп. материалы `auxiliary/`.

## Кандидаты (ранжированы по score)

### Спецификации фич (Feature-writing/)

| Файл | Score | Совпавшие термины | Фрагмент |
|---|---|---|---|
| `Feature-writing/bph-linked-events-yield/bph-linked-events-yield.md` | 52 | `операции`, `операция`, `отдельно`, `операции.`, `клиента`, `каждой` | > Уровень размещения доходности уточняется (GAP-INT-07): операционный lead `HistoryOperationLead` — наиболее вероятная цель для доходности операции. Поля цен... |
| `Feature-writing/bph-moex-tax/bph-moex-tax.md` | 41 | `операции`, `операция`, `новой`, `добавление`, `клиента`, `каждой` | \| Фича \| Добавление типовой операции `TAXES / MOEX_TAX` из BPH в историю операций \| |
| `Feature-writing/og-trading-order-yield/og-trading-order-yield.md` | 33 | `операции`, `операция`, `отдельно`, `клиента`, `источника`, `приходит` | \| Успех \| Торговые заявки получены из ОГ, объединены с другими источниками и доступны в исходящем контракте; доходность отсутствует \| |
| `Feature-writing/og-trading-order-yield/og-trading-order-yield-challenges.md` | 3 | `приходит`, `операция`, `операции` | \| CH-11 \| §4.1.1, §4.1.1.1 \| `HistoryOperationLead` уже содержит поле `currency` (валюта операции). При заполнении `yield.currency` — должны ли они **всегда*... |
| `Feature-writing/og-trading-order-yield/og-trading-order-yield-code-alignment.md` | 2 | `отдельно` | \| T-04 \| §5.5 \| Отдельного toggle для доходности нет \| grep yield в конфигах — 0 \| CONFIRMED \| Info \| |
| `Feature-writing/og-trading-order-yield/og-trading-order-yield-challenges-resolved.md` | 1 | `операции` | \| CH-16 \| MISSING → resolved \| a \| Yield в Ignite cache с TTL операции \| CN-09, §2 \| PO \| |
| `Feature-writing/og-trading-order-yield/og-trading-order-yield-gaps-resolved.md` | 1 | `операции` | \| GAP-CONS-01 / GAP-DM-01 / Q-09 \| a \| Транзит: без PostgreSQL; Ignite как часть операции → CN-09 \| §2, §4.2.3 \| |

### Аналитика (analytics/)

| Файл | Score | Совпавшие термины | Фрагмент |
|---|---|---|---|
| `analytics/SIHIST/SIHIST_markdown_back/[SIHIST-3793]_Сортировка_по_дате_исполнения_для_вкладки_История_на_Композите.md` | 119 | `операции.`, `операция`, `операции`, `клиента`, `источника`, `размер` | **Как работает сейчас:** При формировании ленты истории операций для отображения клиенту в мобильном приложении или веб-версии система НО (сервис истории опе... |
| `analytics/SIHIST/SIHIST_markdown_front/Фронт Композит/Отмены_лента_(FE).md` | 95 | `операция`, `операции`, `клиента`, `рублей.`, `операции.` | \| 4 \| Не отменять \| Кнопка \| Служит для закрытия   модального окна отмены операции. Текст кнопки берётся из поля  -   sections.content.buttons.cancellationBu... |
| `analytics/SIHIST/SIHIST_markdown_back/[SIHIST-3502]_Получение_торговых_операций_из_BPH_по_обмену_GET_LINKED_EVENTS_(ВЕ).md` | 89 | `операции`, `операция`, `источника`, `клиента`, `новой`, `добавление` | - **Источник комиссий:** BPH, BC и OG. Расчет и добавление комиссий по этим сделкам производятся на основе данных: 1. Если комиссии BPH есть для всех сделок ... |
| `analytics/SIHIST/SIHIST_markdown_front/Фронт Композит/Редактирование_операций_(FE).md` | 89 | `операции`, `операция`, `рублей.`, `новой`, `операции.`, `клиента` | 3. Клиент нажимает кнопку редактирования/отмены в ленте/деталке операции. **Mobile App** открывает "**Штора редактирования"**, передавая id операции (без пре... |
| `analytics/SIHIST/SIHIST_markdown_back/[SIHIST-3503]_Получение_легаси_торговых_операций_из_BPH_по_обмену_GET_OPERATION_WITH_DETAILS_(ВЕ).md` | 85 | `операции`, `операция`, `источника`, `отдельно`, `клиента`, `добавление` | - **Источник комиссий:** BPH, BC и OG. Расчет и добавление комиссий по этим сделкам производятся на основе следующих правил: |
| `analytics/SIHIST/SIHIST_markdown_back/[SIHIST-3485]_Композит_-_лента_(BE).md` | 80 | `операция`, `операции`, `операции.`, `приходит`, `добавление`, `клиента` | - детальной информации по операции. |
| `analytics/SIHIST/SIHIST_markdown_back/[SIHIST-2850]_Фильтр_по_дате_и_времени_для_запроса_истории_операции_[back].md` | 79 | `операции`, `клиента`, `операции.`, `новой`, `добавление`, `размер` | 1. НО дедублицирует операции. |
| `analytics/SIHIST/SIHIST_markdown_back/[SIHIST-2811]_Обработка_ответов_от_BC_и_BPH_с_учётом_данных_из_БД.md` | 77 | `операция`, `операции`, `операции.`, `приходит`, `источника`, `клиента` | \| {}.resp[].{}.operations[].{}.operation_display_name \| string \| [1-1] \| Отображаемое имя операции \| Значение для него берётся из поля displayed_name таблицы... |
| `analytics/SIHIST/SIHIST_markdown_back/[SIHIST-3398]_Изменение_взаимодействия_с_DG.md` | 77 | `операция`, `операции`, `операции.`, `каждой`, `добавление`, `клиента` | > Если запрос будет отправлен без блока filters, то Бэк отработает его как запрос по всем типам операциям, во всех договорах пользователя, включая отменённые... |
| `analytics/SIHIST/SIHIST_markdown_back/[SIHIST-3563]_Редактирование_торговых_операций_с_ленты_(BE).md` | 77 | `операции`, `операция`, `новой`, `рублей.`, `операции.`, `клиента` | 1. Клиент нажимает кнопку редактирования/отмены в ленте/деталке операции. **Mobile App** открывает "**Штора редактирования"**, передавая `id операции` (без п... |
| `analytics/SIHIST/SIHIST_markdown_back/[SIHIST-3755]_Отображение_причины_отмены_для_операций_переводов_и_выводов.md` | 76 | `операции`, `операция`, `клиента`, `каждой`, `добавление`, `операции.` | \| {}.operations_details [].{}.operation_display_name \| string \| [1-1] \| Отображаемое имя операции \| Значение для него берётся из поля **displayed_name** табл... |
| `analytics/SIHIST/SIHIST_markdown_back/[SIHIST-3373]_Композит_-_Деталка_(BE).md` | 74 | `операция`, `операции`, `операции.`, `приходит`, `клиента`, `источника` | - детальной информации по операции. |
| `analytics/SIHIST/SIHIST_markdown_back/[SIHIST-3250]_Перевод_комиссий_на_BPH_AS_IS.md` | 72 | `операция`, `операции`, `приходит`, `клиента`, `отдельно`, `операции.` | \| {}.resp[].{}.operations[].{}.operation_display_name \| string \| [1-1] \| Отображаемое имя операции \| Значение для него берётся из поля **displayed_name** таб... |
| `analytics/SIHIST/SIHIST_markdown_back/[SIHIST-1868]_Получение_информации_о_торговых_заявках_и_сделках_из_ВРН.md` | 71 | `операции`, `источника`, `операция`, `клиента`, `приходит`, `отдельно` | - [Фильтры операций из источника](#фильтры-операций-из-источника) |
| `analytics/SIHIST/SIHIST_markdown_front/Фронт Композит/Отмены_деталка_(FE).md` | 71 | `операция`, `операции`, `клиента`, `рублей.`, `операции.` | \| 4 \| Не отменять \| Кнопка \| Служит для закрытия   модального окна отмены операции. Текст кнопки берётся из поля  -   sections.content.buttons.cancellationBu... |

### Код и контракты (repositories/)

| Файл | Score | Совпавшие термины | Фрагмент |
|---|---|---|---|
| `repositories/ИО/history-ops-screen-api/sowa/inet_sigma/from_mobile_to_history_ops_screen_api_operations_feed_http/history_ops_screen_api_operations_feed/schemes/response.json` | 31 | `операции`, `рублей.`, `операция` | "example": "Для отмены заявки необходимо заплатить коммиссию двадцать рублей." |
| `repositories/ИО/history-ops-screen-api/src/test/resources/db/init-test-screens-with-empty-operation-types-filter.sql` | 26 | `операции`, `операция` | 'Секция параметров операции', |
| `repositories/ИО/history-ops-screen-api/src/test/resources/db/init-test-screens-without-operation-types-filter.sql` | 26 | `операции`, `операция` | 'Секция параметров операции', |
| `repositories/ИО/history-ops-screen-api/src/test/resources/db/init-test-screens.sql` | 26 | `операции`, `операция` | 'Секция параметров операции', |
| `repositories/ИО/history-ops/src/main/swagger/bph/bph.yml` | 25 | `операции` | summary: Получение детализации по операции |
| `repositories/ИО/history-ops-screen-api/sowa/inet_sigma/from_mobile_to_history_ops_screen_api_operation_details_http/history_ops_screen_api_operation_details/schemes/response.json` | 12 | `операции`, `операция` | "description": "Данные экрана операции", |
| `repositories/ИО/history-ops/sowa/sigma_alpha/operation_history_to_synapse_rq_http/bc_http_proxy/schemes/xsd/002/response_schema.xsd` | 9 | `операции`, `операция`, `источника` | <xs:documentation>Тип рынка источника: 0 – фондовый рынок, 1 – срочный рынок, 2 |
| `repositories/ИО/history-ops/src/test/resources/db/init/create_schema.sql` | 6 | `добавление`, `операции` | -- Добавление данных в таблицу general_status |
| `repositories/ИО/history-ops/sowa/sigma_alpha/to_bph_rq_http/history_get_linked_events/schemes/json/POST_api_v1_incoming-gateway_operations_linked-events_response_200.json` | 5 | `операции`, `клиента` | "description": "Договор клиента" |
| `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/service/BphRejectReasonHolder.java` | 5 | `операция` | "VAL_OCC_001", "Операция не может быть проведена в соответствии с Федеральным законом № 115-ФЗ от 07.08.2001", |
| `repositories/ИО/history-ops-screen-api/src/test/resources/responses/history-ops-screen-api/feed/history-ops-screen-api-response-10.json` | 4 | `операции`, `операция` | "title": "Тип операции", |
| `repositories/ИО/history-ops-screen-api/src/test/resources/responses/history-ops-screen-api/feed/history-ops-screen-api-response-11.json` | 4 | `операции`, `операция` | "title": "Тип операции", |
| `repositories/ИО/history-ops-screen-api/src/test/resources/responses/history-ops-screen-api/feed/history-ops-screen-api-response-12.json` | 4 | `операции`, `операция` | "title": "Тип операции", |
| `repositories/ИО/history-ops-screen-api/src/test/resources/responses/history-ops-screen-api/feed/history-ops-screen-api-response-2.json` | 4 | `операции`, `операция` | "title": "Тип операции", |
| `repositories/ИО/history-ops-screen-api/src/test/resources/responses/history-ops-screen-api/feed/history-ops-screen-api-response-3.json` | 4 | `операции`, `операция` | "title": "Тип операции", |
| `repositories/ИО/history-ops-screen-api/src/test/resources/responses/history-ops-screen-api/feed/history-ops-screen-api-response-4.json` | 4 | `операции`, `операция` | "title": "Тип операции", |
| `repositories/ИО/history-ops-screen-api/src/test/resources/responses/history-ops-screen-api/feed/history-ops-screen-api-response-5.json` | 4 | `операции`, `операция` | "title": "Тип операции", |
| `repositories/ИО/history-ops-screen-api/src/test/resources/responses/history-ops-screen-api/feed/history-ops-screen-api-response-6.json` | 4 | `операции`, `операция` | "title": "Тип операции", |
| `repositories/ИО/history-ops-screen-api/src/test/resources/responses/history-ops-screen-api/feed/history-ops-screen-api-response-7.json` | 4 | `операции`, `операция` | "title": "Тип операции", |
| `repositories/ИО/history-ops-screen-api/src/test/resources/responses/history-ops-screen-api/feed/history-ops-screen-api-response-8.json` | 4 | `операции`, `операция` | "title": "Тип операции", |
| `repositories/ИО/history-ops-screen-api/src/test/resources/responses/history-ops-screen-api/feed/history-ops-screen-api-response-disabled-auto-follow-operations.json` | 4 | `операции`, `операция` | "title": "Тип операции", |
| `repositories/ИО/history-ops-screen-api/src/test/resources/responses/history-ops-screen-api/feed/history-ops-screen-api-response-disabled-cancellation.json` | 4 | `операции`, `операция` | "title": "Тип операции", |
| `repositories/ИО/history-ops-screen-api/src/test/resources/responses/history-ops-screen-api/feed/history-ops-screen-api-response-disabled-edit.json` | 4 | `операции`, `операция` | "title": "Тип операции", |
| `repositories/ИО/history-ops-screen-api/src/test/resources/responses/history-ops-screen-api/feed/history-ops-screen-api-response-with-empty-operation-types-filter.json` | 4 | `операции`, `операция` | "title": "Тип операции", |
| `repositories/ИО/history-ops-screen-api/src/test/resources/responses/history-ops-screen-api/feed/history-ops-screen-api-response.json` | 4 | `операции`, `операция` | "title": "Тип операции", |

### Данные (db-export/)

| Файл | Score | Совпавшие термины | Фрагмент |
|---|---|---|---|
| `db-export/БД ИО.md` | 65 | `операции`, `операции.`, `источника`, `операция`, `клиента`, `приходит` | \| `chevron`               \| 20   \| Маппинг типа операции на малый логотип: `chevron` берется из `logo` строки `chevron`, где `operation_type` равен типу теку... |

### Доп. материалы (auxiliary/)

Совпадений в auxiliary не найдено.

## Инструкция для агента
1. Прочитай топ-кандидатов из таблиц (начни с наибольшего score; при необходимости расширь поиск Grep/SemanticSearch по тем же терминам).
2. Не подтверждай факты по одному имени файла — открой файл и проверь содержимое (класс, метод, endpoint, proto-сообщение, таблицу, поле).
3. `analytics/` — актуальная аналитика и выгрузка Confluence по фичам: используй для бизнес-контекста, AS IS / TO BE, требований. Технические факты (контракты, поля, код) подтверждай по `repositories/` и `db-export/`.
4. Заполни **Скелет документа-контекста** ниже: для каждого факта дай ссылку на конкретный файл (и якорь: класс/метод/таблица/endpoint).
5. Неизвестное и непроверенное помечай в разделе «Открытые вопросы», не выдумывай поведение.
6. Это контекст для будущего написания фичи, а не сама фича: не проектируй решение, опиши то, что уже есть и что нужно учесть.
7. В финальном документе не оставляй «INTERNAL», score-таблиц и этой инструкции.

## Скелет документа-контекста (заполни и верни)

# Контекст для фичи: bph-portfolio-size-tax

## Задача (бриф)

> Кратко перескажи бриф своими словами: что меняем и зачем.

## Затронутые области

| Область | Что затрагивается | Документы / код |
|---|---|---|
| | | |

## Релевантная аналитика и спеки

| Документ (analytics/, Feature-writing/) | Что описывает | Почему релевантно задаче |
|---|---|---|
| | | |

## Релевантный код

| Файл | Компонент (класс / метод / endpoint / proto) | Текущее поведение | Почему важно для фичи |
|---|---|---|---|
| | | | |

## Данные (БД, выгрузки)

| Таблица / поле / запрос | Где найдено | Текущее устройство | На что влияет фича |
|---|---|---|---|
| | | | |

## Интеграции и контракты, которые нужно учесть

- 

## Ограничения и риски текущего состояния

- 

## Что учесть при написании фичи

- 

## Открытые вопросы / что проверить

| ID | Вопрос | Где искать ответ |
|---|---|---|
| Q-01 | | |

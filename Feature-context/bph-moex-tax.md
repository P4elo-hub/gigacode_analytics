# Контекст для фичи: bph-moex-tax

## Задача (бриф)

> В интеграции `history-ops` ↔ BPH по `GET_OPERATIONS_WITH_DETAILS` нужно добавить обработку нового налога: BPH присылает `type = TAXES`, `subtype = MOEX_TAX` (новый подтип). В Java операция маппится в **тот же** исходящий объект, что и обычный налог (`operation_type = tax`), отличие — **другой `comment`**, который берётся из таблицы `info` по `additionalType`. Логика обработки идентична существующим налогам `TAX_RETAIN`; изменения **data-driven через БД**, без правок Java-кода.

**Трактовка брифа (дана пользователем):** новый BPH subtype семейства `TAXES` маппится в существующий `operation_type = tax`; специфика (текст для UI) задаётся строкой в таблице `info`; `additional_type` — отсутствует (NULL). Механика — как у `TAX_RETAIN`; добавление — INSERT в таблицы маппинга БД HO. Java-код и алгоритм запроса/ответа BPH не меняются.

Это **current-state** документ: фиксирует существующий механизм маппинга налогов из BPH и что именно надо будет добавить данными, без проектирования решения.

## Затронутые области

| Область | Что затрагивается | Документы / код |
|---|---|---|
| Интеграция `history-ops` ↔ BPH | Обмен `GET_OPERATIONS_WITH_DETAILS` — новый subtype семейства `TAXES` в запросе/ответе | `analytics/02-Modules/MOD-001-history-ops/integrations/bph.md`; `repositories/ИО/history-ops/src/main/swagger/bph/bph.yml` |
| Маппинг БД HO (PostgreSQL `history_ops`) | Таблицы `type`, `bph`, `operation`, `operation_type`, `info`, `status_to_operation` — добавление строк | `db-export/БД ИО.md`; `analytics/02-Modules/MOD-001-history-ops/data/bc-bph-mapping-db.md` |
| Java `history-ops` | **Не меняется** — data-driven через кэш маппинга | `BphCommonClientConverter.java`; `BphBcFilterService.java` |
| Лента операций МП | Исходящий объект `operation_type = tax` с новым `comment` | `analytics/.../behavior/operation-type-catalog.md` (секция «Удержание налогов из BPH») |

## Релевантная аналитика и спеки

| Документ (analytics/, Feature-writing/) | Что описывает | Почему релевантно задаче |
|---|---|---|
| `analytics/02-Modules/MOD-001-history-ops/behavior/operation-type-catalog.md` | Каталог типов операций; секция **«Удержание налогов из BPH (3321)»**: `TAXES/TAX_RETAIN` → `tax` (additionalTypes `OUT_MONEY`/`OUT_SECURITIES`/`TAX_PERIOD_END`/`INCENTIVE_PAYMENT`); `TAX_REFUND_BROK_ACCOUNT` → `tax_input`; `comment` из `info.comment` по `additionalType`, `display_name` из `info.displayed_name` | Эталон механики, к которому добавляется `MOEX_TAX` |
| `analytics/02-Modules/MOD-001-history-ops/behavior/bph-response-processing.md` | DB-aware маппинг запроса/ответа BPH: `subtypesAndStatuses` + `additionalTypes[]` из кэша; post-filter — матчинг `additionalType` ↔ `info[].additional_type`; comment/logo из `info[]` | Описывает точный алгоритм, который «просто заработает» после INSERT новых строк |
| `analytics/02-Modules/MOD-001-history-ops/data/bc-bph-mapping-db.md` | Полная схема таблиц маппинга (`operation_type`, `type`, `bph`, `bph_bc`, `operation`, `info`, `status`, `status_to_operation`, …), кэш-строка, примеры | Справочник по устройству таблиц, куда пишется INSERT |
| `analytics/02-Modules/MOD-001-history-ops/integrations/bph.md` | Контракт `GET_OPERATIONS_WITH_DETAILS` (endpoint, headers, body `subtypesAndStatuses`, ответ `data[].lead`) | Контракт источника — поля `type`/`subtype`/`additionalType`/`status` |
| `Feature-writing/bph-portfolio-size-tax/bph-portfolio-size-tax.md` | **Sibling-фича**: налог `PORTFOLIO_SIZE_TAX` из того же семейства `TAXES` → `tax`, тот же data-driven паттерн; в §2 ссылается на `bph-moex-tax` (MOEX_TAX) как на sibling-паттерн | Прямой аналог: те же таблицы, тот же механизм, общая зона риска по id-строкам и статусам |

## Релевантный код

| Файл | Компонент (класс / метод / endpoint) | Текущее поведение | Почему важно для фичи |
|---|---|---|---|
| `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/service/conversion/BphCommonClientConverter.java` | `convert()`; `getAdditionalInfoFromCache()`; `isCorrectAdditionalType()`; `enrichComment()`; константа `TAXES = "TAXES"` | Ищет `Operation` в кэше по `originalType`+`bphType` (bphActive), из `operation.info()` подбирает строку по `additional_type == lead.additionalType` (NULL→`""`, сравнивается `equals`); применяет `comment` и `displayedName`; **для `TAXES` при пустом comment — fallback `accComment`** | Тот же код без изменений: новый subtype `MOEX_TAX` с `info(additional_type=NULL)` подхватится матчингом `"" == ""`, если BPH-ответ приходит без `additionalType` |
| `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/service/filter/BphBcFilterService.java` | `buildBphRequestEntityByBphParams()`; `isActualBphOperation()`; `isCommonOperationByBphContext()` | Формирует `subtypesAndStatuses` из кэша; `additionalTypes[]` добавляется **только** из `info[].additional_type` с `filter(Objects::nonNull)`; при отсутствии BC-контекста (`bcType`/`bcSubtype` пусты) в `isActualBphOperation()` срабатывает ранний `return true` (пропуск watershed и additionalType-фильтра); статус-членство проверяется всегда через `statusMap.containsKey(status)` | Определяет, что для нового subtype с `bc_id=NULL` и `additional_type=NULL` запрос к BPH идёт без `additionalTypes[]`, а проверки watershed/additionalType не блокируют; блокирующим остаётся только статус-членство |
| `repositories/ИО/history-ops/src/main/swagger/bph/bph.yml` | `POST /api/v1/incoming-gateway/operations-with-details` (строка 216); headers `rqUID`/`systemName`; schema `RequestParamsData` (subtypesAndStatuses) | Контракт BPH: запрос с `subtypesAndStatuses[].{type, subtype, statuses, additionalTypes?}`; ответ `data[].lead` c `type`/`subtype`/`additionalType`/`status` | Контракт неизменен; `MOEX_TAX` — лишь новое значение `subtype` в `subtypesAndStatuses` |

## Данные (БД, выгрузки)

Все факты — `db-export/БД ИО.md` (выгрузка схемы и данных БД HO, PostgreSQL `history_ops`).

| Таблица / поле | Где найдено (якорь) | Текущее устройство | На что влияет фича |
|---|---|---|---|
| `type` (id `7` = `TAXES`) | `db-export/БД ИО.md:314,1655` | Справочник BPH-типов; семейство налогов = `TAXES` (id 7) | Семейство нового subtype уже существует — добавлять `type` не нужно |
| `operation_type` (id `2` = `tax`, id `20` = `tax_input`) | `db-export/БД ИО.md:335,343-344,1555` | Нормализованный тип МП; `tax` и `tax_input` уже есть | `MOEX_TAX` → существующий `tax` (id 2) — новый `operation_type` не вводится |
| `bph` (id `19` = `TAX_RETAIN`, type_id `7`; id `20` = `TAX_REFUND_BROK_ACCOUNT`, type_id `7`; max id `24`) | `db-export/БД ИО.md:425,1655,2896` | Справочник BPH `type/subtype` + `is_active` | Добавляется новая строка `bph(subtype=MOEX_TAX, type_id=7, is_active=true)` |
| `operation` (id `2` = `tax`, bc_id `110` `TAX_WITHHOLDING`, bph_id `19` `TAX_RETAIN`; id `23` = `tax_input`, bc_id `NULL`, bph_id `20`; max id `26`) | `db-export/БД ИО.md:476-477,1692,1713,2944` | Центральная строка маппинга: `operation_type_id` + `bc_id` + `bph_id` + `name` | Добавляется строка `operation(operation_type_id=2, bc_id=?, bph_id=<MOEX_TAX>, name=?)`; значение `bc_id` (`NULL` vs `110`) — открытый вопрос (см. Q-04) |
| `info` (operation `2` → 4 строки с `additional_type` = `OUT_MONEY`/`OUT_SECURITIES`/`TAX_PERIOD_END`/`INCENTIVE_PAYMENT` и своими `comment`; operation `23` → 1 строка с `additional_type=NULL`, `comment='Возврат излишне удержанного налога'`; max id `77`) | `db-export/БД ИО.md:1726,1760-1763,2989` | UI-метаданные: `additional_type`, `comment`, `displayed_name`, `logo_url*` | Добавляется строка(и) `info` с `comment` для `MOEX_TAX`; по брифу `additional_type=NULL` (одна строка) |
| `status` (id `19` = `COMPLETE` → `general_status_id=1` `executed`) | `db-export/БД ИО.md:375,1594` | BPH-статус → general_status | Статус для нового subtype (по аналогии `COMPLETE`) |
| `status_to_operation` (operation `2` ↔ status `19`; operation `23` ↔ status `19`; max id `56`) | `db-export/БД ИО.md:601-602,1828` | Какие BPH-статусы допустимы для операции (статус-членство в `statusMap.containsKey`) | Добавляется связка `operation_id=<MOEX_TAX> ↔ status_id=19 (COMPLETE)` — иначе статус-членство отфильтрует операцию |
| Кэш-строка `tax` (TAX_RETAIN) и `tax_input` (TAX_REFUND_BROK_ACCOUNT) | `db-export/БД ИО.md:3308-3351,3984-4004` | Пример рантайм-кэша: `bph_subtype`/`type`/`bph_active`/`bc_active`/`status_and_general_status`/`info[]`; у `tax_input` `bc_type`/`bc_subtype` = `null`, `info[].additional_type = null` | Показывает точный shape, который должен получиться для `MOEX_TAX` (BPH-only, `additional_type=null`) |
| Liquibase changeset `20250606_SIHIST-3321_added_tax_data.sql`, `20250611_SIHIST-3321_modify_type.sql` | `db-export/БД ИО.md:778-779,2046-2047` | Прецедент data-driven добавления налогов через SQL changeset (SIHIST-3321) | Шаблон миграции, который нужно повторить для `MOEX_TAX` |

## Интеграции и контракты, которые нужно учесть

- **`GET_OPERATIONS_WITH_DETAILS`** — `POST /api/v1/incoming-gateway/operations-with-details`, headers `rqUID` + `systemName=si2-ops`, body `RequestParamsData` с `subtypesAndStatuses[]` (`type`, `subtype`, `statuses`, опц. `additionalTypes`). Ответ: `data[].lead` c `type`, `subtype`, `additionalType`, `status`, `totalPrice`, `formationDate`/`eventDate`. Контракт **не меняется** — меняются только данные маппинга. Якоря: `bph.yml:216+`, `analytics/.../integrations/bph.md`.
- **Термины домена:** `TAXES` = BPH-тип (family), `TAX_RETAIN` / `TAX_REFUND_BROK_ACCOUNT` = существующие subtypes, `additionalType` = сужающий фильтр BPH, `subtypesAndStatuses` = фильтр запроса, `bc_id`/`bph_id` = связи `operation` с источниками.
- **Формирование запроса:** `additionalTypes[]` в `subtypesAndStatuses` добавляется только для `info[].additional_type` с не-NULL значением (`BphBcFilterService.buildBphRequestEntityByBphParams`, `filter(Objects::nonNull)`). Для `additional_type=NULL` фильтр не добавляется — запрос идёт по `type+subtype+statuses` без сужения.
- **Маппинг ответа:** `comment`/`displayedName` подбираются из `info[]` по совпадению `additional_type == lead.additionalType` (NULL трактуется как `""`, `"" == ""` → true) (`BphCommonClientConverter.isCorrectAdditionalType`). При пустом `comment` для `TAXES` — fallback на `lead.accComment`.

## Ограничения и риски текущего состояния

- **`MOEX_TAX` не подтверждён ни в одном источнике** (`analytics/`, `repositories/`, `db-export/`) — 0 совпадений. Это новый subtype, значение взято из брифа. Расхождение по написанию приведёт к тому, что запрос вернёт пусто и налог «молча» не отобразится.
- **Java-код не меняется** — фича целиком data-driven. Без правок кода нельзя изменить алгоритм: только через данные таблиц маппинга и кэш.
- **Кэш маппинга обновляется cron-ом** (интервал `bd_response_cron_time`, default 60 мин; при ошибке SQL кэш не перезаписывается). Новые строки появятся в рантайме только после обновления кэша — временной лаг между проливом и фактическим поведением.
- **Статус-членство — жёсткий фильтр:** если для нового `operation` не настроена связка `status_to_operation` с фактическим BPH-статусом, операция отфильтруется (`statusMap.containsKey(status)`). Для `bc_id=NULL` watershed и additionalType-фильтр **не** являются блокирующими (ранний `return true` в `isActualBphOperation`).
- **Общая зона риска с sibling-фичей** `bph-portfolio-size-tax` (тоже `TAXES` → `tax`): черновые id строк (`bph`/`operation`/`info`/`status_to_operation`) не должны пересекаться.
- **Отличие от `TAX_RETAIN`:** у `TAX_RETAIN` 4 `info`-строки с непустыми `additional_type` и `bc_id=110` (есть BC-аналог `TAX_WITHHOLDING`); по брифу у `MOEX_TAX` `additional_type` отсутствует. Это влияет на то, сколько `info`-строк и какое `bc_id` заводить (см. Q-03, Q-04).

## Что учесть при написании фичи

- Это **data-only** фича: INSERT в `bph` (+1), `operation` (+1, `operation_type_id=2` tax), `info` (+1 или более, с `comment`), `status_to_operation` (+1). Новые `type`, `operation_type`, `status` заводить не нужно.
- Паттерн «BPH-only налог» уже существует: `TAX_REFUND_BROK_ACCOUNT` (operation `23`, `bc_id=NULL`, `info.additional_type=NULL`, `status COMPLETE`) — см. кэш-строку `db-export/БД ИО.md:3984-4004`. `MOEX_TAX` отличается от него только `operation_type = tax` (вместо `tax_input`) и своим `comment`.
- Механику маппинга `comment` по `additional_type` (NULL ↔ `""`) обязательно отразить в spec как подтверждённую кодом (`BphCommonClientConverter.java`).
- Сверить с контрактом BPH точное написание `MOEX_TAX`, наличие/отсутствие `additionalType` в ответе и фактический `status` — до пролива (иначе запрос вернёт пусто / статус-членство отфильтрует).
- Учесть обновление кэша (`operation-cache`, cron) и неконфликтные id с `bph-portfolio-size-tax`.

### Актуализация после resolve (2026-10-05)

Решения из resolve, которые писатель и ревьюер должны считать актуальнее исходного current-state:

- GAP-UCTB-03: `info.additional_type = NULL` (одна info-строка) — по брифу/трактовке
- GAP-CONS-03: `info.additional_type = NULL`
- GAP-INT-03: `info.additional_type = NULL` → `additionalTypes[]` не передаётся в запросе
- GAP-ALG-03: `info.additional_type = NULL` (одна строка), матчинг NULL ↔ `""`
- GAP-DM-03: `info.additional_type = NULL`
- GAP-MAP-03: source path `info.additional_type = NULL`
- GAP-MIG-03: `info.additional_type = NULL` (по брифу)
- GAP-UCAS-01: Триггер синхронизации — по запросу клиента МП (в ходе `SEND_OPERATIONS` / `GET_OPERATIONS`); отдельной cron-синхронизации нет (cron — только обновление кэша маппинга)
- GAP-UCAS-02: Недоступность BPH → partial failure (возвращаются операции OG/BC с признаком неполноты); timeout/retry — конфигурация WebClient HO (`WebClientBphConfiguration`)
- GAP-UCAS-03: Исходящий канал — gRPC `SEND_OPERATIONS` (`HistoryOpsGrpcService`)
- GAP-GOAL-04: `MOEX_TAX` подтверждено (как в брифе); `comment` = «Удержание суммы налога»
- GAP-UCTB-01: Написание `MOEX_TAX` подтверждено
- GAP-CONS-01: Написание `MOEX_TAX` подтверждено
- GAP-INT-01: Написание `MOEX_TAX` подтверждено
- GAP-ALG-01: Написание `MOEX_TAX` подтверждено
- GAP-DM-01: Написание `MOEX_TAX` подтверждено
- GAP-MAP-01: Написание `MOEX_TAX` подтверждено
- GAP-MIG-01: Написание `MOEX_TAX` подтверждено
- GAP-OBS-01: Написание `MOEX_TAX` подтверждено
- GAP-UCTB-02: `comment` = «Удержание суммы налога» (переиспользована формулировка `TAX_RETAIN`)
- CH-05: —
- CH-06: —
- CH-07: —
- CH-12: —
- CH-16: —
- CH-17: ## Ожидают решения пользователя (needs-answer)
- CH-01: D-13
- CH-04: D-14
- CH-15: D-15
- CH-02: D-16
- CH-03: D-17
- CH-08: D-18
- CH-09: D-19
- CH-10: D-20
- CH-11: D-21
- CH-14: D-22
- CH-18: D-23
- CH-13: D-24
- CH-19: D-25
- CH-01: A (D-13)

**Якоря полей из актуальной SPEC:**

`MOEX_TAX`, `comment`, `name`, `displayed_name`, `TAX_RETAIN`, `GET_OPERATIONS_WITH_DETAILS`, `info`, `additionalType`, `bph.yml`, `updateDelayMs`, `status_to_operation`, `BphBcFilterService.java`

См. также § «Закрытые вопросы» ниже — не переспрашивать закрытые Q.
## Открытые вопросы / что проверить

| ID | Вопрос | Где искать ответ |
|---|---|---|
| Q-01 | Точное написание нового BPH-подтипа — `MOEX_TAX` (0 совпадений в `analytics/`/`repositories/`/`db-export/`)? Вариант/опечатка (`MOEX_TAX` vs иное) критичен для `subtypesAndStatuses`. | Команда BPH / контракт BPH (`bph_config_*`, ответ `GET_OPERATION_TYPES`) |
| Q-02 | Точный текст `comment` для `MOEX_TAX` (текст для UI)? Бриф даёт только «другой comment». | Product Owner / команда BPH |
| Q-03 | `info.additional_type` действительно `NULL` (одна info-строка), как у `TAX_REFUND_BROK_ACCOUNT`, или конкретное значение? (бриф: «additional_type отсутствует») | Product Owner / команда BPH |
| Q-04 | `operation.bc_id` для `MOEX_TAX` — `NULL` (BPH-only, как `TAX_REFUND_BROK_ACCOUNT`) или `110` (как `TAX_RETAIN`)? Влияет на watershed/ранний `return true` в `isActualBphOperation()`. | Product Owner (решение по аналогии); проверка по коду `BphBcFilterService` |
| Q-05 | Какой BPH-статус у `MOEX_TAX` и какая связка `status_to_operation` (по аналогии `COMPLETE` id=19 → `executed`)? | Команда BPH / контракт; `db-export/БД ИО.md:601-602` |
| Q-06 | `operation.name` / `info.displayed_name` для новой строки — переиспользовать «Удержание суммы налога» или новое имя? | Product Owner |
| Q-07 | Приходит ли `lead.additionalType` в ответе BPH для `MOEX_TAX` как `null`/отсутствует? Если BPH пришлёт non-null `additionalType`, матчинг `info(additional_type=NULL) → "" == ""` не сработает и `comment` не подставится. | Команда BPH / образец ответа `GET_OPERATIONS_WITH_DETAILS` |
| Q-08 | Достаточно ли cron-обновления кэша маппинга после пролива, или требуется ручной прогрев/рестарт? | Конфиг `app-config.operation-cache` (`bd_response_cron_time`) / сопровождение ИО |

## Закрытые вопросы

| ID | Дата | Решение | Где в spec | Источник |
|----|------|---------|------------|----------|
| Q-03 | 2026-10-05 | `info.additional_type = NULL` (одна info-строка) — по брифу/трактовке «additional_type — отсутствует (NULL)» | §1.3, §2, §4.1.1, §4.2.2, §4.2.3, §4.2.4, §4.3 | /resolve-gaps (GAP-UCTB-03, GAP-CONS-03, GAP-INT-03, GAP-ALG-03, GAP-DM-03, GAP-MAP-03, GAP-MIG-03) |
| Q-01 | 2026-10-05 | Написание подтипа `MOEX_TAX` подтверждено (значение, как в брифе) | §1.1, §1.3, §2, §4.1.1, §4.2.2, §4.2.3, §4.2.4, §4.3, §5.3 | /resolve-gaps (D-01) |
| Q-02 | 2026-10-05 | `comment` = «Удержание суммы налога» (переиспользована формулировка `TAX_RETAIN`) | §1.1, §1.3, §2, §4.1.1, §4.2.2, §4.2.3, §4.2.4, §4.3 | /resolve-gaps (D-02) |
| Q-04 | 2026-10-05 | `operation.bc_id` = NULL (BPH-only, паттерн `TAX_REFUND_BROK_ACCOUNT`) | §1.3, §2, §4.2.2, §4.2.3, §4.2.4, §4.3, §5.3 | /resolve-gaps (D-03) |
| Q-05 | 2026-10-05 | BPH-статус `COMPLETE` (id=19 → `executed`) + связка `status_to_operation(operation↔19)` | §1.3, §2, §4.1.1, §4.2.2, §4.2.3, §4.2.4, §4.3 | /resolve-gaps (D-04) |
| Q-07 | 2026-10-05 | `lead.additionalType` в ответе BPH = null/отсутствует (матчинг `"" == ""` срабатывает) | §1.3, §2, §4.1.1, §4.2.2, §4.2.3, §4.2.4, §4.3, §5.3 | /resolve-gaps (D-05) |
| Q-06 | 2026-10-05 | `operation.name` = «Удержание суммы налога» (переиспользована формулировка `TAX_RETAIN`, согласуется с D-02); `info.displayed_name` = NULL (универсальный паттерн — у всех существующих операций) | §1.3, §2, §4.2.2, §4.2.3, §4.2.4, §4.3 | /resolve-gaps (факт: GAP-UCTB-06, GAP-CONS-06, GAP-ALG-07, GAP-DM-06, GAP-MAP-06, GAP-MIG-06) |


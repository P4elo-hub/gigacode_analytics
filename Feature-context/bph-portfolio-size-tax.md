# Контекст для фичи: bph-portfolio-size-tax

## Задача (бриф)

> Добавить новую **неторговую (non-trading)** операцию из источника **BPH (БПХ)** — налог за размер портфеля клиента с порогом от **5 000 000 ₽**. Налог приходит/взимается **отдельно по каждой операции** (не агрегированно).

**Трактовка брифа (дана пользователем):** в интеграции `history-ops` ↔ BPH по `GET_OPERATIONS_WITH_DETAILS` добавляется новый **подтип налоговой операции** (семейство `TAXES`). Механика аналогична существующим налогам `TAX_RETAIN` и `MOEX_TAX`: **data-driven через таблицы маппинга БД HO**, без правок Java-кода. Отличие — новый BPH subtype (в выгрузках не найден) и **иной `comment`** для UI.

Это **current-state** документ: фиксирует существующий механизм маппинга налогов из BPH и что потребуется добавить данными, без проектирования решения.

**Важное замечание по брифе:** отдельного SIHIST-тикета под «налог за размер портфеля» нет — эта часть брифа оборвана (см. Q-07, Q-08).

## Затронутые области

| Область | Что затрагивается | Документы / код |
|---|---|---|
| Интеграция `history-ops` ↔ BPH | Обмен `GET_OPERATIONS_WITH_DETAILS` — новый subtype семейства `TAXES` в запросе/ответе | `analytics/02-Modules/MOD-001-history-ops/integrations/bph.md`; `repositories/ИО/history-ops/src/main/swagger/bph/bph.yml` |
| Маппинг БД HO (PostgreSQL `history_ops`) | Таблицы `bph`, `operation`, `info`, `status_to_operation` — добавление строк (data-only) | `db-export/БД ИО.md`; `analytics/02-Modules/MOD-001-history-ops/data/bc-bph-mapping-db.md` |
| Java `history-ops` | **Не меняется** — data-driven через кэш маппинга | `BphCommonClientConverter.java`; `BphBcFilterService.java`; `BphOperationConverter.java` |
| Лента операций МП | Исходящий объект `operation_type = tax` с новым `comment` | `analytics/.../behavior/operation-type-catalog.md` (секция «Удержание налогов из BPH») |
| Соседние фичи | Общая зона таблиц/id с `bph-moex-tax` (`MOEX_TAX`) — тот же паттерн `TAXES → tax` | `Feature-writing/bph-moex-tax/` |

## Релевантная аналитика и спеки

| Документ (analytics/, Feature-writing/) | Что описывает | Почему релевантно задаче |
|---|---|---|
| `analytics/02-Modules/MOD-001-history-ops/behavior/operation-type-catalog.md` | Секция «Удержание налогов из BPH (3321)»: `TAXES/TAX_RETAIN` → `tax` (additionalTypes `OUT_MONEY`/`OUT_SECURITIES`/`TAX_PERIOD_END`/`INCENTIVE_PAYMENT`); `TAX_REFUND_BROK_ACCOUNT` → `tax_input` (не в 3321); `comment` из `info.comment` по `additionalType`, `display_name` из `info.displayed_name` | Эталон механики, к которому добавляется новый подтип |
| `analytics/02-Modules/MOD-001-history-ops/behavior/bph-response-processing.md` | DB-aware маппинг запроса/ответа BPH: `subtypesAndStatuses` + `additionalTypes[]` из кэша; post-filter — матчинг `additionalType` ↔ `info[].additional_type`; comment/logo из `info[]` | Описывает алгоритм, который «просто заработает» после INSERT новых строк |
| `analytics/02-Modules/MOD-001-history-ops/data/bc-bph-mapping-db.md` | Схема таблиц маппинга (`operation_type`, `type`, `bph`, `bph_bc`, `operation`, `info`, `status`, `status_to_operation`, …), кэш-строка | Справочник по устройству таблиц, куда пишется INSERT |
| `analytics/02-Modules/MOD-001-history-ops/integrations/bph.md` | Контракт `GET_OPERATIONS_WITH_DETAILS` (endpoint, headers, body `subtypesAndStatuses`, ответ `data[].lead`) | Контракт источника — поля `type`/`subtype`/`additionalType`/`status` |
| `Feature-writing/bph-moex-tax/bph-moex-tax.md` (+ `-decisions.md`, `-code-alignment.md`, `-challenges.md`) | **Sibling-фича** `MOEX_TAX` из того же семейства `TAXES` → `tax`, тот же data-driven паттерн; решения D-01…D-25 закрывают вопросы, идентичные для этой фичи (написание subtype, comment, bc_id, статус, additional_type, id-строки, pre-check) | Прямой аналог: те же таблицы, тот же механизм, общая зона риска по id-строкам и статусам. Рекомендуется выровнять значения с этой фичей (см. D-16: `bph-moex-tax` объявлен authoritative для `MOEX_TAX`) |

## Релевантный код

| Файл | Компонент (класс / метод / endpoint) | Текущее поведение | Почему важно для фичи |
|---|---|---|---|
| `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/service/conversion/BphCommonClientConverter.java` | `convert()`; `getAdditionalInfoFromCache()`; `isCorrectAdditionalType()`; `enrichComment()`; `getId()`; константа `TAXES = "TAXES"` | Ищет `Operation` в кэше по `originalType`+`bphType` (фильтр `bphActive`); из `operation.info()` подбирает строку по `additional_type == lead.additionalType` (NULL→`""`, `equals`); применяет `comment`/`displayedName`; для `TAXES` при пустом comment — fallback `lead.accComment`; `id = bph_{operation_type}_{externalSystemId}`; `totalSum = abs(totalPrice)` | Тот же код без изменений: новый subtype с `info(additional_type=NULL)` подхватится матчингом `"" == ""`, если BPH-ответ приходит без `additionalType` |
| `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/service/filter/BphBcFilterService.java` | `buildBphRequestEntityByBphParams()`; `isActualBphOperation()` | `additionalTypes[]` формируется из `info[].additional_type` с `filter(Objects::nonNull)` (строки 115-119), передаётся только при непустом списке; при отсутствии BC-контекста (`bc_id=NULL`) — ранний `return true` (строки 190/194/264), watershed/additionalType-фильтр не блокируют; статус-членство проверяется всегда `statusMap.containsKey(status)` (строки 85, 353) | Для нового subtype с `bc_id=NULL` и `additional_type=NULL` запрос к BPH идёт без `additionalTypes[]`, а watershed/additionalType не блокируют; блокирующим остаётся только статус-членство |
| `repositories/ИО/history-ops/src/main/java/com/sberbank/si20/history/ops/adapter/bph/BphOperationConverter.java` | `convert()`; `validateSimpleAttributes()`; `getSubType()` | Валидирует обязательные поля `type`, `subType`/`subtype`, `formationDate`, `eventDate`, `externalSystemId`, `status`, `agreement`; `getSubType()` читает оба имени (`subtype`, `subType`) через `BphTypesHolder` | Показывает, что контракт BPH имеет два имени поля подтипа и что маппинг типов идёт через `BphTypesHolder` (кэш) |
| `repositories/ИО/history-ops/src/main/swagger/bph/bph.yml` | `POST /api/v1/incoming-gateway/operations-with-details` (строка 216); schema `RequestParamsData` (`subtypesAndStatuses`), `OperationData` | Контракт BPH: запрос с `subtypesAndStatuses[].{type, subtype, statuses, additionalTypes?}` (maxItems 1000, maxLength 225); ответ `data[].lead` c `type`/`subtype`/`additionalType`/`status`/`totalPrice`; `OperationData` имеет оба поля `subType` и `subtype` | Контракт неизменен; новый подтип — лишь новое значение `subtype` в `subtypesAndStatuses` |

## Данные (БД, выгрузки)

Все факты — `db-export/БД ИО.md` (выгрузка схемы и данных БД HO, PostgreSQL `history_ops`).

| Таблица / поле | Где найдено (якорь) | Текущее устройство | На что влияет фича |
|---|---|---|---|
| `type` id `7` = `TAXES` | `db-export/БД ИО.md`, object `type` | Справочник BPH-типов; семейство налогов = `TAXES` (id 7) | Семейство нового subtype уже существует — `type` добавлять не нужно |
| `operation_type` id `2` = `tax`, id `20` = `tax_input` | `db-export/БД ИО.md`, object `operation_type` | Нормализованный тип МП | Целевой `operation_type` для нового налога (по аналогии `TAX_RETAIN`/`MOEX_TAX` → `tax`, id 2) — см. Q-03 |
| `bph` (24 строки): id `19` = `TAX_RETAIN` (type_id 7, active), id `20` = `TAX_REFUND_BROK_ACCOUNT` (type_id 7, active); **max id `24`** | `db-export/БД ИО.md`, object `bph` (полный листинг 24 строк) | Справочник BPH `type/subtype` + `is_active` | Нового подтипа **нет** ни в одной из 24 строк — добавляется новая строка `bph(subtype=<новый>, type_id=7, is_active=true)` |
| `operation`: id `2` = `tax` (bc_id `110` `TAX_WITHHOLDING`, bph_id `19`); id `23` = `tax_input` (bc_id `NULL`, bph_id `20`); **max id `26`** | `db-export/БД ИО.md`, object `operation` | Центральная строка маппинга: `operation_type_id` + `bc_id` + `bph_id` + `name` | Добавляется строка `operation(operation_type_id=?, bc_id=?, bph_id=<новый>, name=?)`; `bc_id` (`NULL` vs `110`) — открытый вопрос Q-04 |
| `info`: operation `2` → 4 строки с `additional_type` = `OUT_MONEY`/`INCENTIVE_PAYMENT`/`OUT_SECURITIES`/`TAX_PERIOD_END` (свои `comment`); operation `23` → 1 строка `additional_type=NULL`, `comment='Возврат излишне удержанного налога'` | `db-export/БД ИО.md`, object `info` | UI-метаданные: `additional_type`, `comment`, `displayed_name`, `logo_url*` | Добавляется строка(и) `info` с `comment` для нового налога; значение `additional_type` (`NULL` vs конкретное) — Q-06 |
| `status` id `19` = `COMPLETE` → `general_status_id=1` `executed` | `db-export/БД ИО.md`, object `status` | BPH-статус → general_status | Фактический статус нового subtype и его связка — Q-05 |
| `status_to_operation`: operation `2` ↔ status `19`; operation `23` ↔ status `19` | `db-export/БД ИО.md`, object `status_to_operation` | Статус-членство (`statusMap.containsKey`) — жёсткий фильтр | Добавляется связка `operation_id=<новый> ↔ status_id=19` — иначе операция отфильтруется |
| Liquibase changeset `SIHIST-3321` (добавление налогов data-driven) | `db-export/БД ИО.md` (`databasechangelog`, 103 строки) | Прецедент data-driven добавления налогов через SQL changeset | Шаблон миграции, который повторяется для нового подтипа |

## Интеграции и контракты, которые нужно учесть

- **`GET_OPERATIONS_WITH_DETAILS`** — `POST /api/v1/incoming-gateway/operations-with-details`, headers `rqUID` + `systemName=history_ops`, body `RequestParamsData` с `subtypesAndStatuses[]` (`type`, `subtype`, `statuses`, опц. `additionalTypes`). Ответ: `data[].lead` c `type`, `subtype`, `additionalType`, `status`, `totalPrice`, `formationDate`/`eventDate`. Контракт **не меняется** — меняются только данные маппинга. Якоря: `bph.yml:216+`, `analytics/.../integrations/bph.md`.
- **Термины домена:** `TAXES` = BPH-тип (family, `type.id=7`), `TAX_RETAIN` / `TAX_REFUND_BROK_ACCOUNT` = существующие subtypes, `MOEX_TAX` = новый subtype из sibling-фичи `bph-moex-tax`, `additionalType` = сужающий фильтр BPH, `subtypesAndStatuses` = фильтр запроса, `bc_id`/`bph_id` = связи `operation` с источниками.
- **Формирование запроса:** `additionalTypes[]` добавляется только для `info[].additional_type` с не-NULL значением (`BphBcFilterService`, `filter(Objects::nonNull)`). Для `additional_type=NULL` фильтр не добавляется — запрос идёт по `type+subtype+statuses` без сужения.
- **Маппинг ответа:** `comment`/`displayedName` подбираются из `info[]` по `additional_type == lead.additionalType` (NULL ↔ `""`, `"" == ""` → true); при пустом `comment` для `TAXES` — fallback `lead.accComment` (`BphCommonClientConverter`).
- **Кэш маппинга:** обновляется cron-ом (`app-config.operation-cache.updateDelayMs`); при ошибке SQL кэш не перезаписывается. Новые строки видны в рантайме только после обновления кэша.

## Ограничения и риски текущего состояния

- **Новый BPH subtype не подтверждён ни в одном источнике** (`analytics/`, `repositories/`, `db-export/`) — 0 совпадений. В sibling-контексте `bph-moex-tax` этот подтип ранее упоминался как `PORTFOLIO_SIZE_TAX` (семейство `TAXES` → `tax`), но сам файл `Feature-writing/bph-portfolio-size-tax/` и `Feature-context/bph-portfolio-size-tax.md` **удалены** — актуального подтверждения значения нет. Расхождение по написанию → запрос вернёт пусто и налог «молча» не отобразится (Q-01).
- **Java-код не меняется** — фича целиком data-driven. Алгоритм нельзя поменять кодом, только данными таблиц маппинга и кэшем.
- **Кэш маппинга обновляется cron-ом** — временной лаг между проливом changeset и фактическим поведением; при стабильном сбое обновления строки в БД есть, в рантайме нет.
- **Статус-членство — жёсткий фильтр** (`statusMap.containsKey(status)`): без корректной связки `status_to_operation` операция отфильтруется. Для `bc_id=NULL` watershed и additionalType-фильтр **не** блокируют (ранний `return true`).
- **Общая зона риска с sibling-фичей** `bph-moex-tax` (тоже `TAXES` → `tax`): id новых строк (`bph`/`operation`/`info`/`status_to_operation`) не должны пересекаться. Sibling отложил id на DBA и использует SERIAL/sequence-авто (D-10, D-20).
- **Порог 5 000 000 ₽** — по брифе это бизнес-условие начисления налога (для портфелей свыше порога); в HO **не** реализуется фильтр по порогу — решение о начислении принимает BPH, HO лишь маппит пришедшую операцию. Требует подтверждения (Q-07), т.к. часть брифа оборвана.
- **`info.additional_type` NULL vs пустая строка `''`**: `filter(Objects::nonNull)` пропускает `''` (не NULL), что исказит `additionalTypes[]` и матчинг (риск, выявленный sibling-фичей — D-18).

## Что учесть при написании фичи

- Это **data-only** фича: INSERT в `bph` (+1), `operation` (+1, `operation_type_id`), `info` (+1 или более, с `comment`), `status_to_operation` (+1). Новые `type`, `operation_type`, `status` заводить не нужно (все существуют).
- **Эталонный паттерн «BPH-only налог»** — `TAX_REFUND_BROK_ACCOUNT` (operation `23`, `bc_id=NULL`, `info.additional_type=NULL`, статус `COMPLETE`). Новый налог отличается от него `operation_type` (`tax` вместо `tax_input`) и своим `comment`.
- **Выровнять с sibling `bph-moex-tax`**: тот прошёл полный цикл resolve (D-01…D-25) и зафиксировал решения по идентичным вопросам — написание subtype, `comment`, `bc_id=NULL`, статус `COMPLETE`, `additional_type=NULL`, pre-check «0 строк», SERIAL-авто id, non-SMART метрика, data-level приёмка. Рекомендуется переиспользовать эти решения, где применимо, и явно зафиксировать непересечение id с `bph-moex-tax`.
- Механику маппинга `comment` по `additional_type` (NULL ↔ `""`) обязательно отразить в spec как подтверждённую кодом (`BphCommonClientConverter.java`).
- Сверить с контрактом BPH точное написание нового subtype, наличие/отсутствие `additionalType` в ответе и фактический `status` — до пролива.
- Учесть обновление кэша (`operation-cache`, cron) и pre-check на дубли (`bph.subtype` без UNIQUE — см. D-24 sibling).

### Актуализация после resolve (2026-10-06)

Решения из resolve, которые писатель и ревьюер должны считать актуальнее исходного current-state:

- GAP-GOAL-03, GAP-UCAS-01, GAP-UCTB-01, GAP-CONS-01, GAP-INT-01, GAP-ALG-01, GAP-DM-01, GAP-MAP-01, GAP-OBS-01: Написание подтипа — `PORTFOLIO_SIZE_TAX`
- GAP-GOAL-04, GAP-UCTB-02, GAP-CONS-07, GAP-INT-02, GAP-ALG-02, GAP-DM-02, GAP-MAP-02: `comment` для UI — «Налог за размер портфеля»
- GAP-GOAL-05, GAP-UCTB-03, GAP-CONS-02, GAP-INT-03, GAP-ALG-03, GAP-DM-03, GAP-MAP-03: `operation_type` = `tax` (id=2)
- GAP-CONS-03, GAP-UCTB-05, GAP-ALG-04, GAP-DM-04, GAP-MAP-04, GAP-OBS-03: `operation.bc_id` = `NULL` (BPH-only)
- GAP-CONS-04, GAP-UCTB-06, GAP-INT-04, GAP-ALG-05, GAP-DM-05, GAP-MAP-05: BPH-статус `COMPLETE` (id=19) + `status_to_operation(operation↔19)`
- GAP-CONS-05, GAP-UCTB-04, GAP-INT-05, GAP-ALG-06, GAP-DM-06, GAP-MAP-06: `info.additional_type` = `NULL` (одна info-строка)
- GAP-GOAL-06, GAP-CONS-06, GAP-UCTB-07, GAP-ALG-07: Порог «от 5 000 000 ₽» — BPH-side правило (CN-04), HO не фильтрует
- GAP-CONS-08, GAP-ALG-08, GAP-DM-08, GAP-MAP-08: `operation.name` = «Налог за размер портфеля», `info.displayed_name` = NULL
- GAP-DM-07, GAP-MAP-07: id новых строк — sequence автоматически (INSERT без явного id), непересечение через pre-check (CN-06)
- GAP-GOAL-01, GAP-GOAL-02, GAP-GOAL-07, GAP-OBS-02: Non-SMART: полнота налоговой ленты через `history_ops_integration_total` + SQL-сверка + интеграционный тест; инициатор/тикет не критичны
- GAP-NFR-01, GAP-NFR-04: Производительность и SLO/SLA наследуются без новых target'ов (CN-14)
- GAP-UCAS-02, GAP-NFR-02, GAP-NFR-03, GAP-NFR-06, GAP-NFR-07: Значения timeout/retry/deadline/page-size задаются внешним конфигом; partial failure без retry (CN-15)
- GAP-NFR-05, GAP-NFR-09, GAP-OBS-04: Аутентификация/хранение/маскирование — детали внешние (Vault/SOWA, `log_masking_rules.yml`); новые классы чувствительных данных не вводятся (CN-16)
- GAP-NFR-08: Отдельный toggle не вводится; раскатка data-driven (`bph.is_active` + кэш), лаг = `update-delay-ms` (CN-17)
- GAP-OBS-05: Вне scope — новых UI-метрик нет
- CH-05: —
- CH-06: —
- CH-09: —
- CH-10: —
- CH-12: B (D-15)
- CH-01: A (D-16)
- CH-02: A (D-17)
- CH-03: A (D-18)
- CH-04: A (D-19)
- CH-07: A (D-20)
- CH-08: A (D-21)
- CH-13: B (D-22)
- CH-15: B (D-23)
- CH-11: A (D-24)
- CH-14: A (D-25)
- CH-16: B (D-26)

**Якоря полей из актуальной SPEC:**

`comment`, `GET_OPERATIONS_WITH_DETAILS`, `TAXES`, `PORTFOLIO_SIZE_TAX`, `operation_type`, `tax`, `TAX_RETAIN`, `MOEX_TAX`, `type`, `tax_input`, `bph`, `operation`

См. также § «Закрытые вопросы» ниже — не переспрашивать закрытые Q.
## Открытые вопросы / что проверить

| ID | Вопрос | Где искать ответ |
|---|---|---|
| Q-01 | Точное написание нового BPH-подтипа (ранее в удалённом sibling-контексте фигурировал `PORTFOLIO_SIZE_TAX`). 0 совпадений в `analytics/`/`repositories/`/`db-export/`. Расхождение критично для `subtypesAndStatuses` и lookup `operation` — налог «молча» не отобразится | Команда BPH / контракт BPH (ответ `GET_OPERATION_TYPES`, `bph_config_*`) |
| Q-02 | Точный текст `comment` для UI («иной comment» из брифа). Бриф не даёт конкретного значения | Product Owner / команда BPH |
| Q-03 | Целевой `operation_type` нового налога: `tax` (id 2, как `TAX_RETAIN`/`MOEX_TAX`) или `tax_input` (id 20) или новый? | Product Owner (по аналогии с существующими налогами); sibling `bph-moex-tax` → `tax` |
| Q-04 | `operation.bc_id`: `NULL` (BPH-only, паттерн `TAX_REFUND_BROK_ACCOUNT`) или `110` (`TAX_WITHHOLDING`, как `TAX_RETAIN`)? Влияет на watershed/ранний `return true` в `isActualBphOperation()` | Product Owner; проверка по коду `BphBcFilterService.java` |
| Q-05 | Фактический BPH-статус нового subtype и связка `status_to_operation` (по аналогии `COMPLETE` id=19 → `executed`)? | Команда BPH / контракт; `db-export/БД ИО.md` |
| Q-06 | `info.additional_type`: `NULL` (одна info-строка, как у `TAX_REFUND_BROK_ACCOUNT`) или конкретное значение? Бриф: «отдельно по каждой операции (не агрегированно)» | Команда BPH / Product Owner |
| Q-07 | Порог «от 5 000 000 ₽» — это BPH-side бизнес-правило начисления (HO не фильтрует по порогу), или требуется какая-то логика в HO? Часть брифа оборвана, отдельного SIHIST-тикета нет | Product Owner / владелец брифа |
| Q-08 | Номер SIHIST-тикета / релиз для этой фичи (в `analytics/` совпадений нет; бриф об этом не сообщает) | Product Owner / Jira (SIHIST-XXXX) |
| Q-09 | Значения `operation.name` и `info.displayed_name` для новой строки: уникальный текст или переиспользование формулировки существующего налога? | Product Owner (см. sibling D-02/D-19: у `MOEX_TAX` оба = «Удержание суммы налога», `displayed_name=NULL`) |

## Закрытые вопросы

| ID | Дата | Решение | Где в spec | Источник |
|----|------|---------|------------|----------|
| Q-01 | 2026-10-06 | Написание нового BPH-подтипа — `PORTFOLIO_SIZE_TAX` | §1.1, §1.3, §2, §4.1.1, §4.2.3, §4.2.4, §5.3.1 | /resolve-gaps (D-01) |
| Q-02 | 2026-10-06 | `comment` для UI — «Налог за размер портфеля» | §1.1, §4.1.1, §4.2.3, §4.2.4 | /resolve-gaps (D-02) |
| Q-03 | 2026-10-06 | Целевой `operation_type` — `tax` (id=2) | §1.1, §2, §4.1.1, §4.2.3, §4.2.4 | /resolve-gaps (D-03) |
| Q-04 | 2026-10-06 | `operation.bc_id` = `NULL` (BPH-only паттерн `TAX_REFUND_BROK_ACCOUNT`) | §2, §4.2.3, §5.3.1, §5.3.2 | /resolve-gaps (D-04) |
| Q-05 | 2026-10-06 | BPH-статус `COMPLETE` (id=19) + связка `status_to_operation(operation↔19)` | §2, §4.1.1, §4.2.3 | /resolve-gaps (D-05) |
| Q-06 | 2026-10-06 | `info.additional_type` = `NULL` (одна info-строка) | §2, §4.1.1, §4.2.3 | /resolve-gaps (D-06) |
| Q-07 | 2026-10-06 | Порог «от 5 000 000 ₽» — BPH-side правило начисления, HO не фильтрует (CN-04) | §1.1, §2 | /resolve-gaps (D-07) |
| Q-08 | 2026-10-06 | Non-SMART: SIHIST-тикет/инициатор не критичны для data-only фичи; полнота через `history_ops_integration_total` + SQL-сверка + интеграционный тест | §1.1, §5.3.2 | /resolve-gaps (D-09) |
| Q-09 | 2026-10-06 | `operation.name` = «Налог за размер портфеля», `info.displayed_name` = NULL | §2, §4.2.3, §4.2.4 | /resolve-gaps (D-08) |

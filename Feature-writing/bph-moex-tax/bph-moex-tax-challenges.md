---
report_type: feature-challenges
slug: bph-moex-tax
source_document: Feature-writing/bph-moex-tax/bph-moex-tax.md
generated_at: 2026-10-05
challenge_iteration: 1
language: ru
---

# Критический разбор: bph-moex-tax

**Спецификация:** `Feature-writing/bph-moex-tax/bph-moex-tax.md`
**Банк вопросов:** `Feature-writing/bph-moex-tax/bph-moex-tax-challenges.md`

## Сводка
- Вопросов: 14 (Critical: 1 · Major: 8 · Minor: 5)
- Фокус прогона: полный проход по категориям + углубление в `bc_id=NULL` (ранний return), `additionalType=NULL`, дубли/приоритет источников, degraded-поведение, координация id и откат

## Бизнес-логика и use case

| ID | § spec | Вопрос | Тип | Severity | Статус |
|----|--------|--------|-----|----------|--------|
| CH-01 | §1.3 постусловие «Неуспех (техн.)»; §2 CN-09; §4.2.2 BR-13 | `bc_id = NULL` означает «только BPH-контекст» и отсутствие BC-корреляции (`bph_bc`). Подтверждено ли, что `MOEX_TAX` приходит **только** из BPH, а не также из OG/BC? У `TAX_RETAIN` `bc_id=110` (`TAX_WITHHOLDING`) — BC-аналог, по которому history-ops коррелирует/дедуплицирует операцию между BPH и BC. Для `MOEX_TAX` такой корреляции нет: если тот же налог прилетит и из BPH, и из другого источника (OG/BC), history-ops не распознает их как одну операцию — в ленте будет дубль без дедупликации и без приоритета источников. | missing-flow | Major | resolved |
| CH-02 | §2 CN-10; §4.2.2 BR-13; §4.2.4 «Backfill: Н/П» | Watershed для `MOEX_TAX` не задаётся (`bc_id=NULL` → ранний return). Значит у нового налога **нет даты отсечения**: при включении BPH (или при ретро-выгрузке исторических событий) в историю пользователя попадут все `MOEX_TAX` с произвольной давностью, в отличие от `TAX_RETAIN` (watershed `historyStart`). Ожидаемо ли это? Сценарий «BPH отдаёт исторические MOEX_TAX при старте» в §4.2.4 не описан (Backfill помечен Н/П только для строк БД, не для данных BPH). | scope-ambiguity | Major | resolved |

## Контракты и интеграции

| ID | § spec | Вопрос | Тип | Severity | Статус |
|----|--------|--------|-----|----------|--------|
| CH-04 | §2 CN-08; §4.2.4 маппинг `comment`; §6 ACC-E01 | `additionalType = NULL` зафиксировано **допущением** (в §1.1 «Противоречия» явно: «значение принято допущением — контракт BPH его не подтверждает»). При `bc_id=NULL` `additionalType`-фильтр пропущен (BR-13), поэтому non-null `additionalType` от BPH **не отфильтруется**, а `enrichComment()` не найдёт строку `info` по `additional_type` (в `info` только NULL-строка) → подставится fallback `details.accComment` вместо «НАЛОГ МОСКОВСКОЙ БИРЖИ». Это silent wrong data, и негативного теста «BPH прислал non-null additionalType» нет (ACC-E01 проверяет только NULL). | contract-edge | Critical | resolved |
| CH-05 | §4.1.1; §4.2.4 формат `id`; sibling `bph-portfolio-size-tax` BR-03 | `MOEX_TAX` — **второй** subtype, маппящийся в `operation_type = tax` (наряду с `TAX_RETAIN`), оба дают id `bph_tax_<externalSystemId>`. Формат id не содержит subtype, поэтому уникальность `externalSystemId` теперь требуется **поперёк subtype**, а не только внутри одного. Если BPH переиспользует `externalSystemId` между `TAX_RETAIN` и `MOEX_TAX`, две разные операции получат одинаковый id. Sibling-спека это фиксирует («HO не дедуплицирует по externalSystemId; уникальность — ответственность BPH»), а `bph-moex-tax` — нет. | contradiction | Major | resolved |
| CH-06 | §4.1.1 response `lead.subType` vs `lead.subtype` | Контракт ответа декларирует `lead.subType` [0-1] как «альтернативное поле подтипа (BPH может присылать subType вместо subtype)». Какой из полей участвует в матчинге пары `type\|subtype` из кэша? Если BPH пришлёт только `subType` (camelCase), риск неверного написания из CN-01 удваивается — а в §4.2.4 маппинг указан только по `lead.subtype`, `lead.subType` не упомянут. | contract-edge | Minor | covered |

## Данные и маппинг

| ID | § spec | Вопрос | Тип | Severity | Статус |
|----|--------|--------|-----|----------|--------|
| CH-07 | §4.2.3 bph (схема) vs §4.2.4 «Идемпотентность» | Миграция опирается на «уникальность `bph.subtype`» для идемпотентности (`INSERT ... WHERE NOT EXISTS`), но в схеме §4.2.3 у `bph.subtype` **нет UNIQUE-ограничения** (колонка `subtype | TEXT | NOT NULL`, ограничения «—»; UNIQUE только у `type.name`, `operation_type.name`, `status.name`). Если UNIQUE на `subtype` отсутствует, защита от дубля — только `WHERE NOT EXISTS`, который сам помечен «по образцу SIHIST-3321, **подтвердить**». Повторный прогон changeset может продублировать строку. | contradiction | Major | resolved |
| CH-08 | §4.2.4 «Application compatibility» (bootstrap JSON) vs DB INSERT | Маппинг заводится в **двух** местах: строки БД (`bph`/`operation`/`info`/`status_to_operation`) и bootstrap JSON `operation-cache.default-value`. Если они рассинхронизируются (пролили БД, но не обновили default-value, или наоборот), кэш поведёт себя по-разному в зависимости от того, загрузился ли он из БД или упал на default-value (`bc_active=false` vs реальные строки). Требование консистентности этих двух артефактов и проверка их согласованности не сформулированы. | data-edge | Minor | covered |
| CH-13 | §4.2.3 `operation.name`; §2 CN-05 | Для `MOEX_TAX` задаётся `operation.name = «Удержание налога MOEX»`, но `info.displayed_name = NULL`, а UI-заголовок карточки/деталки фиксирован «Удержание налога» (CN-05) без различия по subtype. Откуда в итоге берётся отображаемое название и где всплывает `operation.name`? Если `name` нигде не рендерится (displayed_name=NULL, заголовок фиксирован) — это dead data, и непонятно, зачем фиксировать текст «Удержание налога MOEX». | data-edge | Minor | covered |

## NFR, toggles, конфигурация / Ошибки и observability

| ID | § spec | Вопрос | Тип | Severity | Статус |
|----|--------|--------|-----|----------|--------|
| CH-03 | §1.3 постусловие «Неуспех (техн.)»; §2 CN-12; §6 coverage | Degraded-поведение (`bcDataComplete=false` при сбое BPH) описано только в постусловии и в CN-12; **отдельного alt-потока в use case нет** (alt-сценарии — только статус/watershed/additionalType). Кроме того: где именно выставляется `bcDataComplete`? history-ops — это источник BPH, а OG и BC — другие интеграции; признак «неполноты» логичнее выставляется на уровне композита (screen-api), который объединяет источники. Диаграмма (D-08) схлопывает МП/композит в одного участника и скрывает, кто мержит BPH+OG+BC и кто ставит флаг. Нет acceptance-теста на degraded-путь. | nfr-hole | Major | resolved |
| CH-09 | §4.1.1 «Ошибки и исключения»; §4.2.4 «Validation и rejection» | При `bc_id=NULL` фильтр `additionalType` и метрика `unexpected_additional_type_for_common_operation` **не срабатывают** (ранний return). Остальные негативные исходы тоже без события: «пара `type\|subtype` не найдена в кэше → no-op», «статус не настроен → без события». Итог: мис-конфигурация `MOEX_TAX` (неверное написание subtype, статус не `COMPLETE`, кэш не перезагружен) — **полностью молчаливая**, без метрики/алерта. CN-01 признаёт «налог молча не отобразится», но не предлагает ни observability, ни теста «настроено, но нет ни одного MOEX_TAX за период». | nfr-hole | Major | resolved |
| CH-10 | §2 CN-02; §4.2.4 «Application compatibility» | CN-02 фиксирует только направление «до включения BPH — no-op». Не зафиксирован **обратный порядок rollout**: кэш маппинга должен перезагрузиться (INSERT + reload `operation-cache`) **до** того, как BPH начнёт отдавать `MOEX_TAX`. Если BPH включится раньше перезагрузки кэша, lead придёт, но пары `TAXES\|MOEX_TAX` в кэше нет → no-op, налог молча потерян, без ошибки и метрики (см. CH-09). Порядок развёртывания «INSERT → перезагрузка кэша → go-live BPH» в §4.2.4 не утверждён как обязательный. | nfr-hole | Major | resolved |

## Ошибки и observability / Миграция

| ID | § spec | Вопрос | Тип | Severity | Статус |
|----|--------|--------|-----|----------|--------|
| CH-14 | §4.2.4 «Rollback»; §4.2.3 ER-диаграмма | Откат после пролива описан как «DELETE вставленных строк по PK» с пометкой «Удаление `bph` каскадно затрагивает `operation`/`info`/`status_to_operation` — порядок по FK». Но в ER-диаграмме и таблицах §4.2.3 FK заданы как `FK → id` **без ON DELETE CASCADE**. Противоречие: либо CASCADE есть (тогда DELETE `bph` молча удалит дочерние строки — в т.ч. чужие, если id пересечётся), либо его нет (тогда DELETE `bph` упадёт по FK, пока не удалены `info`→`status_to_operation`→`operation`). Точный порядок DELETE и наличие CASCADE не зафиксированы; откат «до пролива» сведён к «зависит от Liquibase tag/rollback». | contradiction | Major | resolved |

## Тесты и приёмка

| ID | § spec | Вопрос | Тип | Severity | Статус |
|----|--------|--------|-----|----------|--------|
| CH-11 | §4.1.1 request `additionalTypes`; §6 coverage matrix | Нет теста, проверяющего **состав запроса** к BPH для `MOEX_TAX`: что элемент `subtypesAndStatuses[]` содержит `{type=TAXES, subtype=MOEX_TAX, statuses=[COMPLETE]}` и **опускает** `additionalTypes` (CN-08). ACC-001/ACC-004 проверяют только результат маппинга, не сам запрос. Отсутствие `additionalTypes` в запросе означает «BPH вернёт все additionalType-варианты MOEX_TAX» — это поведение нигде не протестировано на уровне request-building. | test-gap | Minor | covered |
| CH-12 | §4.1.1 «Связанные разделы»; §4.2.3/§4.2.4 «Связанные артефакты» | Трижды ссылается на «§4.2.2 «Алгоритм обработки» (формирование `subtypesAndStatuses`/`additionalTypes`, фильтрация leads, watershed)», но такой titled-секции в документе нет: алгоритм размазан по BR-06…BR-13 внутри use case «Обработать налоговую операцию MOEX_TAX», а формирование запроса — в §4.1.1. Dangling cross-reference и отсутствие единого места, где целиком описан конвейер «кэш → запрос → фильтрация → маппинг». | missing-flow | Minor | covered |

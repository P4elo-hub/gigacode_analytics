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
- Вопросов: 19 (Critical: 3 · Major: 9 · Minor: 7)
- Фокус прогона: полная ненаблюдаемость тихих отказов при `bc_id=NULL`; неразличимость `MOEX_TAX` от `TAX_RETAIN` в ленте; blast radius нераспознанного enum в общем запросе `subtypesAndStatuses`; ловушка `additional_type` NULL vs пустая строка; кросспековое противоречие значений `name`/`comment` с sibling `bph-portfolio-size-tax`; прод-id/rollback при deferred id (D-10).

## Бизнес-логика и use case

| ID | § spec | Вопрос | Тип | Severity | Статус |
|----|--------|--------|-----|----------|--------|
| CH-01 | §1.1 BR-02, §4.2.3, §4.3 | `MOEX_TAX` получает `comment`=«Удержание суммы налога» (D-02) **и** `operation.name`=«Удержание суммы налога» (D-06), при этом `operation_type=tax` — все три значения идентичны `TAX_RETAIN`. В ленте клиент не сможет отличить «налог MOEX» от обычного удержания налога: ни по типу, ни по тексту, ни по заголовку. Бриф фиксировал отличие именно как «другой comment». Осознанное ли это решение «MOEX_TAX визуально тождествен TAX_RETAIN», или «другой comment» из брифа фактически не выполнен? | contradiction | Critical | resolved |
| CH-02 | §1.1 BR-02, §4.2.3 vs `bph-portfolio-size-tax-challenges.md` CH-09 | Соседний банк `bph-portfolio-size-tax` (CH-09) фиксирует для `MOEX_TAX` иные значения: `operation.name`=«Удержание налога MOEX», `info.comment`=«НАЛОГ МОСКОВСКОЙ БИРЖИ» (name ≠ comment), тогда как эта spec (D-02/D-06) задаёт оба =«Удержание суммы налога». Это признак, что «другой comment» из брифа имел конкретное отличное значение, которое перекрыто переиспользованием формулировки `TAX_RETAIN`. Какое значение authoritative, и не спроектирует ли sibling-фича (общая зона id/таблиц по CN-06) по устаревшим значениям? | contradiction | Major | resolved |
| CH-03 | §4.2.4 (поле `id`), §1.3 | Маппинг `id = bph_{operation_type}_{externalSystemId}`; поведение при повторной отдаче/коррекции не описано. В отличие от sibling `bph-portfolio-size-tax` (BR-03 «HO не дедуплицирует, уникальность — ответственность BPH»), здесь дедупликация по `externalSystemId` не зафиксирована вовсе. Если BPH вернёт две операции `MOEX_TAX` с одинаковым `externalSystemId`, в SEND_OPERATIONS появится дубль по id. Есть ли дедупликация и кто её гарантирует? | scope-ambiguity | Major | resolved |

## Контракты и интеграции

| ID | § spec | Вопрос | Тип | Severity | Статус |
|----|--------|--------|-----|----------|--------|
| CH-04 | §4.1.1, §1.3 шаг 2, §1.2 (partial failure) | `subtypesAndStatuses[]` — один запрос, содержащий И `TAX_RETAIN`, И `TAX_REFUND_BROK_ACCOUNT`, И новый `MOEX_TAX`. Проверено ли, что BPH на нераспознанный `subtype=MOEX_TAX` **игнорирует** элемент массива (а не отвечает 400/500 на весь запрос)? Если BPH отклонит весь запрос из-за ещё не включённого на его стороне `MOEX_TAX`, то упадут и существующие налоги `TAX_RETAIN`/`TAX_REFUND_BROK_ACCOUNT` — blast radius шире data-only фичи. | integration-edge | Critical | resolved |
| CH-05 | §4.2.4 (field mapping `currency`) vs §4.1.1 (`OperationData`) | В таблице маппинга `currency ← lead.currency`, но в перечне полей `OperationData` (§4.1.1) поля верхнего уровня `currency` нет — валюта есть только внутри `price`, `totalPrice` и `instrument`. Откуда реально берётся `currency` для `MOEX_TAX` (`totalPrice.currency`? `instrument.currency`?) и не противоречит ли секция сама себе? | contradiction | Minor | covered |
| CH-06 | §4.1.1 (примечание «два имени») | У поля подтипа в контракте два имени — `subType` и `subtype`, «HO читает оба». Относится ли чтение обоих имён и к ключу lookup `operation` (`originalType + bphType`), и какое из двух имён фактически заполняет BPH для `MOEX_TAX`? Если lookup читает только одно имя, а BPH заполняет другое, операция молча не сматчится. | contract-edge | Minor | covered |
| CH-07 | §4.1.1 (коды ответов) vs §5.3.2 (`dataCompleteFalse`) | §4.1.1 различает `status.code ≠ 0` (business error → «не включаются», partial failure) и HTTP 400/500 («источник помечается failed»); §5.3.2 описывает метрику `dataCompleteFalse` как «Partial failure — при HTTP-ошибке ИЛИ `status.code ≠ 0`». Что происходит с остальными налогами `TAX_RETAIN` при `status.code ≠ 0` в общем ответе: выпадает весь источник BPH или только проблемные операции? Семантика важна для `MOEX_TAX` (одна ошибка в ответе не должна ронять существующие налоги). | contradiction | Minor | covered |

## Данные и маппинг

| ID | § spec | Вопрос | Тип | Severity | Статус |
|----|--------|--------|-----|----------|--------|
| CH-08 | §4.2.3 (info), CN-08, §4.2.4 | Маппинг требует `info.additional_type = NULL` (тогда `filter(Objects::nonNull)` отбрасывает и `additionalTypes[]` не передаётся). Но `Objects::nonNull` пропускает **пустую строку** `''`: если DBA при проливе укажет `additional_type = ''` вместо NULL, в запрос уйдёт `additionalTypes: [""]`, а матчинг `"" == ""` против `lead.additionalType` (`""` при null) может дать ложное срабатывание/поведение BPH. Зафиксировано ли требование «именно NULL, не `''`» и есть ли валидация на это? | data-edge | Major | resolved |
| CH-09 | §4.2.3 (info), §4.2.4 (`operationDisplayName`) | `info.displayed_name = NULL` (универсальный паттерн) → исходящий `operationDisplayName = NULL`. При этом `operation.name`=«Удержание суммы налога» совпадает с `TAX_RETAIN`. Какой текст реально показывает клиент в заголовке карточки/деталки для `MOEX_TAX`: `operation.name` как fallback при `displayed_name=NULL`? Если да — заголовок тождествен `TAX_RETAIN` и неотличим (усиливает CH-01); если fallback отсутствует — заголовок может быть пустым. Где описан этот fallback? | data-edge | Major | resolved |
| CH-10 | §4.3 (Scope и id), CN-06 | Стратегия назначения id новых строк не зафиксирована: changeset задаёт id явно (как прецедент SIHIST-3321) или опускает (SERIAL/sequence авто)? CN-06 требует «id не пересекаются с `bph-portfolio-size-tax`», но оба id отложены на DBA (D-10) без механизма контроля. При явных id и независимом проливе двух changeset коллизия не будет поймана ни FK, ни pre-check. Как гарантируется непересечение? | data-edge | Major | resolved |
| CH-11 | §4.2.2 alt 4a/4b, CN-09 | При non-null `lead.additionalType`, не совпавшем с `info.additional_type=NULL`, `comment`/`displayed_name` не подставляются (alt 4a); fallback `accComment` действует только при **пустом** `info.comment` (alt 4b), а не при несматченном `additionalType`. Если и `accComment` пуст/отсутствует, операция `MOEX_TAX` уйдёт в ленту вообще без комментария — и без какого-либо сигнала. Допустим ли налог без текста в ленте, и нужна ли защита от «без коммента»? | missing-flow | Major | resolved |
| CH-12 | §4.2.4 (field mapping `totalSum`) | `totalSum ← abs(totalPrice)`: удержание налога (`totalPrice` отрицательное, напр. `-12000.00`) будет показано клиенту как положительное значение `12000.00`. Для «удержания» знак семантически значим. Подтверждено ли, что `abs()` — желаемая презентация именно для налога-удержания `MOEX_TAX`, а не артефакт универсального маппинга? | data-edge | Minor | covered |
| CH-13 | §4.2.3 (bph), §4.3 (pre-check) | У таблицы `bph` колонка `subtype` не имеет UNIQUE-ограничения (в ER только `type.name`/`operation_type.name` UNIQUE). Идемпотентность держится только на pre-check «0 строк с `subtype=MOEX_TAX`». Если DBA прольёт changeset дважды (или при откате не удалит строку), появятся две строки `bph(subtype=MOEX_TAX)` с разными id → lookup `operation` по subtype станет неоднозначным. Нужен ли UNIQUE на `bph.subtype` или иной способ защиты от дубля? | data-edge | Minor | resolved |

## NFR, toggles, конфигурация

| ID | § spec | Вопрос | Тип | Severity | Статус |
|----|--------|--------|-----|----------|--------|
| CH-14 | CN-02, §5.3.1 (cron-обновление кэша) | Кэш маппинга обновляется cron (`bd_response_cron_time`, default 60 мин); при SQL-ошибке кэш **не перезаписывается**. Между проливом changeset и успешным обновлением кэша `MOEX_TAX` молча отсутствует; если обновление кэша стабильно падает, строки есть в БД, но в рантайме их нет — и нет ни алерта, ни метрики «строки в БД ≠ строкам в кэше». D-09 отложил только «cron vs ручной прогрев», но не детекцию сбоя обновления кэша. Как обнаруживается рассинхрон БД↔кэш? | nfr-hole | Major | resolved |
| CH-15 | §5.3.2 (метрики ошибок) | Единственная метрика на неожиданный `additionalType` — `unexpected_additional_type_for_common_operation` — явно **не инкрементится** для `bc_id=NULL` (ранний `return true`). Других per-subtype метрик нет: нет счётчика «получено `MOEX_TAX` операций», «смапплено», «отфильтровано». Любая ошибка конфигурации (неверное написание в БД, отсутствующая `status_to_operation`, статус ≠ COMPLETE) даёт **полное молчание** — невозможно отличить «MOEX_TAX не было операций» от «MOEX_TAX сломан». Чем подтверждается в проде, что фича реально заработала? | nfr-hole | Critical | resolved |
| CH-16 | §4.3 (риск «Написание MOEX_TAX»), CN-04 | Риск «написание `MOEX_TAX` не совпадает с контрактом BPH» помечен `resolved (D-01)`, хотя D-01 — это подтверждение пользователем значения «как в брифе», а не пруф из контракта BPH: в `analytics/`/`repositories/`/`db-export/` 0 совпадений, и §4.3 pre-check всё ещё помечен `Blocking: yes` («сверить с контрактом BPH»). Статус «resolved» маскирует остаточный риск «silent no-op при неверном написании». Не следует ли статус риска оставить «open до pre-check», чтобы его не списали раньше времени? | nfr-hole | Major | covered |

## Ошибки и observability

| ID | § spec | Вопрос | Тип | Severity | Статус |
|----|--------|--------|-----|----------|--------|
| CH-17 | §5.3.1 (rsStr, маскирование) | Тело ответа `rsStr` пишется в `integration.log` целиком и теперь содержит операции `MOEX_TAX` с `agreement`, `account`, `ucpId`, `externalSystemId`. Перечень маскируемых полей для `GET_OPERATIONS_WITH_DETAILS` отложен (D-12, `log_masking_rules.yml`). Подтверждено ли field-level, что именно новые `MOEX_TAX`-поля ответа попадают под правило маскирования, или новый subtype потенциально пишет в лог незамаскированные PII (`agreement`/`ucpId`)? | nfr-hole | Minor | deferred |

## Тесты и приёмка

| ID | § spec | Вопрос | Тип | Severity | Статус |
|----|--------|--------|-----|----------|--------|
| CH-18 | §4.3 (Validation) | Validation §4.3 состоит только из SQL-lookup и проверки shape кэш-строки; **не заданы негативные тестовые фикстуры** (ответ BPH с non-null `additionalType`, статус ≠ `COMPLETE`, отсутствие `MOEX_TAX` в кэше, пустой `info.comment`+пустой `accComment`). Sibling `bph-portfolio-size-tax` явно фиксирует обновление тестовых фикстур (`bph_request_all_completed.json` и негатив «неизвестный additionalType»). Здесь негативные сценарии alt 4a/4b/5a описаны в use case, но не переведены в проверяемые тест-кейсы. Какие негативные тесты обязательны? | test-gap | Major | resolved |
| CH-19 | §4.3 (Validation), §1.1 (SMART Measurable) | Приёмка останавливается на уровне данных (SQL + shape кэша) и не содержит end-to-end критерия: gRPC `SEND_OPERATIONS` реально содержит операцию `MOEX_TAX` с `type=tax`, `comment=«Удержание суммы налога»`, `general_status=executed`. SMART-цель уже признана non-SMART (D-07). По какому воспроизводимому критерию фича признаётся «работает» в проде (учитывая отсутствие метрики из CH-15)? | test-gap | Minor | resolved |

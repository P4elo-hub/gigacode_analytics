---
report_type: feature-challenges
slug: bph-portfolio-size-tax
source_document: Feature-writing/bph-portfolio-size-tax/bph-portfolio-size-tax.md
generated_at: 2026-10-06
challenge_iteration: 1
language: ru
---

# Критический разбор: bph-portfolio-size-tax

**Спецификация:** `Feature-writing/bph-portfolio-size-tax/bph-portfolio-size-tax.md`
**Банк вопросов:** `Feature-writing/bph-portfolio-size-tax/bph-portfolio-size-tax-challenges.md`

## Сводка
- Вопросов: 16 (Critical: 1 · Major: 10 · Minor: 5)
- Фокус прогона: полная ненаблюдаемость тихих отказов при `bc_id=NULL`; коллизия исходящего `id` между подтипами, маппящимися в `tax`; противоречие источника `accComment` (lead vs details); пустой заголовок карточки при `displayed_name=NULL`; blast radius нераспознанного `subtype`; сторно/корректирующие операции со статусом ≠ `COMPLETE`.

## Бизнес-логика и use case

| ID | § spec | Вопрос | Тип | Severity | Статус |
|----|--------|--------|-----|----------|--------|
| CH-01 | §1.1 BR-02, CN-04, §4.2.2 BR-09 | BR-02 фиксирует «налог взимается **отдельно по каждой операции** (не агрегированно)», а порог «от 5 000 000 ₽» — это условие **по портфелю** (CN-04, на стороне BPH). Спецификация нигде не определяет, что является «операцией» для налога за размер портфеля (разовое удержание при пересечении порога? периодическое списание? сторно при снижении портфеля ниже порога?). HO маппит пришедшее «как есть» и не может верифицировать ни порог, ни «отдельно по каждой операции». Как BR-02 вообще проверяется в приёмке, если единственный потребительский критерий — data-level (SQL + shape кэша + позитивный тест)? | scope-ambiguity | Major | resolved |
| CH-02 | §1.3 alt 4a/4b, §4.2.4 `comment` | Fallback `lead.accComment` для `TAXES` срабатывает **только** при пустом `info.comment` (alt 4b), а при несматченном `additionalType` (alt 4a) `comment` не подставляется вовсе. Если одновременно `info.comment` пуст **и** `accComment` отсутствует/пуст, операция `PORTFOLIO_SIZE_TAX` уйдёт в ленту вообще без текста — и без какого-либо сигнала (нет метрики, нет лога). Допустим ли налог без текста в ленте, и нужна ли защита от «без коммента»? | missing-flow | Major | resolved |
| CH-03 | §1.3 BR-07, CN-03, §4.2.2 шаг 3 | Для налога, взимаемого «отдельно по каждой операции», корректировки/сторно (возврат ошибочно удержанного налога, отмена при снижении портфеля ниже порога) могут приходить отдельной операцией с **другим** BPH-статусом (например `CANCELED`/`REVERSED`). Статус-членство `statusMap.containsKey(status)` жёсткое: добавлена только связка `status=COMPLETE`. Такая операция молча отфильтруется — клиент увидит удержание, но никогда не увидит его отмену. Как обрабатываются корректирующие/сторнирующие операции налога за размер портфеля? | missing-flow | Major | resolved |

## Контракты и интеграции

| ID | § spec | Вопрос | Тип | Severity | Статус |
|----|--------|--------|-----|----------|--------|
| CH-04 | §4.1.1, CN-11 | CN-11 декларирует допущение «BPH игнорирует нераспознанные `subtype` внутри `subtypesAndStatuses` и не отвечает 400/500 на весь запрос», но закрепляет только «требуется pre-check». Не задан **принимаемый критерий** этого pre-check: что именно должно быть подтверждено командой BPH (реальный прогон с нераспознанным subtype? ответ 200 с пустым `data`?), и что делать, если BPH на практике отклоняет весь запрос — тогда упадут и существующие `TAX_RETAIN`/`TAX_REFUND_BROK_ACCOUNT` (blast radius шире data-only фичи). Чем верифицируется CN-11 до пролива? | integration-edge | Major | resolved |
| CH-05 | §4.1.1 (details/SUPPORTED_DETAILS_KEY) vs §4.2.4 / BR-05 (`lead.accComment`) | §4.1.1 относит `accComment` к ключам массива `details[]` (`BphConverter.SUPPORTED_DETAILS_KEY`, наряду с `comment`/`errorCode`/`statusErrorCode`), а в перечне полей `OperationData` (`lead`) поля `accComment` **нет**. При этом BR-05/CN-09/§4.2.4 повсеместно называют fallback «`lead.accComment`», и пример JSON в §4.2.4 помещает `"accComment"` как прямой атрибут объекта `source` (= `lead`). Откуда реально берётся `accComment` для fallback — из `lead` или из `details[]`? Если fallback читает поле, которого нет в `lead`, он никогда не сработает и налог при пустом `info.comment` останется без текста. | contradiction | Major | covered |
| CH-06 | §4.1.1 (partial conversion) vs §4.2.4 (`validateSimpleAttributes`) | §4.1.1 утверждает «ошибки конвертации отдельной записи фиксируются метрикой `parse_error` и не роняют остальные операции», но `validateSimpleAttributes()` требует обязательные `type`/`subtype`/`formationDate`/`eventDate`/`externalSystemId`/`status`/`agreement` через `checkNotNull`. Что происходит, если BPH пришлёт `PORTFOLIO_SIZE_TAX` без одного из обязательных полей (новый subtype команда BPH может заполнять не полностью): падает вся пачка ответа или только эта запись? Для нового подтипа это критично — одна «недооформленная» операция не должна ронять существующие налоги. | missing-flow | Major | covered |

## Данные и маппинг

| ID | § spec | Вопрос | Тип | Severity | Статус |
|----|--------|--------|-----|----------|--------|
| CH-07 | §4.2.4 `id` | Исходящий `id = bph_{operation_type}_{externalSystemId}`, где `operation_type` — целевой `tax`, а **не** subtype. Т.е. `TAX_RETAIN`, `MOEX_TAX` (sibling) и новый `PORTFOLIO_SIZE_TAX` делят одно id-пространство `bph_tax_{externalSystemId}`. Если BPH гарантирует уникальность `externalSystemId` только **внутри** подтипа (сквозной счётчик на подтип), два разных налога с одинаковым `externalSystemId` дадут одинаковый `id` → дедупликация в Ignite-кэше молча отбросит одну из операций. Уникальность `externalSystemId` глобальная или per-subtype, и чем это подтверждено? | corner-case | Major | resolved |
| CH-08 | §4.2.4 `operationDisplayName`, §4.2.3 `operation`, D-08 | D-08 задаёт `operation.name` = «Налог за размер портфеля», `info.displayed_name` = NULL «по паттерну». При этом §4.2.4 явно фиксирует: «Fallback на `operation.name` при `displayed_name = NULL` в HO-конвертере **отсутствует** (прямое присваивание без fallback)». Следствие: `operationDisplayName` = NULL, а непустой `operation.name` может вообще не использоваться. Что клиент реально видит в заголовке карточки/деталки — пустое значение или есть другой consumer `operation.name`? Если заголовок пуст, решение D-08 по `operation.name` не достигает цели. | contradiction | Major | resolved |
| CH-09 | §4.1.1 (`eventDate` Nullable=Нет, `checkNotNull`) vs §4.2.4 (`timeClosed` Nullable) | В §4.1.1 поле `eventDate` объявлено обязательным (Nullable=Нет, `validateSimpleAttributes → checkNotNull`), а в §4.2.4 target `timeClosed ← lead.eventDate` помечен «Nullable». Если `eventDate` обязателен на входе, `timeClosed` не может быть null — одно из двух утверждений неверно. Какое из них актуально для нового подтипа? | contradiction | Minor | covered |
| CH-10 | §4.2.4 (`Lookup ... по bphType+bphSubtype`) vs §4.1.1/§4.2.2 (`originalType + bphType`) | В §4.2.4 ключ lookup `operation` назван «`bphType`+`bphSubtype`», тогда как во всех остальных разделах (и в `CONTEXT_DOC`) — «`originalType` + `bphType`» (`originalType` = `lead.type` = `TAXES`, `bphType` = `lead.subtype`). Терминологическая несогласованность ключа маппинга может ввести реализатора/тест в заблуждение относительно того, какие именно два поля образуют ключ. Какое написание ключа authoritative? | contradiction | Minor | covered |
| CH-11 | §2 CN-06 vs sibling `bph-moex-tax` | Обе фичи — data-only INSERT в **одни и те же** таблицы (`bph`/`operation`/`info`/`status_to_operation`), обе в одну зону id. CN-06 заявляет «id назначаются SERIAL/sequence автоматически (INSERT без явного id)», но sibling `bph-moex-tax` в своём цикле resolve **отложил назначение id на DBA** (D-10/D-20). Если DBA для sibling-фичи пропишет явные id, а этот changeset полагается на sequence — коллизия не будет поймана ни FK, ни pre-check «0 строк по subtype» (он проверяет только `PORTFOLIO_SIZE_TAX`, не пересечение с `MOEX_TAX`). Кто и чем гарантирует непересечение id между двумя фичами при независимом проливе? | data-edge | Minor | resolved |

## NFR, toggles, конфигурация

| ID | § spec | Вопрос | Тип | Severity | Статус |
|----|--------|--------|-----|----------|--------|
| CH-12 | §5.3.2, CN-03, BR-10 | Единственная метрика на неожиданный `additionalType` — `unexpected_additional_type_for_common_operation` — явно **не инкрементится** при `bc_id=NULL` (ранний `return true`). Per-subtype метрик нет: нет счётчика «получено операций `PORTFOLIO_SIZE_TAX`», «смапплено», «отфильтровано». Любая ошибка конфигурации (неверное написание в БД, отсутствующая `status_to_operation`, статус ≠ `COMPLETE`) даёт **полное молчание**: невозможно отличить «операций `PORTFOLIO_SIZE_TAX` не было» от «фича сломана». Чем в проде подтверждается, что фича реально заработала (учитывая non-SMART приёмку на уровне данных)? | nfr-hole | Critical | resolved |
| CH-13 | §7.1.7, CN-02, §5.3.1 | Кэш маппинга обновляется cron-ом; при SQL-ошибке кэш **не перезаписывается** (остаётся последнее валидное состояние). Между проливом changeset и успешным обновлением кэша `PORTFOLIO_SIZE_TAX` молча отсутствует; при стабильном сбое cron строки есть в БД, а в рантайме — нет, и нет ни алерта, ни метрики «строки в БД ≠ строкам в кэше». Как обнаруживается рассинхрон БД↔кэш (не разовый лаг `update-delay-ms`, а именно сбой перезагрузки)? | nfr-hole | Major | resolved |
| CH-14 | §Конфигурация, CN-13, §Тогглы | Процедура отката фичи не определена явно: §Тогглы описывает «OFF» через `bph.is_active=false` (строка остаётся), но CN-13 предупреждает, что «двойной пролив (или откат без удаления) → две строки `bph` → lookup `operation` по subtype неоднозначен». Что является откатом: down-migration (DELETE строк) или только `is_active=false`? Если `is_active=false` и затем повторный пролив — не создаст ли это вторую активную строку `bph`? | missing-flow | Minor | resolved |

## Тесты и приёмка

| ID | § spec | Вопрос | Тип | Severity | Статус |
|----|--------|--------|-----|----------|--------|
| CH-15 | §5.3.2 (non-SMART), §4.2.4 (Validation) | Приёмка/Validation состоят из SQL-lookup + проверки shape кэш-строки + **позитивного** интеграционного теста. Не заданы **негативные** тест-фикстуры: ответ BPH с non-null `additionalType` (матчинг `"" == ""` не срабатывает), статус ≠ `COMPLETE`, отсутствие связки `status_to_operation`, пустой `info.comment` + пустой `accComment`. Альтернативные сценарии alt 4a/4b/6a описаны в use case, но не переведены в проверяемые тест-кейсы. Какие негативные тесты обязательны для `PORTFOLIO_SIZE_TAX`? | test-gap | Major | resolved |
| CH-16 | §1.1 (SMART Measurable), §5.3.2 | Приёмка останавливается на уровне данных (SQL + shape кэша + позитивный тест) и не содержит end-to-end критерия: gRPC `SEND_OPERATIONS` реально содержит операцию `PORTFOLIO_SIZE_TAX` с `type=tax`, `comment=«Налог за размер портфеля»`, `general_status=executed`. SMART-цель уже признана non-SMART. По какому воспроизводимому критерию фича признаётся «работает» в проде, если метрики уровня «операция смапплена» нет (CH-12)? | test-gap | Minor | resolved |

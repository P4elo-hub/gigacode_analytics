---
report_type: feature-challenges
slug: bph-portfolio-size-tax
source_document: Feature-writing/bph-portfolio-size-tax/bph-portfolio-size-tax.md
generated_at: 2026-08-30
challenge_iteration: 2
language: ru
---

# Критический разбор: bph-portfolio-size-tax

**Спецификация:** `Feature-writing/bph-portfolio-size-tax/bph-portfolio-size-tax.md`
**Банк вопросов:** `Feature-writing/bph-portfolio-size-tax/bph-portfolio-size-tax-challenges.md`

## Сводка
- Вопросов: 17 (Critical: 1 · Major: 10 · Minor: 6)
- Прогон 2 (инкремент): SPEC пересоздан (mtime 2026-08-30 00:39), банк прогона 1 (2026-08-29 21:37) устарел. CH-01…CH-11 переоценены против нового текста (статусы подтверждены, §-ссылки уточнены), добавлены CH-12…CH-17 по новым областям переписанного SPEC.
- Фокус прогона: прод-id/rollback против динамических id; полная ненаблюдаемость тихих отказов при `bc_id=NULL`; меж-subtype коллизия `id`; blast radius нераспознанного enum; удаление раздела тестов §4.2.4; UX-заголовок «Удержание налога».

## Бизнес-логика и use case

| ID | § spec | Вопрос | Тип | Severity | Статус |
|----|--------|--------|-----|----------|--------|
| CH-07 | §4.1.1, BR-03 | BR-03 фиксирует «взимается отдельно по каждой операции (не агрегированно)», но поведение при повторной отдаче/коррекции не описано: если BPH вернёт две операции с одинаковым `externalSystemId` (идемпотентный re-send или коррекция), обе смаппятся в `id = bph_tax_{externalSystemId}` и в SEND_OPERATIONS появится дубль по id. Есть ли дедупликация по `externalSystemId` и кто её гарантирует — HO или BPH? Q-10 в контекст-доке остаётся открытым. | corner-case | Major | resolved |
| CH-08 | §BR-02 | BR-02 декларирует порог «от 5 000 000 ₽» как условие на стороне BPH, и «фильтра по порогу в HO нет». Если BPH (баг/смена порога) пришлёт `PORTFOLIO_SIZE_TAX` для портфеля < 5 млн, HO покажет налог безусловно и без какого-либо признака. Кто/как контролирует, что в ленту не попадают взимания ниже порога, и нужна ли метрика/алерт на такие операции? | scope-ambiguity | Minor | resolved |
| CH-09 | §4.2.3 (примеч.) | `operation.name` и `info.comment` заданы одинаковым текстом «Налог за размер портфеля», тогда как в аналоге MOEX_TAX `operation.name` («Удержание налога MOEX») ≠ `info.comment` («НАЛОГ МОСКОВСКОЙ БИРЖИ»). Какой из двух текстов попадает в `operation_name` кэша (`application-test.yml`) и на деталку, а какой — в `comment` ленты? Совпадение текстов здесь случайно-допустимо или маскирует, что `operation_name` для кэша не задан в §4.2.4? | data-edge | Minor | covered |
| CH-10 | §BR-05, §1.3 alt 5a | BR-05/alt 5a описывают fallback «пустой `info.comment` → `details.accComment`» (правило кода `BphCommonClientConverter`), а SIHIST-3476 (источник BR-05) описывает водораздельное правило «после watershed — `info.comment`, до — `accComment`». Для нового subtype с непустым `info.comment` fallback фактически мёртв. Какое правило актуально для `PORTFOLIO_SIZE_TAX` и не противоречит ли формулировка BR-05 источнику SIHIST-3476? | contradiction | Minor | covered |
| CH-17 | CN-02, CN-03, §1.3 | CN-02/CN-03 фиксируют «МП и композит BDUI не изменяются», «тот же `type=tax`, та же деталка `HISTORY_OPS_TAX_DETAILS_SCREEN`». Но заголовок карточки/деталки налога захардкожен как «Удержание налога» (`TaxSectionCreator.titleText("Удержание налога")`, `HistoryOperationTaxDetailsHeaderSection.defaultTitleName("Удержание налога")`). Для «налога за размер портфеля» клиент увидит в ленте заголовок «Удержание налога» при comment «Налог за размер портфеля» — семантически неверный заголовок. Допустимо ли это по CN-02 (осознанное решение «заголовок не различаем по subtype»), и кто это подтвердил? | scope-ambiguity | Minor | open |

## Контракты и интеграции

| ID | § spec | Вопрос | Тип | Severity | Статус |
|----|--------|--------|-----|----------|--------|
| CH-02 | §4.1.1, §4.2.3 | Строки `PORTFOLIO_SIZE_TAX` и `PORTFOLIO_AMOUNT_TAX` фиксируются как «новые значения», но grep по `repositories/`, `analytics/`, `db-export/` даёт **0 совпадений** — значение не существует ни в одном артефакте воркспейса (Q-01/Q-04 закрыты из брифа, без контрактного пруфа). При неверном `subtype`/`additionalType` фича молча не покажет налог (запросный фильтр `additionalTypes` на стороне BPH вернёт пусто). Как будет верифицировано точное написание enum против реального контракта BPH до пролива, и где фиксируется этот пруф? | contract-edge | Major | resolved |
| CH-15 | §2 чекпойнт 2, §4.1.1, §4.2.2.2 п.4 | §2 чекпойнт 2 и §4.2.2.2 п.4 предполагают, что при неверном `PORTFOLIO_SIZE_TAX`/`PORTFOLIO_AMOUNT_TAX` BPH «вернёт пусто» (запросный фильтр `additionalTypes` отфильтрует, фича молча не покажет налог). Но `subtypesAndStatuses[]` в одном запросе содержит И `TAX_RETAIN`, И `PORTFOLIO_SIZE_TAX` (§4.1.1, пример). Если BPH на нераспознанный subtype/additionalType ответит 400/500 (а не молча пропустит элемент массива), упадёт ВЕСЬ запрос — и существующие `TAX_RETAIN` перестанут отображаться (blast radius шире фичи). Проверено ли, что BPH игнорирует (а не отклоняет) неизвестный subtype внутри `subtypesAndStatuses`, и что происходит с остальными налогами при ошибочном enum? | integration-edge | Major | open |

## Данные и маппинг

| ID | § spec | Вопрос | Тип | Severity | Статус |
|----|--------|--------|-----|----------|--------|
| CH-01 | §4.2.2.2, §1.3 alt 4a | В `BphBcFilterService.isActualBphOperation()` (код, строки 181–196) при `optionalOperationByBph.isPresent()` и отсутствии BC-контекста (`hasBcContext = bcType != null && bcSubtype != null` = `false`, т.к. `bc_id=NULL` из AS-03) выполняется ранний `return true` — проверки watershed (`formationDate` vs `historyStart`), `additionalType ∈ info.additional_type` и статуса пропускаются, лог+метрика из alt 4a/§5.3 не срабатывают. §4.2.2.2 (шаги 2–4) и alt 4a описывают фильтрацию, которая для `bc_id=NULL` фактически не выполняется: операция с неожиданным `additionalType` (вплоть до `NULL`) попадёт в SEND_OPERATIONS с пустым/accComment-комментарием. Что истинно для `PORTFOLIO_SIZE_TAX`: фильтр есть (тогда spec противоречит коду) или его нет (тогда §4.2.2.2/alt 4a/§5.3 надо править)? | contradiction | Critical | resolved |
| CH-03 | §4.2.3 | Тестовые id (bph=22, operation=24, info=52, status_to_operation=37) и прод-«следующие» (25/27/79/57) в §4.2.3 **дословно совпадают** с §4.2.3 sibling-spec `bph-moex-tax` (тот же `bph_id=22`, `operation_id=24`, `info_id=52`, `status_to_operation_id=37`). Оба changeset INSERTят в один `create_schema.sql` — при уже пролитом MOEX_TAX второй INSERT упадёт по PK. Какая из двух фич занимает эти id и как развести тестовые (и прод) id, если обе реализуются? | contradiction | Major | resolved |
| CH-12 | §4.2.3 | Миграция (Liquibase changeset) содержит жёстко зашитые id (`VALUES (23,…)`, `(25,…)`, `(53,…)`, `(38,…)`) и rollback `DELETE … WHERE id=38/53/25/23`. Но там же «Prod / стенды» предписано не использовать черновые test-id и брать `SELECT max(id)+1` (или INSERT без id + FK по business key `subtype` / `bph_type+subtype`). Один и тот же changeset не может одновременно работать с зашитыми id (test) и динамическими (prod): если прокатить его как есть на prod — он упадёт по PK (id 25/27/79/57 уже заняты `bph-moex-tax`) либо займёт чужие id; если сделать id динамическими — rollback по `id=38` не найдёт строку. Какая стратегия id/rollback финальная для prod, и почему rollback зашит на test-id? | contradiction | Major | open |
| CH-14 | §4.1.1, §4.2.2 «Дедупликация», BR-03 | `id = bph_tax_<externalSystemId>` (§4.1.1; `BphCommonClientConverter` `"bph_%s_%s"` по `operationType`) не включает `subtype`. Дедупликация по Ignite — по `id` (§4.2.2). Если BPH использует `externalSystemId` с областью уникальности только внутри subtype (а не глобально), то `TAX_RETAIN` и `PORTFOLIO_SIZE_TAX` с одинаковым `externalSystemId` дадут одинаковый `id = bph_tax_<…>`, и сверка с кэшем Ignite отбросит вторую операцию как дубль — налог за размер портфеля молча пропадёт. BR-03/Q-10 фиксируют уникальность `externalSystemId` только «в одном ответе»; кто гарантирует меж-subtype уникальность и чем она проверяется? | corner-case | Major | open |

## NFR, toggles, конфигурация

| ID | § spec | Вопрос | Тип | Severity | Статус |
|----|--------|--------|-----|----------|--------|
| CH-04 | §2, §5.4, §1.3 alt 2a | Watershed берётся из ответа BPH `GET_OPERATION_TYPES` (ключ `TAXES|PORTFOLIO_SIZE_TAX`), «ручная настройка HO не требуется». Если BPH не вернёт этот ключ (`historyStart` отсутствует), alt 2a описывает только «операции не запрашиваются/не показываются» — без метрики/алерта и без различия «ещё не настроено» vs «сломано». Как сопровождение узнает, что в БД есть `bph_active=true` для subtype, которого нет в `GET_OPERATION_TYPES`, если сценарий молчаливый? | missing-flow | Major | resolved |
| CH-11 | §1.1 SMART, §2 | Time-bound = релиз 7.15.0, но зависимость «BPH отдаёт операции нового subtype» не привязана к дате/стенду: если BPH развернёт subtype позже 7.15.0, фича — no-op без сигнала. Кто и как проверяет готовность BPH к 7.15.0, и есть ли план B (допустимая деградация «налог не показывается»)? | nfr-hole | Minor | resolved |
| CH-13 | §5.3.1, §5.3.2, §4.2.2.2 п.2, §2 | Для `bc_id=NULL` единственная метрика нештатной фильтрации `unexpected_additional_type_for_common_operation` не инкрементится (ранний `return true`), а лог «Unexpected additional type…» не пишется (§5.3.1/§5.3.2 явно фиксируют «не срабатывает»). При этом §4.2.2.2 п.2 сам указывает тихий отказ: «без строки `status_to_operation` операция была бы отфильтрована» — и этот отказ, как и `bph_active=false` (subtype не запрашивается) и несовпадение `additionalType` (comment пуст/`accComment`), не даёт ни лога, ни метрики. После go-live, если пролив частичный или сломалась строка `status_to_operation`, фича молча перестанет показывать налог — ничем не детектируется. Каким сигналом (метрика полноты налоговой ленты? алерт на отсутствие `PORTFOLIO_SIZE_TAX` в SEND_OPERATIONS за период?) сопровождение узнает, что налог перестал отображаться, если §2 принимает деградацию «no-op без сигнала» только до включения BPH? | nfr-hole | Major | open |

## Тесты и приёмка

| ID | § spec | Вопрос | Тип | Severity | Статус |
|----|--------|--------|-----|----------|--------|
| CH-05 | §4.2.4 (удалён в прогоне 2) | В §4.2.4 перечислен только позитивный integration-тест (assert `PORTFOLIO_SIZE_TAX` в SEND_OPERATIONS). Негативные кейсы из alt 4a/2a — неожиданный `additionalType`, `additionalType=NULL` при `info.additional_type='PORTFOLIO_AMOUNT_TAX'`, `formationDate` до `historyStart` — не покрыты ни одним тестом/фикстурой (в sibling-spec MOEX_TAX §4.2.4 строка «Negative» была). Каким тестом проверяется, что операция с неверным `additionalType` НЕ попадает в ответ и инкрементится метрика? | test-gap | Major | resolved |
| CH-06 | §4.2.4 (удалён в прогоне 2) | Фикстура `application-test.yml` (`app-config.operation-cache`) для нового subtype описана как «добавить JSON-объект рядом с TAX_RETAIN» без спецификации полей. TAX_RETAIN имеет `bc_code:110, bc_active:true, bc_type:MONEY_DIAS, bc_subtype:TAX_WITHHOLDING`; при `bc_id=NULL` (AS-03) копирование этого шаблона создаст ложный BC-контекст и переключит ветку кода `isActualBphOperation` (см. CH-01). Какие именно поля (`bc_active`, `bc_code`, `bc_type`, `bc_subtype`, `status_and_general_status`, `operation_name`, `info[].additional_type`, `info[].comment`) должны быть в фикстуре и с какими значениями, чтобы не эмулировать BC-сторону? | test-gap | Major | resolved |
| CH-16 | §1.3, §2, §4.2.3 | Переписанный SPEC удалил раздел тестов/фикстур (бывший §4.2.4, где в прогоне 1 фиксировались позитивный integration-тест и строка Negative). Сейчас критерий приёмки задан только чекпойнтом §2 и тестовыми id §4.2.3; конкретного теста/фикстуры (assert `PORTFOLIO_SIZE_TAX` в SEND_OPERATIONS с `type=tax`, `comment=«Налог за размер портфеля»`; фикстура ответа BPH `json/response/bph/`; обновление `application-test.yml`) в SPEC нет (code-alignment T-01 это тоже фиксирует как Minor). Как фиксируется и проверяется критерий приёмки, если §4.2.4 удалён, а SMART §1.1 ссылается только на «SEND_OPERATIONS с type=tax»? | test-gap | Minor | open |

## Актуализация (прогон 2)

Переоценка CH-01…CH-11 против переписанного SPEC (mtime 2026-08-30 00:39). Статусы не регрессировали: 9 `resolved` + 2 `covered` подтверждены. Изменены только §-ссылки и пометки о stale-тексте.

| ID | Актуализация |
|----|--------------|
| CH-01 | `resolved` подтверждён. §4.2.2.2 уточнён после A-03: для `bc_id=NULL` пропускаются только watershed + `additionalType`; статус-членство проверяется отдельно `isBphCommonOperation()`. Вопрос закрыт точнее, чем в прогоне 1. |
| CH-02 | `resolved` подтверждён. Ответ зафиксирован в §2 «Зависимости и чекпойнты приёмки» п.2 (сверка enum с контрактом BPH до пролива). |
| CH-03 | `resolved` подтверждён. Текст вопроса stale: старые test-id 22/24/52/37 перенумерованы в 23/25/53/38 (§4.2.3), прод — `SELECT max(id)+1` + координация с `bph-moex-tax` (25/27/79/57). |
| CH-04 | `resolved` подтверждён. Ответ в §1.3 alt 2a и §2 Watershed (для `bc_id=NULL` `historyStart` не используется). |
| CH-05 | `resolved` подтверждён, но §-ссылка stale: раздел §4.2.4 удалён из переписанного SPEC. Ответ («негатив на стороне HO неприменим при `bc_id=NULL`») отражён в §4.2.2.2/§2. |
| CH-06 | `resolved` подтверждён, но §-ссылка stale: §4.2.4 удалён; поля фикстуры ныне в §5.4 (BC-free шаблон: `bc_active=false`, `bc_type`/`bc_subtype`=null) и §4.2.3. |
| CH-07 | `resolved` подтверждён. Ответ в BR-03 и §4.2.2 «Дедупликация» (Ignite по `id`; уникальность `externalSystemId` — BPH). |
| CH-08 | `resolved` подтверждён. Ответ в BR-02 (порог на стороне BPH, алерт не требуется). |
| CH-09 | `covered` подтверждён. §4.2.4 → §4.2.3 (примечание «`name` — служебное, в ленту не выводится»). Ссылка на §4.2.4 в тексте вопроса устарела. |
| CH-10 | `covered` подтверждён. BR-05 + §1.3 alt 5a валидны (comment из `info`, fallback `accComment`). |
| CH-11 | `resolved` подтверждён. Ответ в §2 «Зависимости» п.3 (допустимая деградация «налог не показывается»). |

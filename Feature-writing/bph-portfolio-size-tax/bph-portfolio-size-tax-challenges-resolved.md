---
report_type: challenges-resolved
slug: bph-portfolio-size-tax
source_document: Feature-writing/bph-portfolio-size-tax/bph-portfolio-size-tax.md
challenges_document: Feature-writing/bph-portfolio-size-tax/bph-portfolio-size-tax-challenges.md
context_document: Feature-context/bph-portfolio-size-tax.md
generated_at: 2026-08-29
session: 1
language: ru
---

# Карта закрытых вопросов: bph-portfolio-size-tax

## Сводка
- Resolved: 9 · Covered: 2 · Deferred: 0

## Сессия 1 (2026-08-29)

| ID | Verdict | Выбор | Решение | Затронутые § | Источник | Связанный Q |
|----|---------|-------|---------|--------------|----------|-------------|
| CH-01 | MISSING → resolved | a | При bc_id=NULL `isActualBphOperation()` возвращает true досрочно: watershed/additionalType/статус и лог+метрика НЕ выполняются — операция включается безусловно; фильтр по additionalType только на стороне запроса BPH | §4.2.2.2, §1.3 alt 2a/4a, §5.3.1, §5.3.2, §5.4, §2 Watershed | код `BphBcFilterService.java:181–196`; SIHIST-3476 | Q-08 (уточн.) |
| CH-02 | MISSING → resolved | a | AS-01/AS-04 помечены «из брифа, без контрактного пруфа»; добавлен чекпойнт приёмки: сверка subtype/additionalType с контрактом BPH до пролива | §2 Допущения, §2 Зависимости | выбор пользователя | Q-01, Q-04 |
| CH-03 | MISSING → resolved | a | id переназначены: test bph=25, operation=26, info=53, status_to_operation=38 (22/24/52/37 владеет bph-moex-tax); прод — SELECT max(id)+1 | §4.2.3 (таблица, SQL, прод) | выбор пользователя | — |
| CH-04 | MISSING → resolved | b | Watershed для bc_id=NULL не используется (следствие CH-01); молчаливый сценарий принят, алерт не требуется | §1.3 alt 2a, §2 Watershed, §5.4 | выбор пользователя + код | Q-08 (уточн.) |
| CH-05 | MISSING → resolved | a | Негатив только для запроса: assert `additionalTypes:["PORTFOLIO_AMOUNT_TAX"]`; негатив «неожиданный additionalType → не в ответе» на стороне HO неприменим (bc_id=NULL) | §4.2.4 (строка Negative) | выбор пользователя | — |
| CH-06 | MISSING → resolved | a | Фикстура operation-cache — BC-free шаблон (bc_active=false, bc_type/bc_subtype=null, без bc_code; info[0] с additional_type+comment) | §4.2.4 (таблица полей) | выбор пользователя + `application-test.yml`/SIHIST-3476 | — |
| CH-07 | MISSING → resolved | custom | HO не дедуплицирует типовые по externalSystemId в одном ответе; дедупликация = торговые + типовые по окну start/end + сверка с кэшем Ignite (по id) против повторной отправки; уникальность externalSystemId — BPH | §1.1 BR-03, §4.2.2 (Дедупликация) | пользователь + SIHIST-3367 + `OperationsIgniteProxyService` | Q-10 |
| CH-08 | MISSING → resolved | a | Контроль порога на стороне BPH; HO не фильтрует, алерт/метрика не требуется | §1.1 BR-02 | выбор пользователя | Q-09 |
| CH-09 | COVERED | — | comment ленты = `info.comment`; `operation.name` (operation_name) — служебное имя маппинга, не выводится в ленту; совпадение текстов допустимо | §4.2.3 (примечание) | код `BphCommonClientConverter` | — |
| CH-10 | COVERED | — | BR-05 соответствует коду (comment из info по additional_type, fallback accComment); уточнена формулировка со ссылкой на водораздел SIHIST-3476 | §1.1 BR-05 | код `BphCommonClientConverter.java:122–136`; SIHIST-3476 | — |
| CH-11 | MISSING → resolved | a | Зафиксирована допустимая деградация «налог не показывается» до включения BPH + проверка готовности BPH до пролива | §2 Зависимости | выбор пользователя | — |

## Отложено

| ID | Причина |
|----|---------|
| — | — |

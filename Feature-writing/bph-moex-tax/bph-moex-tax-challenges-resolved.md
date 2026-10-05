---
report_type: challenges-resolved
slug: bph-moex-tax
source_document: Feature-writing/bph-moex-tax/bph-moex-tax.md
challenges_document: Feature-writing/bph-moex-tax/bph-moex-tax-challenges.md
context_document: Feature-context/bph-moex-tax.md
generated_at: 2026-10-05
session: 2
language: ru
---

# Карта закрытых вопросов: bph-moex-tax

## Сводка
- Resolved: 9 · Covered: 5 · Deferred: 0

## Сессия 1 (2026-10-05)

| ID | Verdict | Выбор | Решение | Затронутые § | Источник | Связанный Q |
|----|---------|-------|---------|--------------|----------|-------------|
| CH-06 | COVERED | — | Оба поля участвуют в матчинге: `lead.subtype` (приоритет), `lead.subType` (camelCase, fallback) — `BphOperationConverter.getSubType()`. Уточнено в Field mapping (`type`). | §4.2.4 (Field mapping) | код `BphOperationConverter.java:181-190` | — |
| CH-08 | COVERED | — | Добавлена Validation-проверка консистентности bootstrap `operation-cache.default-value` с вставленными строками БД (blocking). | §4.2.5 (Validation) | spec + `application-test.yml` | — |
| CH-11 | COVERED | — | Добавлен acceptance-тест ACC-006 (состав запроса: `subtypesAndStatuses[]` содержит `{TAXES, MOEX_TAX, [COMPLETE]}`, `additionalTypes` опускается) + строка BR-06 в coverage matrix. | §6 (ACC-006, coverage matrix) | spec (CN-08, BR-06) | — |
| CH-12 | COVERED | — | Исправлены dangling-ссылки «§4.2.2 «Алгоритм обработки»» → «§4.2.2 «Обработать налоговую операцию MOEX_TAX из ответа BPH»» (3 места). | §4.1.1, §4.2.3, §4.2.4 | spec | — |
| CH-13 | COVERED | — | Зафиксировано: `operation.name` в UI не рендерится (display-имя из `info.displayed_name` = NULL → фикс. заголовок CN-05); `operation.name` — dead data для отображения. | §4.2.3 (примечание к `operation`) | код `BphCommonClientConverter.enrichOperationDisplayName()`, `Operation.java` | — |

## Сессия 2 (2026-10-05)

| ID | Verdict | Выбор | Решение | Затронутые § | Источник | Связанный Q |
|----|---------|-------|---------|--------------|----------|-------------|
| CH-01 | MISSING → resolved | A | Зафиксировано CN-14: `MOEX_TAX` поступает только из BPH (OG/BC этот налог не отдают, BC-аналог отсутствует); дедупликация BPH↔BC не требуется | §2 (CN-14) | выбор пользователя (D-15) | — |
| CH-02 | MISSING → resolved | A | Зафиксировано как ожидаемое: watershed отсутствует (CN-10), исторические `MOEX_TAX` любой давности попадают в ленту (backfill данных BPH датой не ограничивается); примечание к Backfill | §2 (CN-10), §4.2.5 (Backfill) | выбор пользователя (D-16) | — |
| CH-03 | PARTIAL → resolved | B | Degraded-описание достаточно постусловием «Неуспех (техн.)» и CN-12; отдельный alt-поток и acceptance-тест не добавляются (зафиксировано в CN-12) | §2 (CN-12) | выбор пользователя (D-17) | — |
| CH-04 | MISSING → resolved | A | Edge-сценарий 6a (non-null `additionalType` → fallback `details.accComment`) + негативный тест ACC-E04; `additionalType=NULL` зафиксировано как контрактное требование к BPH (CN-08) | §1.3 (alt 6a), §2 (CN-08), §6 (ACC-E04, coverage) | выбор пользователя (D-14) | — |
| CH-05 | MISSING → resolved | A | Добавлен BR-14: HO не дедуплицирует по `externalSystemId`; уникальность `externalSystemId` поперёк subtype — ответственность BPH; примечание к id-маппингу | §1.3 (BR-14), §4.2.2 (BR-14), §4.2.4 (Field mapping) | выбор пользователя (D-18) | — |
| CH-07 | MISSING → resolved | A | Зафиксирован фактический механизм идемпотентности: UNIQUE на `bph.subtype` отсутствует; идемпотентность = однократный прогон Liquibase changeset (`DATABASECHANGELOG`) + явные `id` PK; убрана формулировка «уникальность bph.subtype» и пометка «подтвердить» | §4.2.5 (Backfill/Идемпотентность) | выбор пользователя (D-19) | — |
| CH-09 | MISSING → resolved | A | Текущее no-op принято; добавлен acceptance-тест ACC-E05 («настроено, но нет `MOEX_TAX` за период») + рекомендация по операционному мониторингу (Observability-примечание) | §4.2.4 (Validation и rejection), §6 (ACC-E05) | выбор пользователя (D-20) | — |
| CH-10 | MISSING → resolved | A | Зафиксирован обязательный порядок rollout: INSERT → перезагрузка кэша → go-live BPH (CN-15 + примечание к Плану миграции) | §2 (CN-15), §4.2.5 (План миграции) | выбор пользователя (D-21) | — |
| CH-14 | MISSING → resolved | A | Зафиксировано фактическое: FK без `ON DELETE CASCADE` → DELETE в порядке `info` → `status_to_operation` → `operation` → `bph`; убрана формулировка «каскадно»; восстановлен заголовок «**Rollback:**» и header-строка таблицы | §4.2.5 (Rollback) | выбор пользователя (D-22) | — |

## Отложено

| ID | Причина |
|----|---------|
| — | — |

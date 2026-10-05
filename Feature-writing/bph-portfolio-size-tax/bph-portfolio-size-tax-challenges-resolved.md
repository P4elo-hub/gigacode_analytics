---
report_type: challenges-resolved
slug: bph-portfolio-size-tax
source_document: Feature-writing/bph-portfolio-size-tax/bph-portfolio-size-tax.md
challenges_document: Feature-writing/bph-portfolio-size-tax/bph-portfolio-size-tax-challenges.md
context_document: Feature-context/bph-portfolio-size-tax.md
generated_at: 2026-10-06
session: 2
language: ru
---

# Карта закрытых вопросов: bph-portfolio-size-tax

## Сводка
- Resolved: 12 · Covered: 4 · Deferred: 0

## Сессия 1 (2026-10-06) — COVERED по факту (spec поправлен)

| ID | Verdict | Выбор | Решение | Затронутые § | Источник | Связанный Q |
|----|---------|-------|---------|--------------|----------|-------------|
| CH-05 | COVERED (факт) | — | `accComment` берётся из `details[]` (ключ `accComment` из `BphConverter.SUPPORTED_DETAILS_KEY`), а не из `lead` (в `OperationData` поля `accComment` нет). Spec поправлен: «`lead.accComment`» → «`accComment` из `details[]`», пример JSON перенёс `accComment` в `details[]` | §1.1 BR-05, §1.3, §2 CN-09, §4.1.1, §4.2.2, §4.2.4 | код `BphOperationConverter.convert()` (`details.get("accComment")`) + `BphConverter.SUPPORTED_DETAILS_KEY` + `BphCommonClientConverter.convert()` (`operation.accComment()`) | — |
| CH-06 | COVERED (факт) | — | `validateSimpleAttributes()` (`checkNotNull`) кидает NPE внутри `converter.convert()`; `ListRequestService.convertEntry()` ловит `RuntimeException` **по записи** и инкрементит `parse_error`, не роняя пачку. Одна «недооформленная» операция `PORTFOLIO_SIZE_TAX` не роняет существующие налоги | §4.1.1, §5.3.2 | код `BphGateway.getOperationsInternal()` → `ListRequestService.convertEntry()` (try/catch RuntimeException) + `BphOperationConverter.validateSimpleAttributes()` | — |
| CH-09 | COVERED (факт) | — | `eventDate` обязателен на входе (`checkNotNull`), а `timeClosed` не бывает null после валидации: `parseLocalDateTime()` (`LocalDateTime.parse`) кидает `DateTimeParseException` при неверном формате → `parse_error`, запись отбрасывается. §4.2.4 `timeClosed` помечен как Required (non-null) | §4.1.1, §4.2.4 | код `BphOperationConverter.validateSimpleAttributes()` + `BphConverter.parseLocalDateTime()` | — |
| CH-10 | COVERED (факт) | — | Authoritative ключ lookup `operation` — `originalType` + `bphType` (`originalType` = `lead.type`, `bphType` = `lead.subtype`). §4.2.4 `type`-строка приведена к этому написанию (было «`bphType`+`bphSubtype`») | §4.1.1, §4.2.2, §4.2.4 | код `BphCommonClientConverter.getOperationFromCache()` / `isSameOperationFromCacheByTypeAndSubtype()` | — |

## Сессия 2 (2026-10-06) — applied (решения пользователя D-15…D-26)

| ID | Verdict | Выбор | Решение | Затронутые § | Источник | Связанный Q |
|----|---------|-------|---------|--------------|----------|-------------|
| CH-12 | MISSING → resolved | B (D-15) | Non-SMART: подтверждение «фича заработала» = SQL-сверка строк маппинга + позитивный интеграционный тест + существующая `history_ops_integration_total`; отдельная per-subtype метрика не вводится | §5.3.2 | выбор пользователя | — |
| CH-01 | MISSING → resolved | A (D-16) | Налог — разовая неторговая операция на каждое удержание BPH; «отдельно по каждой операции» = одна исходящая операция МП на одну операцию BPH без агрегации; BR-02 проверяется data-level | §1.1 BR-02, §1.3 BR-02 | выбор пользователя | — |
| CH-02 | MISSING → resolved | A (D-17) | `info.comment` всегда задан («Налог за размер портфеля», D-02) — сценарий «без текста» не возникает; при одновременно пустых `info.comment` и `accComment` деградация допустима | §4.2.4 | выбор пользователя | — |
| CH-03 | MISSING → resolved | A (D-18) | Вне scope: маппим только `status=COMPLETE`; сторно/корректировки приходят отдельными операциями иного subtype/источника и не затрагиваются (CN-18) | §2 CN-18 | выбор пользователя | — |
| CH-04 | MISSING → resolved | A (D-19) | Pre-check = подтверждённый командой BPH факт «BPH игнорирует неизвестный subtype, ответ 200 с пустым data» + включение subtype на стороне BPH до пролива HO | §2 CN-11, §4.1.1 | выбор пользователя | — |
| CH-07 | MISSING → resolved | A (D-20) | Глобальная уникальность `externalSystemId` (сквозной счётчик BPH) + pre-check с BPH; коллизий нет | §4.2.4 | выбор пользователя | — |
| CH-08 | MISSING → resolved | A (D-21) | `operation.name` используется consumer'ом (МП/деталка) как заголовок при пустом `displayed_name` → заголовок = «Налог за размер портфеля» | §4.2.4 | выбор пользователя | — |
| CH-13 | MISSING → resolved | B (D-22) | Существующий INFO-лог успешного обновления кэша + операционная процедура; отдельная метрика/алерт не вводится, рассинхрон допустим | §7.1.7, §5.3.1 | выбор пользователя | — |
| CH-15 | MISSING → resolved | B (D-23) | Негативные тест-фикстуры вне scope — приёмка = позитивный интеграционный тест + SQL-валидация | §5.3.2 | выбор пользователя | — |
| CH-11 | MISSING → resolved | A (D-24) | SERIAL/sequence авто (INSERT без явного id) — общая sequence гарантирует непересечение с sibling `bph-moex-tax`; координация с DBA не требуется | §2 CN-06 | выбор пользователя | — |
| CH-14 | MISSING → resolved | A (D-25) | Откат = `bph.is_active=false` (строка остаётся); pre-check «0 строк по subtype» перед каждым проливом не создаёт вторую активную строку | §2 CN-13, §Тогглы | выбор пользователя | — |
| CH-16 | MISSING → resolved | B (D-26) | Data-level приёмка (SQL + shape кэша); end-to-end assert не требуется (согласуется с non-SMART D-09) | §5.3.2 | выбор пользователя | — |

## Отложено

Нет — все открытые `CH-*` закрыты.

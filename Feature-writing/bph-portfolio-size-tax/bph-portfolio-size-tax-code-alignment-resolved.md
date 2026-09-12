---
report_type: code-alignment-resolved
slug: bph-portfolio-size-tax
source_document: Feature-writing/bph-portfolio-size-tax/bph-portfolio-size-tax.md
alignment_document: Feature-writing/bph-portfolio-size-tax/bph-portfolio-size-tax-code-alignment.md
generated_at: 2026-08-30
session: 1
language: ru
---

# Карта правок code-alignment: bph-portfolio-size-tax

## Сводка

- Закрыто: 1 (A-03, Major PARTIAL — фактическая поправка)
- Отложено: 0
- Пропущено как TO BE / не closable: 0 (все остальные CONFIRMED)
- Вопрос пользователю не задавался — поведение однозначно из кода (нет неоднозначности дизайна).

## Сессия 1 (2026-08-30)

| ID | Verdict | Тип | Решение | Затронутые § | Источник (код) |
|----|---------|-----|---------|--------------|----------------|
| A-03 | PARTIAL → fixed | фактическая поправка | Заменена формулировка «фильтра по статусу нет / статуса НЕ выполняются / включается безусловно» на точную: для `bc_id=NULL` внутри `isActualBphOperation()` пропускаются только watershed и additionalType (ранний `return true`); статус-членство (`statusMap.containsKey(status)`) по-прежнему проверяется `isBphCommonOperation()` до `isActualBphOperation()`. Для нового налога `status=COMPLETE` настроен через `status_to_operation` (status_id=19), поэтому проверка проходит; без строки `status_to_operation` операция была бы отфильтрована. Сохранено: лог+метрика `unexpected_additional_type_for_common_operation` для этого пути не срабатывают. | §1.3 постусловие; §2 Watershed; §4.2.2.2 | `BphCommonListBuilder.java:65-73` (цепочка фильтров); `BphBcFilterService.java:69-86` (`isBphCommonOperation` → `statusMap.containsKey(status)` строка 85); `BphBcFilterService.java:181-191` (ранний `return true`); `BphBcFilterService.java:201-250` (watershed/additionalType/лог+метрика — пропускаются) |

## Якоря кода, подтверждающие поведение

| Утверждение | Якорь |
|-------------|-------|
| Статус-членство выполняется **до** `isActualBphOperation()` и всегда (вкл. `bc_id=NULL`) | `BphCommonListBuilder.java:65-73` — `.filter(this::isBphCommonOperation)` (строка 68) предшествует `.filter(... isActualBphOperation ...)` (строки 69-71) |
| Делегирование `isBphCommonOperation` | `BphCommonListBuilder.java:86-88` → `bphBcFilterService.isBphCommonOperation(...)` |
| Публичный метод `isBphCommonOperation()` | `BphBcFilterService.java:69-73` |
| Проверка `statusMap.containsKey(status)` | `BphBcFilterService.java:75-86` (`isCommonOperationByBphContext`), строка 85 |
| Ранний `return true` при отсутствии BC-контекста | `BphBcFilterService.java:181-191`; `hasBcContext` = `bcType != null && bcSubtype != null` (строка 187); `return true` на 189-191 |
| Watershed / additionalType / лог+метрика — пропускаются для `bc_id=NULL` | `BphBcFilterService.java:201-250`; лог-шаблон 242-245, метрика 246-247 |

## Отложено

| ID | Причина |
|----|---------|
| — | — |

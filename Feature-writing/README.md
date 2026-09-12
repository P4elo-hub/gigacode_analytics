# Feature-writing

Папки фич. **Один `<slug>` = одна папка** со спецификацией и всеми отчётами.
Как пишется spec: [HOW-IT-WORKS.md](../HOW-IT-WORKS.md).
Канон путей — правило `artifact-paths`.

## Назначение

Спецификация фичи — **финальный артефакт аналитики**: `AS IS`, `TO BE`,
контракты, модель данных, NFR. Не описывает current-state системы целиком;
для current-state — `Feature-context/` (`/find-context`).

Готовый `Feature-writing/<slug>/<slug>.md` передаётся в разработку после
`/check-feature-code` с verdict PASS / PASS WITH GAPS.

## Раскладка

```
Feature-writing/<slug>/
  <slug>.md                        ← спецификация
  <slug>-code-alignment.md
  <slug>-gaps-resolved.md
  <slug>-challenges.md
  <slug>-challenges-resolved.md
```

| Файл | Что это | Кто создаёт |
|---|---|---|
| `<slug>.md` | Готовая спецификация: один Markdown, чистый документ требований | `/write-feature` |
| `<slug>-code-alignment.md` | Сверка spec с кодом (RU) | `/check-feature-code` |
| `<slug>-gaps-resolved.md` | Карта закрытых `[GAP-...]` (не в теле spec) | `/resolve-gaps` |
| `<slug>-challenges.md` | Банк каверзных вопросов `CH-*` | `/challenge-feature` |
| `<slug>-challenges-resolved.md` | Карта закрытых `CH-*` | `/resolve-challenges` |
| `<slug>.part-<block_id>.md` | Фрагмент блока (рабочий) | `/write-feature` |
| `<slug>.context.md` | Накопленный контекст блоков (рабочий) | `/write-feature` |

Рабочие файлы (`*.part-*.md`, `*.context.md`) удаляет успешный
`--mode assemble --out`. Не хранить их после сборки.
Ничего не кладите в `Feature-writing/` вне папки фичи (кроме этого README).

## Статус фичи

```
/feature-status <slug>
```

Покажет открытые `[GAP-...]` и `CH-*`, verdict alignment, устаревшие отчёты и
**одну** следующую команду.

## Как сюда писать

Документ пишется по блокам, каждый блок — в два прохода (черновик → закрытие
гэпов). Через `/write-feature` или напрямую скриптом:

```bash
# 1. План блоков
python3 scripts/write_feature.py "<бриф>" --mode plan --name <slug> --part-dir Feature-writing/<slug>

# 2. Каждый блок пишет spec-writer по карточке задания (вся строка skills:)
#    → Feature-writing/<slug>/<slug>.part-<block_id>.md
#    затем: --mode check-part --block-id <id>

# 3. Сборка финального документа из фрагментов
python3 scripts/write_feature.py "<бриф>" --mode assemble --name <slug> \
  --part-dir Feature-writing/<slug> --out Feature-writing/<slug>/<slug>.md
```

Логика по каждому блоку:

- **Проход 1 (черновик):** бриф + `Feature-context/<slug>.md` + kit-скилл
  (template / example / gate из `kb-writing-kits/` целиком). Чего нет — `[GAP-...]`.
- **Проход 2 (закрытие гэпов):** только при наличии гэпов — якоря из context-doc
  или `find_context.py`; непокрытые остаются для `/resolve-gaps`.

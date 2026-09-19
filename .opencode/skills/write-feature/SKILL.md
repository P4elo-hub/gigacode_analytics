---
name: write-feature
description: >-
  Правила одного блока spec: фрагмент, гэпы, запрет сжимать форму. Очередь
  блоков и сборка — JSON cycle / write_feature_cycle.py, не этот скилл.
user-invocable: false
---

# write-feature

Клетка графа **write-feature** одна. Кто следующий блок и когда собирать SPEC —
скрипт `scripts/write_feature_cycle.py` (поле `cycle` в `pipeline_delegate.py`).
Этот скилл — правила **одного** фрагмента для `spec-writer`.

Пути: правило `artifact-paths`. Таблица блоков и форма → [reference.md](reference.md).

| | Путь |
|---|------|
| **Очередь клетки** | `python3 scripts/write_feature_cycle.py <slug>` → `task` / `assemble` / `done` |
| **Вход блока** | JSON `cycle` (`block_id`, `skills`) + бриф + `CONTEXT_DOC` |
| **Выход блока** | `FEATURE_DIR/<slug>.part-<block_id>.md` |
| **Сборка** | `write_feature_cycle.py <slug> --assemble` (скрипт, не `spec-writer`) |

## Один блок

Пиши только `cycle.block_id`. Не выбирай следующий блок по диску и не собирай SPEC.

1. Загрузи **все** kit-скиллы из `cycle.skills` (колонка плана) — не больше и не меньше.
   Нет скилла в списке → не вызывай его, даже если другой скилл блока его упоминает.
2. Для каждого скилла колонки прочитай его template / example / gate **целиком**
   из `kb-writing-kits/` (чтение файла, не `head`).
3. Прочитай `CONTEXT_DOC` и `<slug>.context.md`, если есть.
4. Проход 1: только бриф, контекст, kit. Нет факта → `[GAP-...]`.
5. Проход 2: гэпы по якорям `CONTEXT_DOC` или `find_context.py`; не нашёл — оставь.
6. Фрагмент → `<slug>.part-<block_id>.md`; допиши в `<slug>.context.md`.
   `check-part` на первом проходе не вызывай (оркестратор — один раз по `cycle.check`).
   Повтор после отказа: один `check-part` с `--block-id` и `--sections` из задания.

Формат фрагмента и гэпы — [reference.md](reference.md). Форма раздела —
только template и gate kit: не добавляй подразделы сверх kit и не выкидывай
то, что kit требует.

## Сборка (не этот скилл)

Оркестратор, когда `cycle.action == assemble`:

```bash
python3 scripts/write_feature_cycle.py <slug> --assemble
```

Успешный assemble пишет `SPEC` и удаляет `*.part-*.md` и `*.context.md`.
Незакрытые гэпы не выдумывать. Лимит строк на `SPEC` не действует.

## Антипаттерны

- ❌ Писать всю spec в одной сессии `spec-writer`
- ❌ Самим решать, какой блок следующий (это `write_feature_cycle.py`)
- ❌ Собирать SPEC через `spec-writer` / `--mode assemble`
- ❌ Фрагмент без скиллов из `cycle.skills` и без чтения файлов из `kb-writing-kits/`
- ❌ Догружать kit-скилл, которого нет в списке
- ❌ Обрезать kit (`head` / `tail`)
- ❌ Соседняя спека как образец полноты
- ❌ Внутренние классы в Use Case; сжимать форму относительно kit
- ❌ Выдумывать факты / удалять `[GAP-...]`
- ❌ Считать блок готовым, если `check-part` вернул отказ
- ❌ Второй `check-part` на тот же блок; вызов без `--block-id` или `--sections`

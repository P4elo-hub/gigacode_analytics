---
description: Написать спецификацию фичи по блокам из spec-catalog.yaml
agent: spec-orchestrator
---

Шаг пайплайна **write-feature**. Бриф: $ARGUMENTS

Собери план через `python3 scripts/write_feature.py --mode plan --profile sihist`.
Профиль уже включает контракт, модель, NFR; вопрос — про исключения и редкие
блоки (threat, acceptance, migration, async). UML AS IS/TO BE — в блоках use case.

После подтверждения — для **каждой** строки копируй в `task` блок
`### \`<block_id>\`` из плана (вся строка `skills:`). После `part`-файла —
**один** `check-part` с `--block-id` и `--sections` утверждённого плана.
Отказ — один повтор writer, снова отказ — стоп.
После всех принятых фрагментов — assemble, сразу `check-feature`.

Не пиши spec сам и не запускай один `spec-writer` на весь документ.

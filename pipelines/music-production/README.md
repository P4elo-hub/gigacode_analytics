# music-production

Независимый pack поверх текущего движка. Slug каталога `pipelines/music-production`.
Python-пакет кода — `music_production/`, не эта папка.

Маршрут последовательный. Цикл текста задан рёбрами, не generic `cycle`.

Human gates (`ask: true`): `package-approval`, `select-base`, `revision-escalation`,
`final-approval`. Пока решения Алекса нет, dispatch остаётся на этом узле в режиме
`ask_user`.

Любое expert decision сначала идёт в один узел `capture-knowledge`.
`decision_capture_pending` истинно, когда в `expert-decision.json` есть
`decision_id`, а в `knowledge.json` → `captured_decision_ids` этого id ещё нет.
Это правило выше любого перехода по verdict. После записи dispatch снова читает
тот же verdict и продолжает маршрут.

Граф не увеличивает `revision_budget_remaining`. `RETRY_REVISION` ведёт в
`plan-revision` только если бюджет уже восстановлен снаружи. Иначе
`revision-escalation` остаётся открытым.

Автоматический `REVISE` пакета смотрит `revision_target`: `LYRICS` или
`PRODUCTION`. Без цели пакет остаётся на `package-review`.

Сервисные шаги без субагента: `generate-batch`, `execute-edit`, `final-qc`.

`gated_subagents` пуст. SubagentStop matcher этим промтом не меняется.

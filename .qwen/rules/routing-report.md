---
description: Every pipeline subagent publishes a compact semantic result for incremental routing
alwaysApply: true
---
# Routing report

Каждый pipeline-субагент завершает финальный ответ ровно одним JSON-блоком:

```text
<routing-report>
{"summary":"что сделано","artifacts":[{"path":"путь","action":"created|updated|deleted"}],"outcomes":["что теперь истинно"],"remaining_work":["что осталось"]}
</routing-report>
```

Правила:

- `summary` обязателен и описывает фактический результат этого прохода.
- `artifacts` перечисляет только реально созданные, изменённые или удалённые файлы.
- `outcomes` содержит установленные факты, полезные для условий маршрутизации.
- `remaining_work` содержит незакрытые вопросы, ошибки и необходимое продолжение; пустой список допустим.
- Не выбирать следующий шаг и не писать `next_step`, `ready` или имя следующего агента.
- Не утверждать факт, который не подтверждён выполненной работой или прочитанным артефактом.

SubagentStop hook сохраняет блок в task-local routing journal. Отсутствующий или
невалидный блок помечается `incomplete` и заставляет routing-analyzer использовать
обычный fallback по артефактам.

---
description: Every lab pipeline subagent publishes a compact semantic result
alwaysApply: true
---
# Routing report

Заверши проход блоком:

```text
<routing-report>
{"summary":"что сделано","artifacts":[],"outcomes":[],"remaining_work":[]}
</routing-report>
```

Не выбирай следующий шаг. SubagentStop hook сохраняет блок в task-local
routing journal; отсутствующий блок становится `incomplete` и требует fallback.

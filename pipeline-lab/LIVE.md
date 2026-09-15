# LIVE — сессия 4

Дата: 2026-09-15.

## Как стартовали

- **cwd:** `pipeline-lab/` (не корень репо)
- **project root Qwen:** вложенный `git init` в `pipeline-lab/`, чтобы грузился
  `pipeline-lab/.qwen/`, а не боевой `.qwen/`
- **команда:** `qwen` из `pipeline-lab/`, затем `/lab-run <scenario-id>`
- Смоук изоляции: из этого cwd доступна только `/lab-run`; боевые
  `/write-feature` и `/find-context` не видны. Агенты — тонкие из
  `pipeline-lab/.qwen/agents/`.

```bash
cd pipeline-lab
test -d .git || git init
qwen
/lab-run lab-03-challenge-not-check
```

Headless (без Qwen): `python3 pipeline-lab/run.py --all` — 7 сценариев зелёные.

## Живые прогоны

| slug | path | expect_path |
|------|------|-------------|
| `lab-01-retry-same-step` | analyze-routing → challenge-feature → challenge-feature | совпал |
| `lab-03-challenge-not-check` | analyze-routing → challenge-feature → **resolve-challenges** | совпал |
| `lab-06-pending-apply-beats-check` | analyze-routing → **resolve-challenges** | совпал |

Критерии графа:

- **lab-03:** после `challenge-feature` оркестратор вызвал `challenge-resolver`,
  не `spec-reviewer`.
- **lab-01:** retry (`ASK_PARENT`) → тот же шаг `challenge-feature` ещё раз.
- **lab-06:** `pending-apply` → `resolve-challenges`, не `check-feature`.

Остальные четыре (`lab-02`, `lab-04`, `lab-05`, `lab-07`) оставлены за
`python3 pipeline-lab/run.py --all`.

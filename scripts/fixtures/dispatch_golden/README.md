# Dispatch golden fixtures

Per-pipeline contract: `fixtures/dispatch_golden/<pipeline_id>/cases.json`
**or** `WAIVER.md` (no-dispatch / `orchestrator_only` only).

Policy: [PIPELINE-GOLDEN.md](../../PIPELINE-GOLDEN.md).

```bash
PYTHONPATH=scripts python3 scripts/pipeline_dispatch_golden_test.py
PYTHONPATH=scripts python3 scripts/pipeline_dispatch_golden_test.py --case 05-open-gaps
PYTHONPATH=scripts python3 scripts/pipeline_dispatch_golden_test.py --list
PYTHONPATH=scripts python3 scripts/pipeline_golden_coverage_test.py
```

Every pack in `pipelines/` must appear here. `dispatch_supported` packs need
≥ 1 case; **spec** is the platform reference (24+ cases, additive only).
A golden folder with no matching pack fails coverage.

Spec pack (24+ cases): [spec/COVERAGE.md](./spec/COVERAGE.md).

Calibration (Option A, no router): [calibration/COVERAGE.md](./calibration/COVERAGE.md)
— 1 case `01-orchestrator-only` (a `WAIVER.md` would also satisfy the gate).

Each case:

- `files` — paths relative to temp workspace root
- `touch_after` — `[older, newer]` mtime pairs
- `run_log` — optional `agent-logs` rows
- `routing_state` — option B: JSON body injected after mtimes (spec pack)
- `expect` — `next_step`, `orchestrator_mode`, `ready`, …
- `pipeline_id` — set from the parent folder name

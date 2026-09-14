# Dispatch golden fixtures

Per-pipeline contract: `fixtures/dispatch_golden/<pipeline_id>/cases.json`.

```bash
PYTHONPATH=scripts python3 scripts/pipeline_dispatch_golden_test.py
PYTHONPATH=scripts python3 scripts/pipeline_dispatch_golden_test.py --case 05-open-gaps
PYTHONPATH=scripts python3 scripts/pipeline_dispatch_golden_test.py --list
```

Spec pack (24+ cases) is the platform reference: [spec/COVERAGE.md](./spec/COVERAGE.md).

Calibration (Option A, no router): [calibration/COVERAGE.md](./calibration/COVERAGE.md).

Each case:

- `files` — paths relative to temp workspace root
- `touch_after` — `[older, newer]` mtime pairs
- `run_log` — optional `agent-logs` rows
- `expect` — `next_step`, `orchestrator_mode`, `ready`, …
- `pipeline_id` — set from the parent folder name

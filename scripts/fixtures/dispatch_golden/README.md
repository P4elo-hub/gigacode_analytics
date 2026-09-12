# Dispatch golden fixtures (compiled router)

Isolated artifact trees exercise `build_dispatch()` without touching live slugs.

Run:

```bash
PYTHONPATH=scripts python3 scripts/pipeline_dispatch_golden_test.py
PYTHONPATH=scripts python3 scripts/pipeline_dispatch_golden_test.py --case 05-open-gaps
PYTHONPATH=scripts python3 scripts/pipeline_dispatch_golden_test.py --list
```

Also invoked from `pipeline_smoke_test.py` as `dispatch-golden`.

Pipeline topology compile (phase 1): see [PIPELINE-COMPILE.md](../../PIPELINE-COMPILE.md).

Full branch matrix: [COVERAGE.md](./COVERAGE.md) (24 cases, compiled router).

Each case in `cases.json`:

- `files` — paths relative to temp workspace root
- `touch_after` — `[older, newer]` mtime pairs (shared base time)
- `run_log` — optional `agent-logs` rows (with `align_spec_before_run_log`)
- `expect` — `next_step`, `orchestrator_mode`, `ready`, etc.

DECISIONS tables use the production 7-column shape (`Prompt`, `Options`, …) so
`DECISION_ROW_RE` in `feature_status.py` parses Status correctly.

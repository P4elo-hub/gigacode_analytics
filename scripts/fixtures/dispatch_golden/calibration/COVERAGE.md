# Dispatch golden — calibration

Phase 3 Option A: calibration has **no** compiled dispatch rules (`orchestrator_only`).

| Fixture | Contract |
|---------|----------|
| `01-orchestrator-only` | `build_dispatch(..., pipeline_id=calibration)` → empty next, `dispatch_supported: false` |

# Waiver would also satisfy the Phase 9 pack↔golden gate; this pack keeps a real case.

Graph + delegate checks live in `pipeline_smoke_test.py` (`dispatch:calibration`, `pipeline-delegate:calibration`).

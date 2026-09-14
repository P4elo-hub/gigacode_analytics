# Dispatch golden — routing-poc (Phase 10)

Fake `ROUTING_STATE` JSON → `build_dispatch(..., pipeline_id="routing-poc")`.
Spec golden (`fixtures/dispatch_golden/spec/`) is unchanged.

| Id | Setup | next |
|----|--------|------|
| `01-fake-json-open-gaps` | JSON `open_gaps` + JSON newer than SPEC | `resolve-gaps` |
| `02-missing-json` | SPEC only | `analyze-routing` |
| `03-stale-json` | JSON older than SPEC | `analyze-routing` |

`when:`: `routing_state_needs_refresh` → `open_gaps` → `routing_state_ready`.
Stale POC: JSON vs SPEC only (full artifact set — Phase 11).
Smoke: no dedicated `routing-poc` row; covered by this golden + compile.

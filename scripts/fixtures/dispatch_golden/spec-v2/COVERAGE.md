# Dispatch golden — spec-v2 (Session 4 / full codegen B1)

Pack-local bools from `pipelines/spec-v2/routing_conditions.yaml` → overlay →
`build_dispatch(..., pipeline_id="spec-v2")`. No `agent_zakonchil_*` when:.

| Id | Setup | next |
|----|--------|------|
| `01-all-domain-bool-false` | Fresh routing-state, all domain bools false | `analyze-routing` (fallback) |
| `02-find-context-true` | Only `find_context: true` | `context-researcher` |
| `03-missing-json-p5` | No routing-state.json | `analyze-routing` (P5) |

`when:` coverage: `routing_state_needs_refresh` (P5), `find_context`, fallback.
Loops work-step → analyze-routing are `after_step` (no bool).

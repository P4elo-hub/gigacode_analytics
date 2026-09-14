# Pipeline routing-state (Phase 10–11)

LLM **analyzer** writes a JSON snapshot. Deterministic **router** reads it
through `populate_status` — no LLM in `build_dispatch`. Spec collectors stay
until Phase 12. Live spec dispatch is still collectors. Live POC graph:
`--pipeline routing-poc`. Phase 11 = dual-run parity, not cutover.

```
delegate → (missing/stale) analyze-routing → routing-analyzer
        → <slug>-routing-state.json
        → overlay_collector → predicates → next step
```

Orchestrator runtime loop is unchanged: delegate → action → append_run_log →
ingest → validate (`--pipeline <id>`). Analyzer is a graph step only on
`routing-poc` (spec graph has no `analyze-routing` until Phase 12).

## Artifact

| Token | Path |
|-------|------|
| `ROUTING_STATE` | `Feature-writing/<slug>/<slug>-routing-state.json` |

Schema version `1`. Analyzer fills `fields` only — never `next_step` /
`orchestrator_mode` / `ready` (router-owned).

```json
{
  "schema_version": 1,
  "slug": "bph-moex-tax",
  "generated_at": "2026-09-14T16:00:00Z",
  "fields": {
    "has_context": true,
    "has_spec": true,
    "open_gaps": ["GAP-X"],
    "challenges": {"open": 0, "deferred": 0, "resolved": 0, "covered": 0, "open_critical": 0, "open_major": 0}
  }
}
```

Helper: `scripts/pipeline_routing_state.py` (`load_routing_state`,
`apply_routing_state_fields`, `overlay_collector`, `spec_overlay_collector`).
Pack collector id: `routing_state`.

## Spec status fields the router uses

Inventory from `pipelines/spec/status.yaml` + `predicates.py` (dispatch `when:`).
Analyzer populates the same names so overlay is 1:1.

| Field | Source today | Predicates / invariant |
|-------|----------------|------------------------|
| `has_context` | artifacts.context | `not_has_context` |
| `has_spec` | artifacts.spec | `not_has_spec` |
| `has_alignment` | artifacts.alignment | `alignment_limit_exhausted`, `alignment_missing_or_stale` |
| `has_challenges` | artifacts.challenges | `open_challenges`, `no_challenges_file`, invariant |
| `has_gaps_map` | artifacts.gaps_map | invariant `needs-check-feature` |
| `has_challenges_map` | artifacts.challenges_map | invariant |
| `has_decisions` | artifacts.decisions | display (not a `when:`) |
| `decisions_needs_answer` | collectors.decisions_table | `needs_answer_*`, `ask_user` |
| `decisions_pending_apply` | collectors.decisions_table | `pending_apply_*` |
| `decisions_needs_answer_alignment` | collectors.decisions_table | `needs_answer_alignment_only` / `_challenges_only` |
| `decisions_pending_apply_alignment` | collectors.decisions_table | `pending_apply_alignment_only` / `_challenges_only` |
| `open_gaps` | collectors.spec_gaps | `open_gaps`, `*_with_gaps`, `*_challenges_only` |
| `challenges.open` | collectors.challenges_table | `open_challenges` |
| `verdict` | collectors.alignment_frontmatter | `alignment_pass`, `alignment_limit_exhausted` |
| `alignment_iteration` | collectors.alignment_frontmatter | limit / mismatch / pending-apply alignment |
| `critical_major_mismatch` | collectors.alignment_frontmatter | `critical_major_mismatch_resolvable` |
| `alignment_stale` | alignment_stale rule | mismatch / pending-apply alignment |
| `stale` | stale[] | `alignment_missing_or_stale` (`"alignment" in stale`) |
| `needs_check_feature` + `_reason` | collectors.needs_check_feature | invariant `needs-check-feature` |

Not used by spec dispatch: `open_questions`, `spec_lines`, `context_lines`,
other `challenges.*` counts (display). Engine still computes **mtime** `stale[]`
and `alignment_stale` from `status.yaml` after the overlay.

Full mapping: `pipelines/spec/routing_conditions.yaml` (shadow, not compiled).
Parity table: [PIPELINE-PARITY.md](PIPELINE-PARITY.md).

## Stale / missing

Treat as “run analyzer” (`when: routing_state_needs_refresh` on the POC pack):

1. File missing.
2. Invalid JSON or `schema_version` ≠ 1, or `fields` sets router-owned keys.
3. `stale` rule `routing_state` older than `spec` (POC). Spec (Phase 11): older
   than spec / context / decisions / challenges / alignment / gaps_map /
   challenges_map (`stale_vs` in `routing_conditions.yaml`).
4. After any step that mutates those artifacts (write/check/resolve/challenge/
   alignment).

Validate ids (pack `extra_advice`, **warn**): `routing-state-missing`,
`routing-state-stale`. Invalid JSON is reported as missing. Spec dispatch does
**not** route to `analyze-routing` (not in spec graph). POC dispatch does.

## When to run the analyzer

| Trigger | Who |
|---------|-----|
| No `ROUTING_STATE` / stale / invalid | POC router → step `analyze-routing` |
| Orchestrator just finished a mutating step | next delegate; stale rule fires (POC) |
| Manual `/analyze-routing <slug>` | human / dual-run |

Do **not** call the analyzer from `pipeline_dispatch.py`.

## Packs

| Pack | Role |
|------|------|
| `spec` | Collectors live. Overlay collector `routing_state` last, gated. `routing_conditions.yaml` is SSOT for skill + parity. |
| `routing-poc` | Graph node `analyze-routing`, overlay collector, dispatch from JSON. |

## Phase 11 parity

Dual-run: **A** = `populate_status` collectors (live default). **B** = same
populate, overlay `fields` from JSON (`spec_overlay_collector`). Overlay-field
collectors do not win over JSON (`routing_state` is last).

When overlay applies:

- parity B-mode only: `overlay_context(mode="on")` or `PIPELINE_ROUTING_STATE_OVERLAY=1`
- otherwise collectors (Mode A / live). Golden spec 24 cases unchanged.

JSON missing/stale is `extra_advice` (`routing-state-missing` / `routing-state-stale`),
not a live overlay trigger. Live overlay-if-fresh would be Phase 12 cutover:
`needs_check_feature` depends on run-log, which is not in `stale_vs`.

```bash
PYTHONPATH=scripts python3 scripts/routing_state_parity.py <slug>
PYTHONPATH=scripts python3 scripts/routing_state_parity.py <slug> --json
PYTHONPATH=scripts python3 scripts/routing_state_parity.py <slug> --strict
PYTHONPATH=scripts python3 scripts/routing_state_parity.py <slug> \
  --replay scripts/fixtures/routing_state_replay/<slug>.json
```

Replay fixtures are collector snapshots (no LLM):
`scripts/routing_state_replay_from_collectors.py`.

Phase 12: `analyze-routing` in spec `graph.yaml`, cutover dispatch to overlay,
drop spec collectors. Phase 13: frontend codegen.

## Tests

Phase 10 **не** добавляет отдельный smoke-check на `routing-poc` — pack уже в
`dispatch-golden N/N`, `pipeline-compile` и `golden-coverage:packs`. Phase 11
smoke still does **not** add `dispatch:routing-poc` (optional).

```bash
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --check
PYTHONPATH=scripts python3 scripts/pipeline_routing_state_test.py
PYTHONPATH=scripts python3 scripts/routing_state_parity_test.py
PYTHONPATH=scripts python3 scripts/pipeline_dispatch_golden_test.py
PYTHONPATH=scripts python3 scripts/pipeline_golden_coverage_test.py
PYTHONPATH=scripts python3 scripts/pipeline_smoke_test.py
PYTHONPATH=scripts python3 scripts/routing_state_parity.py <slug> --strict
```

| Gate | Что закрывает |
|------|----------------|
| `pipeline_routing_state_test` | schema, overlay, spec gating, validate ids |
| `routing_state_parity_test` | replay identity / mismatch / fixture slugs |
| `dispatch_golden` `routing-poc` | missing / stale / open_gaps → next_step |
| `dispatch_golden` `spec` | эталон 24+ **без изменений** |
| `golden-coverage:packs` | `routing-poc` не orphan |
| smoke | aggregate golden + compile; **нет** `dispatch:routing-poc` |
| `routing_state_parity.py --strict` | A vs B fields + dispatch |

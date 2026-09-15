# Pipeline routing-state (Phase 12)

LLM **analyzer** writes a JSON snapshot. Deterministic **router** reads it
through `populate_status` overlay — no LLM in `build_dispatch`. Spec live
dispatch is routing-state only. Domain collectors are gone from the hot path.

```
delegate → (missing/stale) analyze-routing → routing-analyzer
        → <slug>-routing-state.json
        → overlay_collector → predicates → next step
```

Orchestrator runtime loop is unchanged: delegate → action → append_run_log →
ingest → validate (`--pipeline <id>`). Analyzer is a graph step on **spec**
and `routing-poc`.

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
Pack collector id: `routing_state`. Spec `status.yaml`: `collector_mode: routing_state`.

## Spec status fields the router uses

Inventory from `pipelines/spec/status.yaml` + `predicates.py` (dispatch `when:`).
Analyzer populates the same names so overlay is 1:1.

| Field | Source | Predicates / invariant |
|-------|--------|------------------------|
| `has_context` | artifacts.context (exists) + JSON | `not_has_context` |
| `has_spec` | artifacts.spec + JSON | `not_has_spec` |
| `has_alignment` | artifacts.alignment + JSON | `alignment_limit_exhausted`, `alignment_missing_or_stale` |
| `has_challenges` | artifacts.challenges + JSON | `open_challenges`, `no_challenges_file` |
| `has_gaps_map` | artifacts.gaps_map + JSON | invariant `needs-check-feature` |
| `has_challenges_map` | artifacts.challenges_map + JSON | invariant |
| `has_decisions` | artifacts.decisions + JSON | display |
| `decisions_needs_answer` | JSON | `needs_answer_*`, `ask_user` |
| `decisions_pending_apply` | JSON | `pending_apply_*` |
| `decisions_needs_answer_alignment` | JSON | `_alignment_only` / `_challenges_only` |
| `decisions_pending_apply_alignment` | JSON | `_alignment_only` / `_challenges_only` |
| `open_gaps` | JSON | `open_gaps`, `*_with_gaps`, `*_challenges_only` |
| `challenges.open` | JSON | `open_challenges` |
| `verdict` | JSON | `alignment_pass`, `alignment_limit_exhausted` |
| `alignment_iteration` | JSON | limit / mismatch / pending-apply alignment |
| `critical_major_mismatch` | JSON | `critical_major_mismatch_resolvable` |
| `alignment_stale` | engine after overlay | mismatch / pending-apply alignment |
| `stale` | engine stale[] | `alignment_missing_or_stale`; `routing_state` id → P5 |
| `needs_check_feature` + `_reason` | JSON fields (hook sync + analyzer) | invariant `needs-check-feature` |
| `step_completion` | JSON metadata (hook only) | not router overlay |

Not used by spec dispatch: `open_questions`, `spec_lines`, `context_lines`,
other `challenges.*` counts (display). Engine still computes **mtime** `stale[]`
and `alignment_stale` from `status.yaml` after the overlay (`ENGINE_RECOMPUTED_FIELDS`).

Full mapping: `pipelines/spec/routing_conditions.yaml` (`status_fields` SSOT for the skill;
`edge_conditions` SSOT for `when:` bodies — Phase 13).
Parity / replay: [PIPELINE-PARITY.md](PIPELINE-PARITY.md).

## Stale / missing

Treat as “run analyzer” (`when: routing_state_needs_refresh`, spec P5):

1. File missing (or overlay load error).
2. Invalid JSON or `schema_version` ≠ 1, or `fields` sets router-owned keys.
3. `stale` rule `routing_state` older than spec / context / decisions /
   challenges / alignment / gaps_map / challenges_map (`stale_vs`).
4. After any **mutating** step (write / resolve / challenge / alignment /
   find-context). Gate steps (check-feature with no file change) do **not**
   go here — the hook stamps JSON instead.

Validate ids (pack `extra_advice`, **block** on spec): `routing-state-missing`,
`routing-state-stale`. Invalid JSON is reported as missing. Dispatch also
routes to `analyze-routing`. POC validate stays **warn**.

## When to run the analyzer

| Trigger | Who |
|---------|-----|
| No `ROUTING_STATE` / stale / invalid | spec (and POC) router → step `analyze-routing` |
| Orchestrator just finished a mutating step | next delegate; stale rule fires |
| Gate step that still rewrote artifacts | hook skips stamp; stale rule fires |
| Manual `/analyze-routing <slug>` | human |

Do **not** call the analyzer from `pipeline_dispatch.py`.

## Hook sync (gate steps only)

Generic box — not spec-only. Hook **does not** rewrite JSON after mutating
steps (that would clear `stale` and skip the LLM analyzer).

1. Pack `status.yaml`: `collector_mode: routing_state` + `routing_state_sync`.
2. `sync_after_steps` — allowlist of **gate** steps (no artifact rewrite).
   Spec: `check-feature`. Empty list = never stamp (routing-poc).
3. `skip_after_steps` — extra deny (default: `analyze-routing`).
4. Pack module `pipelines/<id>/routing_state_sync.py` → `refresh_fields(...)`
   updates **invariants only** (e.g. `needs_check_feature`). No domain parse.
5. If JSON is already stale vs `stale_vs`, hook **skips** so analyzer runs.
6. Router reads `fields` only — no run-log on dispatch.

Spec invariant `needs_check_feature`: pack config
`routing_state_sync.invariants.needs_check_feature.satisfied_by_step` names
which completed gate step clears the flag (default `check-feature`).

Golden `25-check-feature-stamped-json`. See
[fixtures/dispatch_golden/spec/COVERAGE.md](fixtures/dispatch_golden/spec/COVERAGE.md).

## Packs

| Pack | Role |
|------|------|
| `spec` | Overlay always on. Graph node `analyze-routing`. `routing_conditions.yaml` SSOT. |
| `routing-poc` | Reference cutover (refresh → overlay `open_gaps`). Unchanged. |

## Phase 12 cutover checklist

1. Spec `graph.yaml` has `analyze-routing` + refresh edges after mutating steps
   and from analyzer to every dispatch target.
2. `dispatch.yaml` P5 `routing_state_needs_refresh` → `analyze-routing`;
   existing P10–P140 `when:` → `next` mappings unchanged.
3. Fallback when JSON is not ready → `analyze-routing`.
4. `status.yaml` `collector_mode: routing_state`; collectors[] = `routing_state` only.
5. Golden option B: `cases.json` `routing_state` key; runner writes JSON **after**
   `touch_after` / run-log and utimes it newest.
6. `pipeline_compile.py --apply` then `--check`.

```bash
PYTHONPATH=scripts python3 scripts/routing_state_replay_from_collectors.py --golden
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --apply
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --check
PYTHONPATH=scripts python3 scripts/pipeline_routing_state_test.py
PYTHONPATH=scripts python3 scripts/routing_state_parity_test.py
PYTHONPATH=scripts python3 scripts/pipeline_dispatch_golden_test.py
PYTHONPATH=scripts python3 scripts/pipeline_golden_coverage_test.py
PYTHONPATH=scripts python3 scripts/pipeline_smoke_test.py
PYTHONPATH=scripts python3 scripts/routing_state_parity.py pipeline-viewer-smoke --strict
python3 scripts/feature_status_test.py
```

Replay fixtures are collector-equivalent snapshots (no LLM):
`scripts/routing_state_baseline.py` via `routing_state_replay_from_collectors.py`.

Phase 13: `routing_conditions.yaml` is the SSOT for **two** things:

| Section | Who reads it | Purpose |
|---------|--------------|---------|
| `status_fields` | analyze-routing skill, `--catalog` field palette, baseline | Analyzer JSON field names + instructions |
| `edge_conditions` | interpreter + codegen + `--catalog` edge editor | `when:` formulas (`expr`) + `dispatch` (priority / next / outcome) |

Runtime choice **A**: `scripts/pipeline_edge_conditions.evaluate_edge_condition`. Spec
`predicates.py` does not contain domain formulas. Router stays deterministic (no LLM).
Authoring: PlantUML / UI label → `pipeline_routing_codegen.py` → YAML → `pipeline_compile.py --apply`.
See [PIPELINE-PACK-AUTHORING.md](PIPELINE-PACK-AUTHORING.md) Phase 13.

## Tests

```bash
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --check
PYTHONPATH=scripts python3 scripts/pipeline_routing_state_test.py
PYTHONPATH=scripts python3 scripts/routing_state_parity_test.py
PYTHONPATH=scripts python3 scripts/pipeline_dispatch_golden_test.py
PYTHONPATH=scripts python3 scripts/pipeline_golden_coverage_test.py
PYTHONPATH=scripts python3 scripts/pipeline_smoke_test.py
```

| Gate | Что закрывает |
|------|----------------|
| `pipeline_routing_state_test` | schema, overlay always-on, validate block ids |
| `routing_state_parity_test` | replay identity / mismatch / fixture slugs |
| `dispatch_golden` `routing-poc` | missing / stale / open_gaps → next_step |
| `dispatch_golden` `spec` | 24 cases; expect unchanged; JSON injected |
| `golden-coverage:packs` | `routing-poc` не orphan |
| smoke | aggregate golden + compile + `dispatch:spec-with-routing-state` |
| `routing_state_parity.py --strict` | baseline vs overlay on `--replay` |

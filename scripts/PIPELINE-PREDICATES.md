# Pipeline predicates

`when:` in `dispatch.yaml` is a **name**, not a formula. The catalog maps that
name to an implementation. New semantics → register a predicate; do **not**
edit `pipeline_router.py`.

```
dispatch.yaml (when: open_gaps)
    ↓
pipeline_predicates.catalog_names(pipeline_id)
    ↓
core (status.yaml artifacts + counters)
  + edge_conditions YAML (Phase 13 interpreter)
  + optional pack predicates.py (thin wrapper / reasons)
    ↓
pipeline_router._evaluate_rules → next step
```

**Phase 13 (choice A):** the **body** of a domain `when:` is a declarative `expr` in
`pipelines/<id>/routing_conditions.yaml` → `edge_conditions`. Runtime evaluates it with
`evaluate_edge_condition(expr, status)` (`scripts/pipeline_edge_conditions.py`). No LLM
in dispatch. Do **not** add new functions to `predicates.py` for spec — edit YAML and
re-run codegen / `--check`.

`when: "open_gaps && has_spec"` is still invalid as a dispatch string. Combine in `expr`
(`all` / `any` / `not` / `ref`).

## Core vs domain vs edge_conditions

| Kind | Where | Names |
|------|--------|--------|
| **Core** | `scripts/pipeline_predicates.py` + `status.yaml` | Auto from artifacts: `not_has_<id>`, `has_<id>`, `file_missing_<id>`. Counters: `{field}_gt_{n}` (+ optional `alias`) |
| **Edge conditions** | `routing_conditions.yaml` `edge_conditions` | Pack `when:` formulas + `dispatch.priority` / `next`. Interpreter. |
| **Domain module** | `pipelines/<id>/predicates.py` | Thin wrapper: register interpreter preds, `reason_for_predicate`, invariants. Optional if YAML has `reason:`. |

Core builders (`CORE_BUILDERS`): `file_missing`, `has_artifact`, `field_gt`,
`pending_apply`. They are factories, not `when:` names. Spec also lists `not_has_context`
/ `not_has_spec` in `edge_conditions` with `core: true` so the UI can put them on edges;
the interpreter matches the core builders.

Spec `core_predicates.counters` also keep **legacy aliases** `field_gt` and
`pending_apply` in the catalog (same fn as `decisions_needs_answer_gt_0` /
`decisions_pending_apply_gt_0`). **Dispatch does not use them.**

Artifact-missing reasons come from `status.yaml` (`missing_reason` on the
artifact, or `core_predicates.reasons` / `messages.predicates`). Domain reasons
come from pack `reason_for_predicate` (spec keeps the mapping) or `edge_conditions.reason`.

## Spec pack (reference)

`pipelines/spec/dispatch.yaml` `when:` (must exist in `edge_conditions` or core):

| when | kind | status fields |
|------|------|----------------|
| `routing_state_needs_refresh` | edge | missing / invalid JSON / `routing_state` in stale |
| `not_has_context` | core + edge | `has_context` |
| `not_has_spec` | core + edge | `has_spec` |
| `alignment_limit_exhausted` | edge | `has_alignment`, `alignment_iteration`, `verdict` |
| `needs_answer_with_gaps` | edge | `decisions_needs_answer_gaps` |
| `needs_answer_alignment_only` | edge | `decisions_needs_answer_alignment`, `open_gaps` |
| `needs_answer_challenges_only` | edge | `decisions_needs_answer_challenges` |
| `pending_apply_with_gaps` | edge | `decisions_pending_apply_gaps` |
| `pending_apply_alignment_only` | edge | `decisions_pending_apply_alignment`, mismatch, iteration |
| `pending_apply_challenges_only` | edge | `decisions_pending_apply_challenges` |
| `critical_major_mismatch_resolvable` | edge | `critical_major_mismatch`, iteration, stale |
| `open_gaps` | edge | `open_gaps` |
| `open_challenges` | edge | `has_challenges`, `challenges.open` |
| `no_challenges_file` | edge | `has_challenges` |
| `alignment_missing_or_stale` | edge | `has_alignment`, `stale` |
| `alignment_pass` | edge | `verdict` |
| `alignment_fail_reaudit` | edge | (always true; last rule) |

Constants (`alignment_max_iterations`, verdict strings) live in
`pipelines/spec/status.yaml` → `constants:`, not `artifact_paths.py`.
`dispatch.rules` must equal `edge_conditions.*.dispatch` (codegen `--apply` syncs).

## Add a domain predicate (YAML, not Python)

1. **Codegen** from a labeled edge (see [PIPELINE-PACK-AUTHORING.md](PIPELINE-PACK-AUTHORING.md)
   Phase 13) **or** add `edge_conditions.<name>` by hand (`expr` + `dispatch`).
2. **Instruction** — new fields referenced in `expr` need `status_fields` (codegen stubs
   them). Fill the analyzer instruction.
3. **Compile**

```bash
PYTHONPATH=scripts python3 scripts/pipeline_routing_codegen.py --pipeline <id> --apply
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --check
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --apply
```

Do not add the name to the router. Do not implement a new function in `predicates.py`.

## Authoring palette

```bash
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --catalog
```

JSON includes `catalog_version` **2**, `predicates.core`, `predicates.by_pipeline.<id>`,
`routing_conditions.<id>.fields` / `.edge_conditions` / `.stale_vs`, and `runtime.<id>.loop`.
Contract: [PIPELINE-PACK-AUTHORING.md](PIPELINE-PACK-AUTHORING.md).

## Example: new `when` for calibration

Calibration today has a graph and **no** dispatch rules (`dispatch_supported: false`).
To add a router later, prefer `edge_conditions` + interpreter (same as spec). A pack
`predicates.py` is only needed for custom reasons / invariants.

## Compile checks

`--check` fails when:

- `when:` is not in `catalog_names(pipeline_id)` (typo)
- `when:` has no callable implementation
- `reason_for` is empty
- `DOMAIN_PREDICATE_NAMES` ≠ `PREDICATES` keys (if the pack still has predicates.py)
- invariant `id` ∉ `invariant_names(pipeline_id)`
- `core_predicates.counters` uses an unknown builder
- pack has `edge_conditions` and a `when:` is missing from that map **and** core
- `dispatch.rules` ≠ `edge_conditions.dispatch` (run codegen `--apply`)
- `expr` field refs not in `status_fields` / `engine_fields` / artifact `exists_as`
- `graph.edges[].condition` id not in `edge_conditions`

## Tests

Predicate catalog has its **own** suite. It is **not** in smoke (smoke is 31/31
including a thin registry check).

```bash
PYTHONPATH=scripts python3 scripts/pipeline_predicates_test.py
PYTHONPATH=scripts python3 scripts/pipeline_routing_codegen_test.py
PYTHONPATH=scripts python3 scripts/pipeline_dispatch_golden_test.py
PYTHONPATH=scripts python3 scripts/pipeline_smoke_test.py
python3 scripts/feature_status_test.py
```

`pipeline_predicates_test.py`: catalog vs dispatch `when:` vs `edge_conditions` ids,
domain callable + reason, constants from yaml, compile typo, stub golden
(`fixtures/predicate_golden/spec/`). `pipeline_smoke_test.py` does not import it.


# Pipeline predicates

`when:` in `dispatch.yaml` is a **name**, not a formula. The catalog maps that
name to a function. New semantics → register a predicate in the pack; do **not**
edit `pipeline_router.py`.

```
dispatch.yaml (when: open_gaps)
    ↓
pipeline_predicates.catalog_names(pipeline_id)
    ↓
core (status.yaml artifacts + counters) + domain (pack predicates.py)
    ↓
pipeline_router._evaluate_rules → next step
```

No `when: "open_gaps && has_spec"` — combine conditions in Python in the pack.

## Core vs domain

| Kind | Where | Names |
|------|--------|--------|
| **Core** | `scripts/pipeline_predicates.py` + `status.yaml` | Auto from artifacts: `not_has_<id>`, `has_<id>`, `file_missing_<id>`. Counters: `{field}_gt_{n}` (+ optional `alias`) |
| **Domain** | `pipelines/<id>/predicates.py` | Pack-specific `when:` (spec: `open_gaps`, `alignment_pass`, …) |

Core builders (`CORE_BUILDERS`): `file_missing`, `has_artifact`, `field_gt`,
`pending_apply`. They are factories, not `when:` names. `core_predicates_from_status`
uses them so a new pack does not edit the engine.

Spec `core_predicates.counters` also keep **legacy aliases** `field_gt` and
`pending_apply` in the catalog (same fn as `decisions_needs_answer_gt_0` /
`decisions_pending_apply_gt_0`). **Dispatch does not use them.** Rules use
domain names (`open_gaps`, `pending_apply_with_gaps`, …), not `field_gt`.
Do not add new `when:` rules that point at the aliases.

Artifact-missing reasons come from `status.yaml` (`missing_reason` on the
artifact, or `core_predicates.reasons` / `messages.predicates`). Domain reasons
come from pack `reason_for_predicate`. The engine does not hardcode spec strings.

## Spec pack (reference)

`pipelines/spec/dispatch.yaml` `when:`:

| when | kind | status fields |
|------|------|----------------|
| `not_has_context` | core | `has_context` |
| `not_has_spec` | core | `has_spec` |
| `alignment_limit_exhausted` | domain | `has_alignment`, `alignment_iteration`, `verdict` |
| `needs_answer_with_gaps` | domain | `decisions_needs_answer`, `open_gaps` |
| `needs_answer_alignment_only` | domain | `decisions_needs_answer_alignment`, `open_gaps` |
| `needs_answer_challenges_only` | domain | `decisions_needs_answer*` , `open_gaps` |
| `pending_apply_with_gaps` | domain | `decisions_pending_apply`, `open_gaps` |
| `pending_apply_alignment_only` | domain | `decisions_pending_apply_alignment`, mismatch, iteration |
| `pending_apply_challenges_only` | domain | `decisions_pending_apply*` , `open_gaps` |
| `critical_major_mismatch_resolvable` | domain | `critical_major_mismatch`, iteration, stale |
| `open_gaps` | domain | `open_gaps` |
| `open_challenges` | domain | `has_challenges`, `challenges.open` |
| `no_challenges_file` | domain | `has_challenges` |
| `alignment_missing_or_stale` | domain | `has_alignment`, `stale` |
| `alignment_pass` | domain | `verdict` |
| `alignment_fail_reaudit` | domain | (always true; last rule) |

Constants (`alignment_max_iterations`, verdict strings) live in
`pipelines/spec/status.yaml` → `constants:`, not `artifact_paths.py`.

## Add a domain predicate (3 steps)

1. **Implement** in `pipelines/<id>/predicates.py` — function
   `(root, task_id, status) -> bool` plus `reason_for_predicate` text.
2. **Declare** — add the name to `DOMAIN_PREDICATE_NAMES` **and** `PREDICATES`.
   Compile fails if the two sets differ.
3. **Use** — a rule in `pipelines/<id>/dispatch.yaml`:

```yaml
- priority: 90
  when: open_gaps
  next: resolve-gaps
```

Then:

```bash
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --check
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --apply
```

Do not add the name to the router. Do not put the condition in YAML.

## Authoring palette

```bash
PYTHONPATH=scripts python3 scripts/pipeline_compile.py --catalog
```

JSON includes `predicates.core` (union of auto core names across packs) and
`predicates.by_pipeline.<id>` (core + domain for that pack).

## Example: new `when` for calibration

Calibration today has a graph and **no** dispatch rules (`dispatch_supported: false`).
To add a router later:

1. `pipelines/calibration/predicates.py` — e.g. `gold_missing` reading a status field.
2. `DOMAIN_PREDICATE_NAMES = frozenset({"gold_missing"})` and `PREDICATES`.
3. `pipelines/calibration/dispatch.yaml`:

```yaml
rules:
  - priority: 10
    when: gold_missing
    next: snapshot-baseline
```

4. `--check` / `--apply`. Golden: `scripts/fixtures/dispatch_golden/calibration/`.

No edits to `pipeline_router.py` or `pipeline_predicates.py` unless you need a
**new core builder** (rare).

## Compile checks

`--check` fails when:

- `when:` is not in `catalog_names(pipeline_id)` (typo)
- `when:` has no callable implementation
- `reason_for` is empty
- `DOMAIN_PREDICATE_NAMES` ≠ `PREDICATES` keys
- invariant `id` ∉ `invariant_names(pipeline_id)`
- `core_predicates.counters` uses an unknown builder

## Tests

Predicate catalog has its **own** suite. It is **not** in smoke (smoke is 31/31
including a thin registry check).

```bash
PYTHONPATH=scripts python3 scripts/pipeline_predicates_test.py
PYTHONPATH=scripts python3 scripts/pipeline_dispatch_golden_test.py
PYTHONPATH=scripts python3 scripts/pipeline_smoke_test.py
python3 scripts/feature_status_test.py
```

`pipeline_predicates_test.py`: catalog vs dispatch `when:`, domain callable +
reason, constants from yaml, compile typo, stub golden
(`fixtures/predicate_golden/spec/`). `pipeline_smoke_test.py` does not import it.

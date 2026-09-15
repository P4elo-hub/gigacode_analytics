# Spec routing-state parity (Phase 12)

Live spec dispatch is overlay. Domain collectors are not on the hot path.
`--replay` remains a CI drift check: baseline parse
(`scripts/routing_state_baseline.py`) vs overlay of a fixture JSON.

SSOT for field semantics: `pipelines/spec/routing_conditions.yaml`.
Contract: [PIPELINE-ROUTING-STATE.md](PIPELINE-ROUTING-STATE.md).

```
A  baseline parse (overlay off + routing_state_baseline)  → dispatch via temp JSON
B  populate_status overlay from replay / live JSON         → dispatch
```

Live A-mode (collectors-first) is **deprecated** and gone for spec.
`overlay_context(mode="off")` is tests/baseline only.

`stale` and `alignment_stale` are engine mtime after overlay (JSON copies are
informational). Replay fixtures: `scripts/fixtures/routing_state_replay/`.

## Field map

| Field | Baseline parser | routing_conditions | Predicate(s) / invariant | Dispatch impact |
|-------|-----------------|--------------------|--------------------------|-----------------|
| `has_context` | artifacts.context | `has_context` | `not_has_context` | P20 find-context |
| `has_spec` | artifacts.spec | `has_spec` | `not_has_spec` | P30 write-feature |
| `has_decisions` | artifacts.decisions | `has_decisions` | (display) | none |
| `has_gaps_map` | artifacts.gaps_map | `has_gaps_map` | `needs-check-feature` | invariant → check-feature |
| `has_challenges` | artifacts.challenges | `has_challenges` | `open_challenges`, `no_challenges_file` | P100 / P110 |
| `has_challenges_map` | artifacts.challenges_map | `has_challenges_map` | `needs-check-feature` | invariant |
| `has_alignment` | artifacts.alignment | `has_alignment` | limit, `alignment_missing_or_stale` | P10 / P120 |
| `decisions_needs_answer` | decisions table | `decisions_needs_answer` | `needs_answer_with_gaps`, `_challenges_only`, ask_user | P40 / P50 + ask_user |
| `decisions_pending_apply` | decisions table | `decisions_pending_apply` | `pending_apply_with_gaps`, `_challenges_only` | P60 / P70 |
| `decisions_needs_answer_alignment` | decisions table | `decisions_needs_answer_alignment` | `_alignment_only`, `_challenges_only` | P45 / P50 |
| `decisions_pending_apply_alignment` | decisions table | `decisions_pending_apply_alignment` | `_alignment_only`, `_challenges_only` | P65 / P70 |
| `open_gaps` | spec gaps | `open_gaps` | `open_gaps`, `*_with_gaps` | P40 / P60 / P90 |
| `open_questions` | context questions | `open_questions` | (display) | none |
| `challenges.open` | challenges table | `challenges` | `open_challenges` | P100 |
| `verdict` | alignment frontmatter | `verdict` | `alignment_pass`, limit | P10 / P130 |
| `alignment_iteration` | alignment frontmatter | `alignment_iteration` | limit, mismatch, pending alignment | P10 / P65 / P80 |
| `critical_major_mismatch` | alignment frontmatter | `critical_major_mismatch` | mismatch resolvable, pending alignment | P65 / P80 |
| `alignment_stale` | alignment_stale | `alignment_stale` | mismatch, pending alignment | P65 / P80 (engine) |
| `stale` | stale[] | `stale` | `alignment_missing_or_stale`; P5 refresh | P5 / P120 |
| `needs_check_feature` | needs_check_feature | `needs_check_feature` | invariant `needs-check-feature` | after P70 → check-feature |
| `needs_check_feature_reason` | needs_check_feature | `needs_check_feature_reason` | invariant | (reason only) |

## Documented diffs

Replay fixtures are generated from the baseline parser
(`routing_state_replay_from_collectors.py`). On those snapshots **A vs B is
identity** — no known dispatch diffs.

A real LLM analyzer that disagrees with the baseline parser will show DIFF in
`routing_state_parity.py` (fields and/or `next_step` / `orchestrator_mode` /
`ready` / `must_continue`). Fix the skill or the JSON; do not change the
24 spec golden `expect` values without a waiver.

Golden migration is **option B**: `routing_state` on each case, injected by
`pipeline_dispatch_golden_test.py` after `touch_after` / run-log.

## Commands

```bash
PYTHONPATH=scripts python3 scripts/routing_state_replay_from_collectors.py --all
PYTHONPATH=scripts python3 scripts/routing_state_replay_from_collectors.py --golden
PYTHONPATH=scripts python3 scripts/routing_state_parity.py pipeline-viewer-smoke --strict
PYTHONPATH=scripts python3 scripts/routing_state_parity.py bph-moex-tax --strict
PYTHONPATH=scripts python3 scripts/routing_state_parity_test.py
```

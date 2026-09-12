<!--
Imported from: migration-standard-kit/skills\migration-analysis\SKILL.md
Current-state adaptation:
- Use only confirmed current behavior.
- Do not write TO BE, rollout/rollback, future requirements, design proposals, GAP/ASM/DESIGN markers as reader-facing content.
- Put unresolved or future/change-specific material into working-layer gaps, not into permanent KB pages.
-->
---
name: migration-analysis
disable-model-invocation: true
---

# Migration Analysis

## Purpose

Use this skill to document how data/schema changes are rolled out safely. This skill depends on confirmed data model changes or explicit greenfield design authorization.

## Required Files

| Artifact | Spec | Template | Canonical example | Quality gate |
|---|---|---|---|---|
| Migration plan | `spec-kit/migration-plan.schema.yaml` | `templates/migration-plan.template.md` | `examples/payment-status-backfill-migration-example.md` | `quality-gates/migration-review.yaml` |

## Instructions

1. Confirm migration scope.
   - Link to data model artifact or describe confirmed schema/data change.
   - If target schema is unknown, route to `data-standard-kit` first.

2. Classify migration type.
   - DDL, DML, backfill, cleanup, index build, constraint tightening, table split/merge, data correction.

3. Ask clarification-first questions.
   - Database engine/version.
   - Data volume.
   - Downtime allowance.
   - Online migration requirements.
   - Backward/forward compatibility window.
   - Validation method.

4. Write migration phases.
   - Pre-checks.
   - Expand phase.
   - Application compatibility phase.
   - Backfill phase.
   - Validation phase.
   - Contract/cleanup phase.

5. Add scripts only when evidence or authorization exists.

6. Register gaps and assumptions.

7. Run quality gate.

## Clarification Triggers

Ask before final plan when unknown:

- DB engine and version;
- expected row count / table size;
- lock/downtime constraints;
- migration tool (Flyway/Liquibase/manual/etc.);
- existing indexes/constraints;
- data validation query;
- current-state functionality toggle or dual-write period.

## Forbidden Without Evidence

- Exact SQL for destructive operations.
- Lock safety guarantees.
- Row counts, duration, batch size.
- Claiming zero-downtime without compatibility plan.

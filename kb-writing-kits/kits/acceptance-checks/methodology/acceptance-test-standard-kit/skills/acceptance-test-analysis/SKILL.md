<!--
Imported from: acceptance-test-standard-kit/skills\acceptance-test-analysis\SKILL.md
Current-state adaptation:
- Use only confirmed current behavior.
- Do not write TO BE, rollout/rollback, future requirements, design proposals, GAP/ASM/DESIGN markers as reader-facing content.
- Put unresolved or future/change-specific material into working-layer gaps, not into permanent KB pages.
-->
---
name: acceptance-test-analysis
description: Writes acceptance tests and scenarios using Given/When/Then, positive/negative/edge cases, regression scope, test data and traceability to requirements.
disable-model-invocation: true
---

# Acceptance Test Analysis

## Purpose

Use this skill to make current-state functionality behavior testable. Do not invent business rules, expected results, test data or thresholds without evidence.

## Required Files

| Artifact | Spec | Template | Canonical example | Quality gate |
|---|---|---|---|---|
| Acceptance tests | `spec-kit/acceptance-tests.schema.yaml` | `templates/acceptance-tests.template.md` | `examples/operation-sorting-acceptance-example.md` | `quality-gates/acceptance-tests-review.yaml` |

## Instructions

1. Collect source requirements and use cases.
2. Extract acceptance criteria.
3. Write Given/When/Then scenarios.
4. Cover positive, negative and edge cases.
5. Define test data.
6. Define regression scope.
8. Run quality gate.

## Clarification Triggers

Ask when unknown:

- expected result;
- edge/null/fallback behavior;
- test data source;
- roles/permissions;
- environments;
- acceptance owner;
- regression boundaries.

## Forbidden Without Evidence

- Expected result values.
- Test data records.
- SLA/performance thresholds.
- Security roles and permissions.
- Claiming a scenario is not needed without reason.

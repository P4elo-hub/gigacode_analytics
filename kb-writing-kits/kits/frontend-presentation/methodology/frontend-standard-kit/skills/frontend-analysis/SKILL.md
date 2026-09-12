<!--
Imported from: frontend-standard-kit/skills\frontend-analysis\SKILL.md
Current-state adaptation:
- Use only confirmed current behavior.
- Do not write TO BE, rollout/rollback, future requirements, design proposals, GAP/ASM/DESIGN markers as reader-facing content.
- Put unresolved or future/change-specific material into working-layer gaps, not into permanent KB pages.
-->
---
name: frontend-analysis
description: Documents frontend behavior for a current-state functionality: screens, UI states, user actions, API-to-UI mapping, validations, messages, loading/empty/error states and accessibility-relevant behavior.
disable-model-invocation: true
---

# Frontend Analysis

## Purpose

Use this skill to document what the user sees and how UI behavior changes. Do not invent screen names, API fields, text, validation or error handling without evidence.

## Required Files

| Artifact | Spec | Template | Canonical example | Quality gate |
|---|---|---|---|---|
| Frontend | `spec-kit/frontend.schema.yaml` | `templates/frontend.template.md` | `examples/operation-history-frontend-example.md` | `quality-gates/frontend-review.yaml` |

## Instructions

1. Identify UI scope.
   - Screens, components, user roles, devices/channels.

2. Capture user actions and states.
   - Default, loading, empty, success, validation error, system error, partial/degraded, disabled.

3. Map data to UI.
   - Source field -> UI element.
   - Formatting, sorting, filtering, visibility.

4. Document validation and messages.
   - Client-side and server-side errors.
   - Message text only if provided; otherwise gap.

5. Link backend artifacts.
   - Integration/API, data mapping, use case, observability/frontend metrics.

6. Register gaps and assumptions.

7. Run quality gate.

## Clarification Triggers

Ask when unknown:

- exact screen/component;
- user role;
- source API/query;
- sorting/filtering/null behavior;
- message text;
- empty/loading/error behavior;
- accessibility or localization constraints.

## Forbidden Without Evidence

- Exact UI copy.
- Field names and formats.
- Claiming no UI impact.
- Sorting/null/fallback behavior.
- Error messages and analytics events.

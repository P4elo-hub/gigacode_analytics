<!--
Imported from: process-standard-kit/skills\process-analysis\SKILL.md
Current-state adaptation:
- Use only confirmed current behavior.
- Do not write TO BE, rollout/rollback, future requirements, design proposals, GAP/ASM/DESIGN markers as reader-facing content.
- Put unresolved or future/change-specific material into working-layer gaps, not into permanent KB pages.
-->
---
name: process-analysis
disable-model-invocation: true
---

# Process Analysis

## Purpose

Use this skill to describe the current and target process. Do not invent actors, steps, systems, decisions or pain points without evidence.

## Required Files

| Artifact | Spec | Template | Canonical example | Quality gate |
|---|---|---|---|---|
| Process | `spec-kit/process.schema.yaml` | `templates/process.template.md` | `examples/operation-history-process-example.md` | `quality-gates/process-review.yaml` |

## Instructions

1. Decide whether process analysis is needed.

2. Identify participants.
   - Users, systems, operators, external systems, support/compliance actors.

3. Describe текущее поведение.
   - Current trigger, steps, decisions, outputs, pain points.
   - If current process is unknown, ask before final artifact unless draft requested.

   - Target trigger, steps, decisions, outputs, behavior changes.
   - Keep changes traceable to requirements.

5. Compare deltas.
   - Added, changed, removed steps.
   - New actors/systems.
   - Rules moved between actors/systems.

6. Link downstream artifacts.
   - Use cases for detailed scenarios.
   - UML activity for visual process.
   - Integration/data/frontend/NFR when process changes depend on them.

7. Register gaps and assumptions.

8. Run quality gate.

## Clarification Triggers

Ask when unknown:

- current process steps;
- target process owner;
- trigger and end state;
- actor responsible for decisions;
- exception/error branches;
- manual vs automated steps;
- systems involved.

## Output Discipline


## Forbidden Without Evidence

- Claiming current behavior if not provided.
- Claiming pain points, decisions or owner as fact.
- Saying process has no exceptions without evidence.

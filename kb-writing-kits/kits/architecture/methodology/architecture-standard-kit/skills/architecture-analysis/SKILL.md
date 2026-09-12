<!--
Imported from: architecture-standard-kit/skills\architecture-analysis\SKILL.md
Current-state adaptation:
- Use only confirmed current behavior.
- Do not write TO BE, rollout/rollback, future requirements, design proposals, GAP/ASM/DESIGN markers as reader-facing content.
- Put unresolved or future/change-specific material into working-layer gaps, not into permanent KB pages.
-->
---
name: architecture-analysis
description: Analyzes current-state functionality architecture, affected components, C4 diagrams, ownership boundaries, architectural decisions and impact. Use when a current-state functionality changes services, modules, containers, dependencies or runtime topology.
disable-model-invocation: true
---

# Architecture Analysis

## Purpose

Use this skill to document the architecture impact of a current-state functionality. The skill defines workflow; spec, template, example and gate define the output.

Do not invent components, owners, protocols, deployment topology, tech choices, databases or dependencies without evidence.

## Required Files

| Artifact | Spec | Template | Canonical example | Quality gate |
|---|---|---|---|---|
| Architecture | `spec-kit/architecture.schema.yaml` | `templates/architecture.template.md` | `examples/operation-history-architecture-example.md` | `quality-gates/architecture-review.yaml` |

## Instructions

1. Decide whether architecture analysis is needed.
   - Use when services, modules, containers, dependencies, ownership or deployment boundaries change.
   - Skip for pure wording/config changes with no architectural impact.

2. Identify components.
   - Capture existing components, new components and changed responsibilities.
   - Ask if component names or ownership are unknown.

3. Capture architectural drivers.
   - Requirements and NFRs that shape the design.

4. Describe diagrams.
   - Prefer C4 Container for system-level change.
   - Use C4 Component when one container changes internally.
   - Use PlantUML when writing diagram code.
   - Keep diagram consistent with component tables.

5. Document decisions.
   - Each decision has context, options, chosen option, rationale, consequences and status.

6. Document impact.

7. Register gaps and assumptions.
   - Every marker must have a row in `Gaps и допущения`.

8. Run quality gate.

## Clarification Triggers

Ask before final artifact when unknown:

- system/component names;
- source and target ownership;
- new vs existing component boundary;
- synchronous/asynchronous dependency direction;
- deployment/runtime boundary;
- data ownership;
- security boundary;
- reason for architectural choice.

If user requests quick draft, write draft with explicit gaps.

## Output Discipline

Use title `#### Архитектура фичи — <Название>`. Do not expose source standard IDs. Use Russian prose and preserve technical identifiers.

## Forbidden Without Evidence

- New service names, database ownership, teams, deployment topology, broker/topic names.
- Tech choices and trade-offs as accepted decisions.
- Statements like `не влияет на безопасность`, `конфликтов нет`, `миграция не нужна` without evidence or marker.

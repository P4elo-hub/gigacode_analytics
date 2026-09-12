<!--
Imported from: data-mapping-standard-kit/skills\data-mapping-analysis\SKILL.md
Current-state adaptation:
- Use only confirmed current behavior.
- Do not write TO BE, rollout/rollback, future requirements, design proposals, GAP/ASM/DESIGN markers as reader-facing content.
- Put unresolved or future/change-specific material into working-layer gaps, not into permanent KB pages.
-->
---
name: data-mapping-analysis
description: Documents source-to-target field mappings, transformations, enum/status mapping, null/default behavior, validation and rejection rules. Use when integrating sources, migrating data, or mapping API/event fields to domain/UI/storage models.
disable-model-invocation: true
---

# Data Mapping Analysis

## Purpose

Use this skill to produce a traceable mapping between source and target data. Do not invent source fields, target fields, enum values, transformations or defaults without evidence.

## Required Files

| Artifact | Spec | Template | Canonical example | Quality gate |
|---|---|---|---|---|
| Data mapping | `spec-kit/data-mapping.schema.yaml` | `templates/data-mapping.template.md` | `examples/bph-event-to-operation-mapping-example.md` | `quality-gates/data-mapping-review.yaml` |

## Instructions

1. Identify source and target.
   - Source contract/model, owner, version.
   - Target contract/model, owner, version.

2. Ask for evidence.
   - Source schema/example payload.
   - Target schema/model.
   - Business rules for transformations.

3. Map fields.
   - One row per target field.
   - Include source path, transformation, required/default/null behavior, validation and example.

4. Map enums/statuses.
   - Source value -> target value.
   - Unknown values and fallback behavior.

5. Define rejection/partial behavior.
   - What happens when required source field is missing or invalid.

6. Register gaps and assumptions.

7. Run quality gate.

## Clarification Triggers

Ask when unknown:

- source schema or sample payload;
- target field names;
- required/optional behavior;
- units, timezone, currency, precision;
- enum/status values;
- invalid data handling;
- owner of mapping approval.

## Forbidden Without Evidence

- Field names and paths.
- Units and timezone conversions.
- Default values and fallback behavior.
- Enum/status equivalence.
- Data rejection rules.

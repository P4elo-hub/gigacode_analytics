<!--
Imported from: security-threat-model-kit/skills\threat-model-analysis\SKILL.md
Current-state adaptation:
- Use only confirmed current behavior.
- Do not write TO BE, rollout/rollback, future requirements, design proposals, GAP/ASM/DESIGN markers as reader-facing content.
- Put unresolved or future/change-specific material into working-layer gaps, not into permanent KB pages.
-->
---
name: threat-model-analysis
description: Builds a security threat model for a current-state functionality: assets, actors, trust boundaries, data flows, threats, mitigations, residual risks and security gaps.
disable-model-invocation: true
---

# Threat Model Analysis

## Purpose

Use this skill to identify security threats and mitigations for a current-state functionality. Do not invent sensitive data classes, roles, auth rules or mitigations as accepted facts without evidence.

## Required Files

| Artifact | Spec | Template | Canonical example | Quality gate |
|---|---|---|---|---|
| Threat model | `spec-kit/threat-model.schema.yaml` | `templates/threat-model.template.md` | `examples/bph-getlink-events-threat-model-example.md` | `quality-gates/threat-model-review.yaml` |

## Instructions

1. Identify assets and sensitive data.
2. Identify actors and trust boundaries.
3. Document data flows.
4. Identify threats using STRIDE-style categories where useful.
5. Map mitigations and owners.
6. Record residual risks and decisions.
7. Link security NFR and observability.
9. Run quality gate.

## Clarification Triggers

Ask when unknown:

- data classification;
- auth/authz model;
- external system trust level;
- secrets/credentials handling;
- audit logging requirements;
- masking/encryption rules;
- security owner/approver.

## Forbidden Without Evidence

- Claiming no sensitive data.
- Claiming access is safe.
- Auth/authz rules.
- Encryption/masking requirements.
- Threat mitigations as implemented.

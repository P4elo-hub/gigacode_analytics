---
description: Requirement IDs and traceability in feature specifications
alwaysApply: true
---
# Rule: requirement traceability in feature specs

Every testable statement in `Feature-writing/<slug>/<slug>.md` should be traceable to an ID or gap marker.

## ID formats (scoped per feature slug)

- `BR-01, BR-02...` — business rules (section 1.1)
- `CN-01, CN-02...` — constraints and assumptions (section 2)
- `GAP-...` — unverified or missing facts (gap tables per block)
- `Q-01, Q-02...` — open questions (context doc or spec)
- Use case steps may reference `[BR-XX]` inline

Uniqueness is per feature: `bph-moex-tax.BR-01` and `other-feature.BR-01` are different.

## Where to place traceability

| Artifact | Required reference |
|----------|-------------------|
| Use case step | `[BR-XX]` when rule applies |
| Business rules table | `BR-XX` ID column |
| Gap table | `GAP-...` with source attempted |
| Context doc open questions | `Q-XX` |
| Code alignment finding | Doc section + claim quote |

## Verification rule

For every TO BE claim about contracts, DB, config, or behavior — `check-feature-code` must find CONFIRMED or document NOT FOUND / UNVERIFIABLE with evidence.

## Examples

```markdown
<!-- Bad — untestable vague statement -->
Налог отображается корректно.

<!-- Good -->
| BR-02 | MOEX_TAX маппится в operation_type=tax при additionalType=null | §4.2.2.2 |
```

---
description: Common process antipatterns to avoid in feature analytics
alwaysApply: true
---
# Rule: antipatterns to avoid

## Process antipatterns

- **Orchestrator improvises next step** — не угадывать шаг; только
  `pipeline_dispatch.py <slug> --json`. Завершать ход при `must_continue: true` запрещено.
- **Stopping after subagent fail** — fail/truncated output → `append_run_log --result fail`
  → dispatch → retry `task` в том же ходе. Не ждать «продолжи».
- **Pausing on pending-apply** — `pending-apply` → сразу resolver apply; пауза только на
  `needs-answer`.
- **Spec without gaps discipline** — unverified facts must be `[GAP-...]`, not prose that reads as confirmed.
- **Spec as implementation ticket** — SQL snippets and class names belong in technical sections (4.x), not in use case narratives.
- **Vague traceability** — "probably BR-01" is not a link. Explicit ID or gap marker required.
- **Skipping code alignment** — TO BE claims about DB/contracts without check against `repositories/` drift quickly.
- **Huge multi-week spec** — split into linked feature slugs instead of one 500-line document.

## Spec antipatterns

- **Use case with internal class names** — AS IS/TO BE describe service behavior, not `BphRawLinkedEventsWrapper`.
- **Partial contract tables** — list all fields (existing + new), mark new/changed columns.
- **Figma as source of truth** — Figma is reference; behavior = spec, structure = catalog sections.
- **Only happy path** — alternate flows, errors, and edge cases in use case tables.
- **Closing gaps by invention** — if not in analytics/code/context, leave `[GAP-...]` for human review.

## Code antipatterns (when reading repositories for context)

- **Analytics over code for technical facts** — code and migrations win for DDL, proto fields, config keys.
- **Confirming without file path** — every fact needs `repositories/...` or `db-export/...` citation.

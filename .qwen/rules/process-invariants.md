---
description: Development process invariants for feature analytics
alwaysApply: true
---
# Rule: development process invariants

These rules apply to ALL work in the project, regardless of artifact type.

## File size limit

Applies to **code, scripts, rules, skills and working artifacts**: target 100–200 lines per file; 300 is a hard cap, used only when splitting would hurt clarity. Long files degrade AI context quality. One file = one thing.

**Feature deliverables are exempt.** `SPEC`, `CONTEXT_DOC`, `*-decisions.md` and
`*-resolved.md` have no line limit. Section shape lives in kit `templates/` and
`quality-gates/`; heading order is `kb-writing-kits/spec-catalog.yaml`. Never drop a subsection the kit
requires and never compress wording to hit a line count. Completeness beats
brevity; split only if the feature scope itself should be split.

## Feature slug naming

Use `kebab-case-descriptive` for feature slugs: `bph-moex-tax`, `listing-events-query`. Never use generic names like `update`, `changes`, `wip`.

## Context hygiene

Clean the AI agent context before long `/write-feature` or `/check-feature` runs. Stale context leads to incoherent specs.

## Artifact layering

Lower-layer artifacts reference facts from upper layers:
1. Brief / business ask — why
2. Context doc (`Feature-context/`) — verified current state
3. Feature spec (`Feature-writing/`) — AS IS, TO BE, contracts, data, NFR
4. Code alignment report — verification vs `repositories/`

If a section has no source in context, analytics, or code — mark `[GAP-...]`, do not invent.

## Feature scope

One feature spec = one initiative, completable in 1–4 weeks. If scope grows beyond that, split into separate specs with linked slugs.

## CLI settings (permissions + hooks)

**Never edit** `.qwen/settings.json` or `.gigacode/settings.json` directly — agents are
denied; a bad overwrite drops `permissions` and breaks unattended runs.

| File | Purpose |
|------|---------|
| `settings.base.json` | context, tools, permissions (source of truth) |
| `settings.hooks.json` | PreToolUse / SubagentStop only |
| `settings.json` | **generated** — do not hand-edit |

After changing base or hooks:

```bash
python3 scripts/build_cli_settings.py
python3 scripts/build_cli_settings.py --check
```

`pipeline_smoke_test.py` validates that `permissions.allow` and hooks are present.

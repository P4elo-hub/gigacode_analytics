---
name: code-review
description: >
  Two-axis review (Standards + Spec) of uncommitted or session changes to feature
  specifications and analytics artifacts. Use after /check-feature or
  /resolve-code-alignment edits, before declaring spec ready, or when the user
  asks to review doc changes against spec-catalog and workspace rules.
user-invocable: false
---

# Code review (Standards ∥ Spec)

Review changes to analytics artifacts on two independent axes. Prefer parallel
sub-agents if available; otherwise run sequentially and report separately.

## When to run

After editing `Feature-writing/<slug>/<slug>.md` (via `/check-feature`, any
`/resolve-*` skill, or manual edits), **before**:

- declaring spec ready / PASS alignment
- suggesting commit (unless user opts out)

Also useful for reviewing diff in `Feature-context/` or related analytics files.

Skip if user explicitly opts out.

## 1. Pin the diff scope

Use, in order:

1. Path(s) user named (`Feature-writing/<slug>/<slug>.md`, …)
2. Else `git diff` / `git diff --staged` for analytics workspace files
3. Else ask the user

Empty diff → stop with «nothing to review».

## 2. Spec axis (feature specification)

Sources for `<slug>` (paths per `artifact-paths` rule):

1. `SPEC` (structure vs plan / `kb-writing-kits/spec-catalog.yaml`)
2. `CONTEXT_DOC` (postanovka, anchors, closed questions)
3. `ALIGNMENT` if exists (open MISMATCH?)
4. `GAPS_MAP` / `CHALLENGES_MAP` if exist (decisions must match spec text)
5. Relevant kit quality gates from `kb-writing-kits/`

Check:

- (a) missing sections / blocks per approved plan / catalog
- (b) AS IS/TO BE at scenario level (no internal classes in use cases)
- (c) contract tables complete (all fields, new marked)
- (d) open `[GAP-...]` not silently removed — closed ones must appear in `GAPS_MAP`
- (e) BR/CN/Q traceability consistent
- (f) no leftover decision logs / `[CH-...]` inside the spec
- (g) artifacts live in `FEATURE_DIR`, nothing loose in `Feature-writing/`

Quote section numbers and `BR-XX` / `GAP-...` ids. Under ~400 words.

## 3. Standards axis (workspace rules)

Sources:

- `.qwen/rules/` — `code-style`, `naming`, `traceability`,
  `process-invariants`, `antipatterns`, `analytics-workflow`
- File size (~200 lines target per process-invariants) — **не применять к
  деливераблам** (`SPEC`, `CONTEXT_DOC`, `*-resolved.md`): у них лимита нет

Per changed file/hunk: (a) rule breaches (cite rule); (b) naming / structure smells.
Hard vs judgement. Under ~400 words.

## 4. Aggregate

Present under `## Standards` and `## Spec` separately — do **not** merge.

One-line summary: findings count per axis + worst item within each.

## After review

- **Blockers** (wrong contract field, removed gap, broken `## N` order vs catalog): fix before `/check-feature-code`
- **Judgement smells**: report; fix if user agrees
- Do not expand feature scope beyond context-doc / brief

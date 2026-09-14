# opencode_analytics

Analytics workspace for History Operations (SIHIST / ИО). **CLI:** GigaCode (`gigacode`, `.gigacode/`, `GIGACODE.md`) or Qwen Code (`qwen`, `.qwen/`, `QWEN.md`). **Output:** feature specification in `Feature-writing/<slug>/<slug>.md`.

IMPORTANT: Read `repositories/`, `analytics/`, and `db-export/` before writing or reviewing specs. These three directories are local-only (gitignored); after a fresh clone they must be copied onto the machine.

## Workspace layout

| Path | Purpose |
|------|---------|
| `repositories/` | Cloned Java/gRPC service repos (read-only context) |
| `analytics/` | Current analytics and Confluence exports |
| `db-export/` | Database exports and dictionaries |
| `Feature-writing/<slug>/` | One folder per feature: spec + reports |
| `Feature-context/` | Context packs from find-context |
| `agent-logs/<slug>/` | CLI session telemetry (ingest from `~/.qwen/` / `~/.gigacode/`) |
| `Calibration/<slug>/` | Meta-pipeline: baseline, gold, proposals, benchmark (`HOW-WORK-CALIBRATION.md`) |
| `kb-writing-kits/` | Analytics methodology kits + `spec-catalog.yaml` |

Canonical artifact paths: rule `artifact-paths` (`.gigacode/rules/artifact-paths.md` or `.qwen/rules/artifact-paths.md`).

## Code style

- No hardcoded values — `.qwen/rules/code-style.md` (where applicable)
- Descriptive naming — `.qwen/rules/naming.md`

## Process invariants

- Feature specs follow `spec-catalog.yaml` block order and kb-writing-kits quality gates
- Unclosed `[GAP-...]` stay visible for manual review — do not invent facts
- Files should stay under 200 lines for AI context quality where practical — except feature deliverables in `Feature-writing/` and `Feature-context/`, which have no line limit
- Feature slugs: `kebab-case-descriptive`
- One slug = one folder in `Feature-writing/`; nothing loose at the top level
- Spec stays clean: answers live in `*-decisions.md`; maps live in `*-resolved.md`

## Analytics workflow

```
/find-context → /write-feature → /check-feature → /resolve-gaps → /challenge-feature → /resolve-challenges → /check-feature-code ↔ /resolve-code-alignment (≤3 iter)
```

`/feature-status <slug>` at any point: runs `scripts/feature_status.py` — open items, stale reports, one next step.
The orchestrator launches that next step itself — no «run check-feature?» prompt.
It pauses only for real questions (write-feature section plan, `needs-answer` in
`*-decisions.md`, missing brief, ambiguous slug).

**Final deliverable:** `Feature-writing/<slug>/<slug>.md` with PASS / PASS WITH GAPS code alignment.

### Re-run loops

- Any `/resolve-*` that touches BR/CN/use case → `/check-feature`
- `/resolve-code-alignment` → `/check-feature-code` (mandatory, closes the loop)
- Spec edits stale `*-code-alignment.md` → re-run code audit; `*-challenges.md` stale after apply is informational only (no auto re-challenge)
- All `/resolve-*` skills append closed `Q-XX` to the context doc § «Закрытые вопросы» and run `scripts/refresh_context.py`

## Skills (`.gigacode/skills/` / `.qwen/skills/`)

| Skill | Purpose |
|-------|---------|
| `feature-status` | Read-only dashboard via `scripts/feature_status.py` |
| `find-context` | Discovery + verified context doc → `Feature-context/<slug>.md` |
| `write-feature` | Правила одного блока spec; план и цикл — у оркестратора |
| `check-feature` | Review/fix feature spec vs sources |
| `check-feature-code` | Audit spec vs `repositories/` |
| `resolve-gaps` | Close spec `[GAP-...]` via `DECISIONS` + patch spec |
| `challenge-feature` | Adversarial questions → `-challenges.md` (read-only spec) |
| `resolve-challenges` | Close `CH-*` via `DECISIONS` + KB search → patch spec |
| `resolve-code-alignment` | Close closable alignment gaps via `DECISIONS` |
| `code-review` | Two-axis review of spec edits |
| `archive-session` | Ingest CLI jsonl → `agent-logs/<slug>/` |
| `analyze-telemetry` | Anomalies, skill repeats → `telemetry-analysis.md` |
| `capture-review` | Sync gold + human review themes |
| `analyze-delta` | Baseline vs gold diff |
| `propose-calibration` | Skill/process proposals from delta + telemetry |
| `apply-calibration` | Apply approved L1 skill patches |
| `benchmark-rerun` | Isolated rerun workspace under `Calibration/.../rerun/` |
| `calibrate` | Full calibration chain (calibration-orchestrator) |
| `analyze-routing` | Writes `<slug>-routing-state.json` (POC pack `routing-poc`; spec cutover Phase 11) |

## Slash commands and subagents

Slash commands live in `.gigacode/commands/` or `.qwen/commands/` (type `/` in CLI). Each command
dispatches to a subagent from the matching `agents/`, which loads the skill of the
same name from `skills/`. Основная сессия — оркестратор (`GIGACODE.md` / `QWEN.md`).

| Command | Subagent |
|---------|----------|
| `/feature-status` | основная сессия (`spec-orchestrator`) |
| `/find-context` | `context-researcher` |
| `/write-feature` | `spec-orchestrator` → `spec-writer` по одному блоку |
| `/check-feature` | `spec-reviewer` |
| `/resolve-gaps` | `gap-resolver` |
| `/challenge-feature` | `spec-challenger` |
| `/resolve-challenges` | `challenge-resolver` |
| `/check-feature-code` | `code-auditor` |
| `/resolve-code-alignment` | `alignment-resolver` |
| `/code-review` | `doc-reviewer` |
| `/archive-session` | оркестратор (ingest) |
| `/analyze-telemetry` | `session-telemetry-analyst` |
| `/snapshot-baseline` | скрипт / calibration-orchestrator |
| `/calibrate` | `calibration-orchestrator` |
| `/capture-review` | `review-capturer` |
| `/analyze-delta` | `regression-analyst` |
| `/propose-calibration` | `calibration-proposer` |
| `/apply-calibration` | `calibration-applier` |
| `/benchmark-rerun` | `benchmark-runner` |
| `/analyze-routing` | `routing-analyzer` (POC `--pipeline routing-poc`) |

Slash commands: `.gigacode/commands/` or `.qwen/commands/`. Pipeline rule: `analytics-workflow`.

## Process rules (`.gigacode/rules/` / `.qwen/rules/`)

| Rule file | Scope | What it covers |
|-----------|-------|----------------|
| `analytics-workflow` | global | SA command pipeline |
| `artifact-paths` | global | Canonical paths: one folder per slug |
| `traceability.md` | global | BR/CN/GAP IDs in feature specs |
| `process-invariants.md` | global | File size, slug naming |
| `antipatterns.md` | global | Common process mistakes |
| `gherkin.md` | `**/features/**/*.feature` | Gherkin conventions (if used in kits) |
| `code-style.md` | global | No magic values |
| `naming.md` | global | Descriptive names |

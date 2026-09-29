# Dispatch golden — music-production

Каждый dispatch `when` имеет case. Human verdict проверяется после записи
decision_id в knowledge store. Пока id не записан, побеждает
`decision_capture_pending`.

| when | case | next |
|---|---|---|
| `already_paused` | `limit-exhausted` | `paused` |
| `need_brief` | `no-brief` | `brief` |
| `lyrics_revise` | `lyrics-revise` | `lyrics-write` |
| `need_lyrics` | `need-lyrics` | `lyrics-write` |
| `lyrics_review_needed` | `need-lyrics-review` | `lyrics-review` |
| `need_sound` | `need-sound` | `sound-design` |
| `package_revise_lyrics` | `package-revise` | `lyrics-write` |
| `package_revise_production` | `package-revise-production` | `sound-design` |
| `package_revise_unspecified` | `package-revise-unspecified` | `package-review` |
| `package_review_needed` | `need-package-review` | `package-review` |
| `package_approval_needed` | `package-ready` | `package-approval` |
| `prompt_needed` | `prompt-needed` | `prompt-compile` |
| `generation_pending` | `generation-waiting` | `generate-batch` |
| `candidate_review_needed` | `candidates-need-review` | `candidate-review` |
| `base_selection_needed` | `candidates-need-choice` | `select-base` |
| `comparison_rejected` | `comparison-rejected` | `plan-revision` |
| `comparison_accepted_defects` | `revision-accepted-defects` | `diagnose-defects` |
| `qc_failed` | `final-qc-failed` | `diagnose-defects` |
| `comparison_accepted_clear` | `revision-accepted` | `final-qc` |
| `defect_open` | `defect-open` | `plan-revision` |
| `compare_needed` | `edit-ready-to-compare` | `compare-versions` |
| `revision_plan_ready` | `revision-plan-ready` | `execute-edit` |
| `base_selected_diagnose` | `base-selected` | `diagnose-defects` |
| `final_approval_needed` | `final-approval-waiting` | `final-approval` |
| `knowledge_needed` | `approved` | `capture-knowledge` |
| `track_approved` | `knowledge-captured` | `готово` |
| `decision_capture_pending` | `capture-pending-package` | `capture-knowledge` |
| `decision_capture_pending` | `capture-pending-base` | `capture-knowledge` |
| `decision_capture_pending` | `capture-pending-revision` | `capture-knowledge` |
| `decision_capture_pending` | `capture-pending-final` | `capture-knowledge` |
| `package_approve` | `package-approve-captured` | `prompt-compile` |
| `package_change_lyrics` | `package-change-lyrics` | `lyrics-write` |
| `package_change_production` | `package-change-production` | `sound-design` |
| `human_stop` | `package-stop` | `paused` |
| `base_select` | `base-select-captured` | `diagnose-defects` |
| `base_regenerate` | `base-regenerate-batch` | `prompt-compile` |
| `base_combine_direction` | `base-combine-direction` | `sound-design` |
| `base_change_lyrics` | `base-change-lyrics` | `lyrics-write` |
| `base_change_production` | `base-change-production` | `sound-design` |
| `human_stop` | `base-stop` | `paused` |
| `revision_budget_exhausted` | `revision-escalation-budget` | `revision-escalation` |
| `capability_missing` | `revision-escalation-capability` | `revision-escalation` |
| `defect_fix_limit_exhausted` | `revision-escalation-defect-limit` | `revision-escalation` |
| `comparisons_stagnant` | `revision-escalation-stagnant` | `revision-escalation` |
| `revision_accept` | `revision-accept` | `final-qc` |
| `revision_retry` | `revision-retry` | `plan-revision` |
| `revision_budget_exhausted` | `revision-retry-closed` | `revision-escalation` |
| `revision_rollback` | `revision-rollback` | `diagnose-defects` |
| `revision_rollback_needs_parent` | `revision-rollback-needs-parent` | `revision-escalation` |
| `human_stop` | `revision-stop` | `paused` |
| `final_approve` | `final-approve-captured` | `готово` |
| `final_request_revision` | `final-request-revision` | `diagnose-defects` |
| `human_stop` | `final-stop` | `paused` |
| `defect_open` | `revision-loop-plan` | `plan-revision` |
| `revision_plan_ready` | `revision-loop-edit` | `execute-edit` |
| `compare_needed` | `revision-loop-compare` | `compare-versions` |

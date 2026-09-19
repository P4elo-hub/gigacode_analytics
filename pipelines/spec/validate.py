"""Spec-pack extra validate rules (DECISIONS / challenge one-pass / check loop).

Missing or stale routing-state.json is block — dispatch must run analyze-routing
before domain steps. See scripts/PIPELINE-ROUTING-STATE.md.
"""

from __future__ import annotations

from pathlib import Path

from pipeline_common import last_successful_step_ts


def extra_advice(root: Path, task_id: str, status, dispatch: dict, report, add) -> None:
    if (
        status.decisions_pending_apply
        and dispatch.get("orchestrator_mode") == "ask_user"
    ):
        add(
            report,
            id="pending-apply-paused",
            severity="block",
            title="pending-apply не должен ставить паузу",
            detail=f"В DECISIONS есть pending-apply ({status.decisions_pending_apply})",
            fix="Сразу `task` на gap/challenge/alignment-resolver для apply — без ask_user.",
        )

    if status.decisions_needs_answer and dispatch.get("orchestrator_mode") != "ask_user":
        add(
            report,
            id="needs-answer-not-asked",
            severity="block",
            title="Есть needs-answer в DECISIONS — нужен ask_user",
            detail=f"Строк: {status.decisions_needs_answer}",
            fix=(
                "`pipeline_delegate.py` → action ask_user. Сейчас НЕ `task`. "
                "Опроси DECISIONS → pending-apply → `task` из JSON ask_user "
                "(без delegate). После apply — снова delegate."
            ),
        )

    from pipeline_routing_state import SPEC_STALE_VS, add_routing_state_advice
    from pipeline_status import resolve_artifact_paths

    pid = getattr(status, "pipeline_id", None) or "spec"
    paths = resolve_artifact_paths(root, task_id, pid)
    check_needed = bool(getattr(status, "needs_check_feature", False))
    check_reason = str(getattr(status, "needs_check_feature_reason", "") or "")
    last_check_ts = last_successful_step_ts(root, task_id, "check-feature")
    spec = paths.get("spec")
    last = getattr(report, "_last_history", None)
    if (
        check_needed
        and check_reason.startswith("SPEC новее GAPS_MAP")
        and last_check_ts is not None
        and spec is not None
        and spec.is_file()
        and last_check_ts >= spec.stat().st_mtime - 2
        and last
        and last.get("step") == "check-feature"
        and last.get("result") == "ok"
    ):
        add(
            report,
            id="check-feature-redundant-loop",
            severity="warn",
            title="check-feature уже прошёл после правки SPEC",
            detail="Dispatch снова просит check-feature из-за SPEC > GAPS_MAP",
            fix=(
                "check-feature уже ok после правки SPEC — dispatch должен идти дальше "
                "(resolve-gaps / check-feature-code)."
            ),
        )

    if status.has_challenges and report.next_step == "challenge-feature":
        add(
            report,
            id="challenge-repeat-blocked",
            severity="block",
            title="Повторный challenge-feature запрещён",
            detail="Файл CHALLENGES уже существует — автоматический re-challenge не допускается.",
            fix="Dispatch → check-feature-code (или resolve-challenges, если CH open>0).",
        )

    add_routing_state_advice(
        root,
        task_id,
        report,
        add,
        stale_vs=SPEC_STALE_VS,
        paths=paths,
        severity="block",
    )

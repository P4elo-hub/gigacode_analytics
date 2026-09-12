#!/usr/bin/env python3
"""Declarative dispatch router for the spec pipeline (phase 2)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from artifact_paths import ALIGNMENT_MAX_ITERATIONS, VERDICT_FAIL, VERDICT_PASS, VERDICT_PASS_WITH_GAPS
from feature_status import FeatureStatus, needs_check_feature
from pipeline_common import step_to_command, subagent_for_step

SCRIPTS = Path(__file__).resolve().parent
REGISTRY_PATH = SCRIPTS / "generated" / "pipeline_registry.json"

KNOWN_INVARIANTS = frozenset({"needs-check-feature"})
KNOWN_PREDICATES = frozenset(
    {
        "alignment_limit_exhausted",
        "not_has_context",
        "not_has_spec",
        "needs_answer_with_gaps",
        "needs_answer_challenges_only",
        "pending_apply_with_gaps",
        "pending_apply_challenges_only",
        "critical_major_mismatch_resolvable",
        "open_gaps",
        "open_challenges",
        "no_challenges_file",
        "alignment_missing_or_stale",
        "alignment_pass",
        "alignment_fail_reaudit",
    }
)
VALID_STEPS = frozenset(
    {
        "find-context",
        "write-feature",
        "check-feature",
        "resolve-gaps",
        "challenge-feature",
        "resolve-challenges",
        "check-feature-code",
        "resolve-code-alignment",
    }
)
VALID_OUTCOMES = frozenset({"ready", "stopped"})
# Legacy runs alignment/context/spec checks before needs_check_feature (graph gate).
INVARIANT_AFTER_PRIORITY = 30


@dataclass
class DispatchDecision:
    next_step: str = ""
    next_reason: str = ""
    ready: bool = False
    stopped: bool = False


def load_dispatch_spec(registry_path: Path | None = None) -> dict:
    path = registry_path or REGISTRY_PATH
    data = json.loads(path.read_text(encoding="utf-8"))
    dispatch = data.get("dispatch") or {}
    spec = dispatch.get("spec")
    if not isinstance(spec, dict):
        raise ValueError("registry dispatch.spec missing")
    return spec


def _predicate_alignment_limit_exhausted(_root: Path, _slug: str, status: FeatureStatus) -> bool:
    return (
        status.has_alignment
        and status.alignment_iteration >= ALIGNMENT_MAX_ITERATIONS
        and status.verdict == VERDICT_FAIL
    )


def _predicate_not_has_context(_root: Path, _slug: str, status: FeatureStatus) -> bool:
    return not status.has_context


def _predicate_not_has_spec(_root: Path, _slug: str, status: FeatureStatus) -> bool:
    return not status.has_spec


def _predicate_needs_answer_with_gaps(_root: Path, _slug: str, status: FeatureStatus) -> bool:
    return status.decisions_needs_answer > 0 and bool(status.open_gaps)


def _predicate_needs_answer_challenges_only(_root: Path, _slug: str, status: FeatureStatus) -> bool:
    return status.decisions_needs_answer > 0 and not status.open_gaps


def _predicate_pending_apply_with_gaps(_root: Path, _slug: str, status: FeatureStatus) -> bool:
    return status.decisions_pending_apply > 0 and bool(status.open_gaps)


def _predicate_pending_apply_challenges_only(_root: Path, _slug: str, status: FeatureStatus) -> bool:
    return status.decisions_pending_apply > 0 and not status.open_gaps


def _predicate_critical_major_mismatch_resolvable(_root: Path, _slug: str, status: FeatureStatus) -> bool:
    return (
        status.critical_major_mismatch > 0
        and status.alignment_iteration < ALIGNMENT_MAX_ITERATIONS
    )


def _predicate_open_gaps(_root: Path, _slug: str, status: FeatureStatus) -> bool:
    return bool(status.open_gaps)


def _predicate_open_challenges(_root: Path, _slug: str, status: FeatureStatus) -> bool:
    return status.has_challenges and status.challenges.open > 0


def _predicate_no_challenges_file(_root: Path, _slug: str, status: FeatureStatus) -> bool:
    return not status.has_challenges


def _predicate_alignment_missing_or_stale(_root: Path, _slug: str, status: FeatureStatus) -> bool:
    return not status.has_alignment or "alignment" in status.stale


def _predicate_alignment_pass(_root: Path, _slug: str, status: FeatureStatus) -> bool:
    return status.verdict in {VERDICT_PASS, VERDICT_PASS_WITH_GAPS}


def _predicate_alignment_fail_reaudit(_root: Path, _slug: str, status: FeatureStatus) -> bool:
    return True


PREDICATES: dict[str, Callable[[Path, str, FeatureStatus], bool]] = {
    "alignment_limit_exhausted": _predicate_alignment_limit_exhausted,
    "not_has_context": _predicate_not_has_context,
    "not_has_spec": _predicate_not_has_spec,
    "needs_answer_with_gaps": _predicate_needs_answer_with_gaps,
    "needs_answer_challenges_only": _predicate_needs_answer_challenges_only,
    "pending_apply_with_gaps": _predicate_pending_apply_with_gaps,
    "pending_apply_challenges_only": _predicate_pending_apply_challenges_only,
    "critical_major_mismatch_resolvable": _predicate_critical_major_mismatch_resolvable,
    "open_gaps": _predicate_open_gaps,
    "open_challenges": _predicate_open_challenges,
    "no_challenges_file": _predicate_no_challenges_file,
    "alignment_missing_or_stale": _predicate_alignment_missing_or_stale,
    "alignment_pass": _predicate_alignment_pass,
    "alignment_fail_reaudit": _predicate_alignment_fail_reaudit,
}


def reason_for_predicate(when: str, status: FeatureStatus) -> str:
    if when == "alignment_limit_exhausted":
        return (
            f"лимит цикла alignment исчерпан ({ALIGNMENT_MAX_ITERATIONS}), "
            "нужен ручной разбор ALIGNMENT"
        )
    if when == "not_has_context":
        return "нет проверенного контекста"
    if when == "not_has_spec":
        return "спецификация не написана"
    if when == "needs_answer_with_gaps":
        return (
            f"{status.decisions_needs_answer} строк needs-answer в DECISIONS — "
            "оркестратор опрашивает пользователя"
        )
    if when == "needs_answer_challenges_only":
        return (
            f"{status.decisions_needs_answer} строк needs-answer в DECISIONS (CH) — "
            "оркестратор опрашивает пользователя"
        )
    if when == "pending_apply_with_gaps":
        return (
            f"применить pending-apply из DECISIONS ({status.decisions_pending_apply} строк)"
        )
    if when == "pending_apply_challenges_only":
        return (
            f"применить pending-apply из DECISIONS "
            f"({status.decisions_pending_apply} строк, CH)"
        )
    if when == "critical_major_mismatch_resolvable":
        return "spec противоречит коду"
    if when == "open_gaps":
        if status.decisions_needs_answer:
            return (
                f"незакрытые факты ({len(status.open_gaps)}); "
                "оркестратор спрашивает needs-answer в DECISIONS"
            )
        if status.decisions_pending_apply:
            return (
                f"незакрытые факты ({len(status.open_gaps)}); "
                "применить pending-apply из DECISIONS"
            )
        return f"незакрытые факты ({len(status.open_gaps)})"
    if when == "open_challenges":
        return f"незакрытые corner cases ({status.challenges.open})"
    if when == "no_challenges_file":
        return "критический разбор не проводился"
    if when == "alignment_missing_or_stale":
        return "сверка с кодом отсутствует или устарела"
    if when == "alignment_pass":
        return "spec готов"
    if when == "alignment_fail_reaudit":
        return "alignment без PASS / PASS WITH GAPS"
    return ""


def decision_from_rule(rule: dict, status: FeatureStatus) -> DispatchDecision:
    when = rule["when"]
    next_step = rule.get("next")
    outcome = rule.get("outcome")
    reason = reason_for_predicate(when, status)

    if outcome == "ready":
        return DispatchDecision(next_step="", next_reason=reason, ready=True)
    if outcome == "stopped" or next_step is None:
        return DispatchDecision(next_step="", next_reason=reason, stopped=True)
    return DispatchDecision(next_step=str(next_step), next_reason=reason)


def evaluate_invariants(
    root: Path,
    slug: str,
    status: FeatureStatus,
    invariants: list[dict],
) -> DispatchDecision | None:
    for inv in invariants:
        inv_id = inv.get("id")
        if inv_id == "needs-check-feature":
            check_needed, check_reason = needs_check_feature(root, slug, status)
            if check_needed:
                step = inv.get("step") or "check-feature"
                return DispatchDecision(next_step=step, next_reason=check_reason)
    return None


def _rule_priority(rule: dict) -> int:
    return int(rule.get("priority", 0))


def _evaluate_rules(
    rules: list[dict],
    root: Path,
    slug: str,
    status: FeatureStatus,
    *,
    max_priority: int | None = None,
    min_priority: int | None = None,
) -> DispatchDecision | None:
    for rule in sorted(rules, key=_rule_priority):
        priority = _rule_priority(rule)
        if max_priority is not None and priority > max_priority:
            continue
        if min_priority is not None and priority <= min_priority:
            continue
        when = rule.get("when")
        if when not in PREDICATES:
            continue
        if PREDICATES[when](root, slug, status):
            return decision_from_rule(rule, status)
    return None


def evaluate_dispatch(
    root: Path,
    slug: str,
    status: FeatureStatus,
    *,
    dispatch_spec: dict | None = None,
) -> DispatchDecision:
    spec = dispatch_spec if dispatch_spec is not None else load_dispatch_spec()
    invariants = spec.get("invariants") or []
    rules = spec.get("rules") or []

    early = _evaluate_rules(
        rules,
        root,
        slug,
        status,
        max_priority=INVARIANT_AFTER_PRIORITY,
    )
    if early is not None:
        return early

    invariant_decision = evaluate_invariants(root, slug, status, invariants)
    if invariant_decision is not None:
        return invariant_decision

    late = _evaluate_rules(
        rules,
        root,
        slug,
        status,
        min_priority=INVARIANT_AFTER_PRIORITY,
    )
    if late is not None:
        return late

    return DispatchDecision(next_step="check-feature-code", next_reason="alignment без PASS / PASS WITH GAPS")


def apply_router_decision(status: FeatureStatus, root: Path, slug: str | None = None) -> None:
    """Apply compiled dispatch rules to FeatureStatus (includes finalize)."""
    from feature_status import _finalize_orchestrator_mode

    slug = slug or status.slug
    decision = evaluate_dispatch(root, slug, status)

    if decision.ready:
        status.ready = True
        status.next_command = ""
        status.next_step = ""
        status.next_subagent = ""
        status.next_reason = decision.next_reason
        _finalize_orchestrator_mode(status)
        return

    if decision.stopped or not decision.next_step:
        status.next_command = ""
        status.next_step = ""
        status.next_subagent = ""
        status.next_reason = decision.next_reason
        _finalize_orchestrator_mode(status)
        return

    status.next_step = decision.next_step
    status.next_command = step_to_command(decision.next_step, status.slug)
    status.next_subagent = subagent_for_step(decision.next_step)
    status.next_reason = decision.next_reason
    _finalize_orchestrator_mode(status)

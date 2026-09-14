#!/usr/bin/env python3
"""Declarative dispatch router. Rules come from dispatch.<pipeline_id>; when: from the catalog."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from pipeline_predicates import evaluate_invariant, predicates_for, reason_for
from pipeline_status import apply_dispatch_fields

SCRIPTS = Path(__file__).resolve().parent
REGISTRY_PATH = SCRIPTS / "generated" / "pipeline_registry.json"

VALID_OUTCOMES = frozenset({"ready", "stopped"})
INVARIANT_AFTER_PRIORITY = 30


@dataclass
class DispatchDecision:
    next_step: str = ""
    next_reason: str = ""
    ready: bool = False
    stopped: bool = False


def load_dispatch(pipeline_id: str, registry_path: Path | None = None) -> dict | None:
    """Return compiled dispatch.<pipeline_id>, or None when that pipeline has no rules."""
    path = registry_path or REGISTRY_PATH
    data = json.loads(path.read_text(encoding="utf-8"))
    dispatch = data.get("dispatch")
    if not isinstance(dispatch, dict):
        return None
    block = dispatch.get(pipeline_id)
    return block if isinstance(block, dict) else None


def load_dispatch_spec(pipeline_id: str = "spec", registry_path: Path | None = None) -> dict:
    spec = load_dispatch(pipeline_id, registry_path)
    if spec is None:
        raise ValueError(f"registry dispatch.{pipeline_id} missing")
    return spec


def decision_from_rule(rule: dict, status, pipeline_id: str) -> DispatchDecision:
    when = rule["when"]
    next_step = rule.get("next")
    outcome = rule.get("outcome")
    reason = reason_for(when, status, pipeline_id)
    if outcome == "ready":
        return DispatchDecision(next_step="", next_reason=reason, ready=True)
    if outcome == "stopped" or next_step is None:
        return DispatchDecision(next_step="", next_reason=reason, stopped=True)
    return DispatchDecision(next_step=str(next_step), next_reason=reason)


def evaluate_invariants(
    root: Path,
    task_id: str,
    status,
    invariants: list[dict],
    pipeline_id: str,
) -> DispatchDecision | None:
    for inv in invariants:
        result = evaluate_invariant(str(inv.get("id")), root, task_id, status, pipeline_id)
        if not result:
            continue
        needed, reason = result
        if needed:
            return DispatchDecision(next_step=str(inv.get("step") or ""), next_reason=reason)
    return None


def _rule_priority(rule: dict) -> int:
    return int(rule.get("priority", 0))


def _evaluate_rules(
    rules: list[dict],
    root: Path,
    task_id: str,
    status,
    pipeline_id: str,
    *,
    max_priority: int | None = None,
    min_priority: int | None = None,
) -> DispatchDecision | None:
    preds = predicates_for(pipeline_id)
    for rule in sorted(rules, key=_rule_priority):
        priority = _rule_priority(rule)
        if max_priority is not None and priority > max_priority:
            continue
        if min_priority is not None and priority <= min_priority:
            continue
        when = rule.get("when")
        pred = preds.get(when)
        if pred is None:
            continue
        if pred(root, task_id, status):
            return decision_from_rule(rule, status, pipeline_id)
    return None


def evaluate_dispatch(
    root: Path,
    slug: str,
    status,
    *,
    dispatch_spec: dict | None = None,
    pipeline_id: str = "spec",
) -> DispatchDecision:
    spec = dispatch_spec if dispatch_spec is not None else load_dispatch(pipeline_id)
    if spec is None:
        raise ValueError(f"registry dispatch.{pipeline_id} missing")
    invariants = spec.get("invariants") or []
    rules = spec.get("rules") or []
    after = int(spec.get("invariant_after_priority", INVARIANT_AFTER_PRIORITY))

    early = _evaluate_rules(rules, root, slug, status, pipeline_id, max_priority=after)
    if early is not None:
        return early

    invariant_decision = evaluate_invariants(root, slug, status, invariants, pipeline_id)
    if invariant_decision is not None:
        return invariant_decision

    late = _evaluate_rules(rules, root, slug, status, pipeline_id, min_priority=after)
    if late is not None:
        return late

    fallback = spec.get("fallback") or {}
    reason = str(fallback.get("reason") or "")
    if fallback.get("outcome") == "ready":
        return DispatchDecision(next_step="", next_reason=reason, ready=True)
    next_step = fallback.get("next")
    if next_step:
        return DispatchDecision(next_step=str(next_step), next_reason=reason)
    return DispatchDecision(next_step="", next_reason=reason, stopped=True)


def apply_router_decision(
    status,
    root: Path,
    slug: str | None = None,
    *,
    pipeline_id: str = "spec",
) -> None:
    slug = slug or status.slug
    pipe = getattr(status, "pipeline_id", None) or pipeline_id
    decision = evaluate_dispatch(root, slug, status, pipeline_id=pipe)

    if decision.ready:
        status.ready = True
        apply_dispatch_fields(status, "", decision.next_reason, pipe)
        return
    if decision.stopped or not decision.next_step:
        apply_dispatch_fields(status, "", decision.next_reason, pipe)
        return
    apply_dispatch_fields(status, decision.next_step, decision.next_reason, pipe)

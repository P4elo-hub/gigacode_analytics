"""Spec-pack domain predicates: names + reasons. Bodies live in edge_conditions YAML."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pipeline_edge_conditions import predicates_from_edge_conditions
from pipeline_pack import load_pack

PIPELINE_ID = "spec"
PREDICATES = predicates_from_edge_conditions(PIPELINE_ID)
DOMAIN_PREDICATE_NAMES = frozenset(PREDICATES)
DOMAIN_INVARIANT_NAMES = frozenset({"needs-check-feature"})


@lru_cache(maxsize=1)
def _constants() -> dict:
    try:
        return dict((load_pack(PIPELINE_ID).get("status") or {}).get("constants") or {})
    except FileNotFoundError:
        return {}


def _max_iter() -> int:
    return int(_constants().get("alignment_max_iterations", 3))


def reason_for_predicate(when: str, status) -> str:
    if when == "routing_state_needs_refresh":
        from pipeline_routing_state import STALE_ID

        error = getattr(status, "routing_state_error", "") or ""
        if error and error != "missing":
            return f"routing-state невалиден ({error}) — нужен analyze-routing"
        if STALE_ID in (getattr(status, "stale", None) or []):
            return "routing-state.json устарел — нужен analyze-routing"
        return "нет routing-state.json — нужен analyze-routing"
    if when == "routing_state_ready":
        return "routing-state актуален"
    if when == "alignment_limit_exhausted":
        return (
            f"лимит цикла alignment исчерпан ({_max_iter()}), "
            "нужен ручной разбор ALIGNMENT"
        )
    if when == "needs_answer_with_gaps":
        return (
            f"{status.decisions_needs_answer} строк needs-answer в DECISIONS — "
            "оркестратор опрашивает пользователя"
        )
    if when == "needs_answer_alignment_only":
        return (
            f"{status.decisions_needs_answer_alignment} строк needs-answer в DECISIONS "
            "(ALIGNMENT) — оркестратор опрашивает пользователя"
        )
    if when == "needs_answer_challenges_only":
        ch_only = status.decisions_needs_answer - status.decisions_needs_answer_alignment
        return (
            f"{ch_only} строк needs-answer в DECISIONS (CH) — "
            "оркестратор опрашивает пользователя"
        )
    if when == "pending_apply_with_gaps":
        return f"применить pending-apply из DECISIONS ({status.decisions_pending_apply} строк)"
    if when == "pending_apply_alignment_only":
        return (
            f"применить pending-apply из DECISIONS "
            f"({status.decisions_pending_apply_alignment} строк, ALIGNMENT)"
        )
    if when == "pending_apply_challenges_only":
        ch_only = status.decisions_pending_apply - status.decisions_pending_apply_alignment
        return f"применить pending-apply из DECISIONS ({ch_only} строк, CH)"
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


def evaluate_invariant(inv_id: str, root: Path, slug: str, status):
    from pipeline_pack import load_pack_module

    pid = getattr(status, "pipeline_id", None) or PIPELINE_ID
    collectors = load_pack_module(pid, "collectors")
    if collectors is None:
        return None
    table = getattr(collectors, "INVARIANTS", None)
    fn = table.get(inv_id) if isinstance(table, dict) else None
    if fn is None:
        return None
    return fn(root, slug, status)

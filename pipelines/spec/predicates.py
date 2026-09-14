"""Spec-pack domain predicates and reasons. YAML dispatch uses these names only."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pipeline_pack import load_pack

PIPELINE_ID = "spec"
DOMAIN_PREDICATE_NAMES = frozenset(
    {
        "alignment_limit_exhausted",
        "needs_answer_with_gaps",
        "needs_answer_alignment_only",
        "needs_answer_challenges_only",
        "pending_apply_with_gaps",
        "pending_apply_alignment_only",
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
DOMAIN_INVARIANT_NAMES = frozenset({"needs-check-feature"})


@lru_cache(maxsize=1)
def _constants() -> dict:
    try:
        return dict((load_pack(PIPELINE_ID).get("status") or {}).get("constants") or {})
    except FileNotFoundError:
        return {}


def _max_iter() -> int:
    return int(_constants().get("alignment_max_iterations", 3))


def _verdict_pass() -> set[str]:
    const = _constants()
    return {
        str(const.get("verdict_pass", "PASS")),
        str(const.get("verdict_pass_with_gaps", "PASS WITH GAPS")),
    }


def _verdict_fail() -> str:
    return str(_constants().get("verdict_fail", "FAIL"))


def _alignment_limit_exhausted(_root: Path, _slug: str, status) -> bool:
    return (
        status.has_alignment
        and status.alignment_iteration >= _max_iter()
        and status.verdict == _verdict_fail()
    )


def _needs_answer_with_gaps(_root: Path, _slug: str, status) -> bool:
    return status.decisions_needs_answer > 0 and bool(status.open_gaps)


def _needs_answer_alignment_only(_root: Path, _slug: str, status) -> bool:
    return status.decisions_needs_answer_alignment > 0 and not status.open_gaps


def _needs_answer_challenges_only(_root: Path, _slug: str, status) -> bool:
    return (
        status.decisions_needs_answer > status.decisions_needs_answer_alignment
        and not status.open_gaps
    )


def _pending_apply_with_gaps(_root: Path, _slug: str, status) -> bool:
    return status.decisions_pending_apply > 0 and bool(status.open_gaps)


def _pending_apply_alignment_only(_root: Path, _slug: str, status) -> bool:
    return (
        status.decisions_pending_apply_alignment > 0
        and status.critical_major_mismatch > 0
        and status.alignment_iteration < _max_iter()
        and not status.alignment_stale
    )


def _pending_apply_challenges_only(_root: Path, _slug: str, status) -> bool:
    return (
        status.decisions_pending_apply > status.decisions_pending_apply_alignment
        and not status.open_gaps
    )


def _critical_major_mismatch_resolvable(_root: Path, _slug: str, status) -> bool:
    return (
        status.critical_major_mismatch > 0
        and status.alignment_iteration < _max_iter()
        and not status.alignment_stale
    )


def _open_gaps(_root: Path, _slug: str, status) -> bool:
    return bool(status.open_gaps)


def _open_challenges(_root: Path, _slug: str, status) -> bool:
    return status.has_challenges and status.challenges.open > 0


def _no_challenges_file(_root: Path, _slug: str, status) -> bool:
    return not status.has_challenges


def _alignment_missing_or_stale(_root: Path, _slug: str, status) -> bool:
    return not status.has_alignment or "alignment" in status.stale


def _alignment_pass(_root: Path, _slug: str, status) -> bool:
    return status.verdict in _verdict_pass()


def _alignment_fail_reaudit(_root: Path, _slug: str, status) -> bool:
    return True


PREDICATES = {
    "alignment_limit_exhausted": _alignment_limit_exhausted,
    "needs_answer_with_gaps": _needs_answer_with_gaps,
    "needs_answer_alignment_only": _needs_answer_alignment_only,
    "needs_answer_challenges_only": _needs_answer_challenges_only,
    "pending_apply_with_gaps": _pending_apply_with_gaps,
    "pending_apply_alignment_only": _pending_apply_alignment_only,
    "pending_apply_challenges_only": _pending_apply_challenges_only,
    "critical_major_mismatch_resolvable": _critical_major_mismatch_resolvable,
    "open_gaps": _open_gaps,
    "open_challenges": _open_challenges,
    "no_challenges_file": _no_challenges_file,
    "alignment_missing_or_stale": _alignment_missing_or_stale,
    "alignment_pass": _alignment_pass,
    "alignment_fail_reaudit": _alignment_fail_reaudit,
}


def reason_for_predicate(when: str, status) -> str:
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

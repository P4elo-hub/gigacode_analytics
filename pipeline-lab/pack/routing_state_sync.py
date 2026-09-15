"""Gate-step stamp for spec pack — no domain parse (that is analyze-routing)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from pipeline_status import load_status_spec
from routing_state_baseline import needs_check_feature_from_completion


def _satisfied_by_step(pipeline_id: str, invariant_id: str, default: str) -> str:
    spec = load_status_spec(pipeline_id)
    sync = spec.get("routing_state_sync") if isinstance(spec.get("routing_state_sync"), dict) else {}
    inv = (sync.get("invariants") or {}).get(invariant_id) if isinstance(sync.get("invariants"), dict) else {}
    if isinstance(inv, dict) and inv.get("satisfied_by_step"):
        return str(inv["satisfied_by_step"])
    return default


def refresh_fields(
    root: Path,
    slug: str,
    paths: dict[str, Path],
    step_completion: dict[str, str],
    current_fields: dict,
) -> dict:
    del root
    out = dict(current_fields)
    review_step = _satisfied_by_step("spec", "needs_check_feature", "check-feature")
    status = SimpleNamespace(
        slug=slug,
        pipeline_id="spec",
        has_gaps_map=bool(out.get("has_gaps_map")),
        has_challenges=bool(out.get("has_challenges")),
        has_alignment=bool(out.get("has_alignment")),
    )
    needed, reason = needs_check_feature_from_completion(
        status,
        paths,
        step_completion,
        satisfied_by_step=review_step,
    )
    out["needs_check_feature"] = needed
    out["needs_check_feature_reason"] = reason
    return out

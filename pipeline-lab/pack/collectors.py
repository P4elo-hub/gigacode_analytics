"""Spec-pack collectors: routing-state overlay only (Phase 12).

Domain GAP/DECISIONS/CH/alignment parsing lives in:
- skill analyze-routing (runtime LLM, routing_conditions.yaml)
- scripts/routing_state_baseline.py (CI golden / replay etalon)

INVARIANTS.needs-check-feature reads overlay fields from JSON. SubagentStop hook
stamps `step_completion` only after pack `sync_after_steps` (spec: check-feature).
Mutating steps leave JSON stale so analyze-routing rewrites fields. Router reads
fields only — no run-log on dispatch.
"""

from __future__ import annotations

from pathlib import Path

from pipeline_routing_state import spec_overlay_collector

COLLECTORS = {
    "routing_state": spec_overlay_collector,
}


def needs_check_feature(_root: Path, _slug: str, status, _paths: dict[str, Path] | None = None):
    """Thin reader: gate-step hook stamp + analyzer keep JSON fields current."""
    return (
        bool(getattr(status, "needs_check_feature", False)),
        str(getattr(status, "needs_check_feature_reason", "") or ""),
    )


INVARIANTS = {
    "needs-check-feature": needs_check_feature,
}

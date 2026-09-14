"""Read routing-state.json into status fields. Spec collectors are untouched."""

from __future__ import annotations

from pipeline_routing_state import overlay_collector

COLLECTORS = {
    "routing_state": overlay_collector,
}

INVARIANTS: dict = {}

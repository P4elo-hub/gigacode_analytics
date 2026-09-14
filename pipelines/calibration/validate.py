"""Calibration-pack extra validate rules (graph / orchestrator_only; no dispatch)."""

from __future__ import annotations

from pathlib import Path

from pipeline_runtime import load_pipeline_schema


def extra_advice(root: Path, task_id: str, status, dispatch: dict, report, add) -> None:
    del root, task_id, status  # graph / orchestrator_only only
    mode = dispatch.get("orchestrator_mode") or ""
    if mode == "orchestrator_only" or not dispatch.get("dispatch_supported", True):
        add(
            report,
            id="cal-orchestrator-only",
            severity="ok",
            title="Calibration: orchestrator_only",
            detail=(
                "Правил dispatch нет. Оркестратор ведёт шаги по markdown; "
                "delegate проверяет рёбра графа."
            ),
            fix=(
                "`pipeline_delegate.py <slug> --cli <cli> --pipeline calibration` "
                "(при необходимости `--from-step` / `--to-step`)."
            ),
        )

    schema = load_pipeline_schema("calibration")
    orch = schema.get("orchestrator") or ""
    node_ids = {n.get("id") for n in schema.get("nodes") or [] if isinstance(n, dict)}
    if orch and orch not in node_ids:
        add(
            report,
            id="cal-graph-orchestrator-missing",
            severity="block",
            title="Граф calibration: нет узла оркестратора",
            detail=f"orchestrator={orch!r} отсутствует в nodes",
            fix="Исправь pipelines/calibration/graph.yaml и `pipeline_compile.py --apply`.",
        )

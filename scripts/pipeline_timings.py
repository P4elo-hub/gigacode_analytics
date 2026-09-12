"""Wall-clock timings per pipeline step from agent-logs + Qwen subagent meta."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from agent_logs import load_manifest
from archive_subagent_passes import load_archived_passes
from build_pipeline_graph import (
    history_sort_key,
    load_schema,
    parse_iso_ts,
    sort_history_by_ts,
    subagent_to_step,
)

ORCHESTRATOR_IDLE = "orchestrator-idle"
RUN_LOG_PASS_CAP_SEC = 600  # run-log gaps >10m are likely idle, not subagent work


def _fmt_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f} с"
    minutes = seconds / 60
    if minutes < 60:
        return f"{minutes:.1f} мин"
    hours = int(minutes // 60)
    rem = minutes % 60
    return f"{hours} ч {rem:.0f} мин"


def _step_labels(schema: dict) -> dict[str, str]:
    return {n["id"]: n.get("label") or n["id"] for n in schema.get("nodes", [])}


def _archived_passes(root: Path, slug: str, schema: dict) -> list[dict]:
    """Timings from agent-logs/subagent-passes.jsonl (archived Qwen meta)."""
    rows = load_archived_passes(root, slug)
    passes: list[dict] = []
    for row in rows:
        step = row.get("step") or subagent_to_step(schema, row.get("subagent") or "") or ""
        if not step:
            continue
        duration = row.get("duration_sec")
        if duration is None:
            start = parse_iso_ts(row.get("started_at"))
            end = parse_iso_ts(row.get("ended_at"))
            if start and end and end > start:
                duration = round((end - start).total_seconds(), 1)
        if not duration:
            continue
        passes.append(
            {
                "step": step,
                "subagent": row.get("subagent") or row.get("agent_type") or "",
                "start_ts": row.get("started_at"),
                "end_ts": row.get("ended_at"),
                "seconds": float(duration),
                "source": "agent-logs",
                "confidence": "high",
                "note": (row.get("description") or "")[:120],
                "session_id": row.get("session_id"),
                "call_id": row.get("call_id"),
            }
        )
    sort_history_by_ts(passes)
    return passes


def _event_passes(schema: dict, events: list[dict]) -> list[dict]:
    """Duration per agent.spawn → last subagent event before next spawn."""
    if not events:
        return []

    ordered = sorted(events, key=history_sort_key)
    spawns: list[dict] = []
    for event in ordered:
        if event.get("type") != "agent.spawn":
            continue
        subagent = str(event.get("subagent_type") or "").strip()
        step = subagent_to_step(schema, subagent) or ""
        if not step:
            continue
        spawns.append(
            {
                "ts": event.get("ts"),
                "step": step,
                "subagent": subagent,
                "description": event.get("description") or "",
            }
        )

    passes: list[dict] = []
    for index, spawn in enumerate(spawns):
        start = parse_iso_ts(spawn.get("ts"))
        if start is None:
            continue
        next_start: datetime | None = None
        if index + 1 < len(spawns):
            next_start = parse_iso_ts(spawns[index + 1].get("ts"))

        subagent = spawn["subagent"]
        needle = subagent.replace("-", "")
        end = start
        for event in ordered:
            event_ts = parse_iso_ts(event.get("ts"))
            if event_ts is None or event_ts < start:
                continue
            if next_start and event_ts >= next_start:
                break
            agent = str(event.get("agent") or "")
            if subagent in agent or needle in agent.replace("-", ""):
                if event_ts > end:
                    end = event_ts

        duration = max(0.0, (end - start).total_seconds())
        passes.append(
            {
                "step": spawn["step"],
                "subagent": subagent,
                "start_ts": spawn.get("ts"),
                "end_ts": end.isoformat().replace("+00:00", "Z"),
                "seconds": round(duration, 1),
                "source": "events",
                "confidence": "high",
                "note": spawn.get("description") or "",
            }
        )
    return passes


def _run_log_passes(schema: dict, run_log: list[dict]) -> tuple[list[dict], float]:
    """Fallback: interval until next row; long gaps capped → idle overflow."""
    step_ids = {n["id"] for n in schema.get("nodes", [])}
    rows = [r for r in run_log if (r.get("step") or "") in step_ids]
    sort_history_by_ts(rows)
    if not rows:
        return [], 0.0

    passes: list[dict] = []
    idle_overflow = 0.0
    for index, row in enumerate(rows):
        start = parse_iso_ts(row.get("ts"))
        if start is None or index + 1 >= len(rows):
            continue
        end = parse_iso_ts(rows[index + 1].get("ts"))
        if end is None:
            continue
        raw = max(0.0, (end - start).total_seconds())
        capped = min(raw, RUN_LOG_PASS_CAP_SEC)
        if raw > capped:
            idle_overflow += raw - capped
        passes.append(
            {
                "step": row.get("step") or "",
                "subagent": row.get("subagent") or "",
                "start_ts": row.get("ts"),
                "end_ts": rows[index + 1].get("ts"),
                "seconds": round(capped, 1),
                "source": "run-log",
                "confidence": "estimate",
                "note": (row.get("note") or "")[:120],
                "agent_run_id": row.get("agent_run_id"),
            }
        )
    return passes, idle_overflow


def _aggregate_by_step(passes: list[dict]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for row in passes:
        step = row.get("step") or ""
        if not step:
            continue
        totals[step] = totals.get(step, 0.0) + float(row.get("seconds") or 0)
    return totals


def _passes_for_step(
    step: str,
    *,
    meta_passes: list[dict],
    event_passes: list[dict],
    log_passes: list[dict],
) -> tuple[list[dict], str]:
    meta = [p for p in meta_passes if p.get("step") == step]
    if meta:
        return meta, "agent-logs"
    events = [p for p in event_passes if p.get("step") == step]
    if events:
        return events, "events"
    log = [p for p in log_passes if p.get("step") == step]
    return log, "run-log"


def build_step_timings(
    *,
    schema: dict,
    run_log: list[dict],
    events: list[dict],
    root: Path | None = None,
    slug: str = "",
    cli: str = "qwen",
    agent_run_ids: list[str] | None = None,
) -> dict:
    labels = _step_labels(schema)
    archived: list[dict] = []
    if root is not None and slug:
        archived = _archived_passes(root, slug, schema)

    event_passes = _event_passes(schema, events)
    log_passes, _log_idle_overflow = _run_log_passes(schema, run_log)

    all_steps = sorted(
        {p.get("step") for p in archived + event_passes + log_passes if p.get("step")}
    )

    by_step: dict[str, dict] = {}
    passes: list[dict] = []
    for step in all_steps:
        step_passes, source = _passes_for_step(
            step,
            meta_passes=archived,
            event_passes=event_passes,
            log_passes=log_passes,
        )
        if not step_passes:
            continue
        passes.extend(step_passes)
        seconds = sum(float(p.get("seconds") or 0) for p in step_passes)
        confidences = {p.get("confidence") or "estimate" for p in step_passes}
        confidence = "high" if confidences == {"high"} else "estimate"
        by_step[step] = {
            "id": step,
            "label": labels.get(step, step),
            "seconds": seconds,
            "passes": len(step_passes),
            "sources": {source},
            "confidence": confidence,
        }

    active_total = sum(item["seconds"] for item in by_step.values())
    steps = []
    for step_id, bucket in sorted(by_step.items(), key=lambda x: -x[1]["seconds"]):
        seconds = float(bucket["seconds"])
        steps.append(
            {
                "id": step_id,
                "label": bucket["label"],
                "seconds": round(seconds, 1),
                "minutes": round(seconds / 60, 2),
                "percent": 0.0,
                "passes": bucket["passes"],
                "source": "+".join(sorted(bucket["sources"])),
                "confidence": bucket["confidence"],
            }
        )
    total = active_total

    all_ts = [parse_iso_ts(r.get("ts")) for r in run_log if r.get("ts")]
    all_ts = [t for t in all_ts if t is not None]
    started = min(all_ts).isoformat().replace("+00:00", "Z") if all_ts else None
    ended = max(all_ts).isoformat().replace("+00:00", "Z") if all_ts else None

    wall_sec = 0.0
    if all_ts:
        wall_sec = max(0.0, (max(all_ts) - min(all_ts)).total_seconds())
    # Capped run-log passes already exclude overflow from active_total; wall − total
    # includes those gaps — do not add _log_idle_overflow again (double-count).
    idle_sec = max(0.0, wall_sec - total) if wall_sec else 0.0
    if idle_sec >= 30:
        steps.append(
            {
                "id": ORCHESTRATOR_IDLE,
                "label": "Паузы (оркестратор + пользователь)",
                "seconds": round(idle_sec, 1),
                "minutes": round(idle_sec / 60, 2),
                "percent": 0.0,
                "passes": 0,
                "source": "derived",
                "confidence": "estimate",
            }
        )
        total = total + idle_sec

    if total:
        for step in steps:
            step["percent"] = round(100 * float(step["seconds"]) / total, 1)

    notes: list[str] = []
    if archived:
        notes.append(
            "Источник: agent-logs/subagent-passes.jsonl (архив Qwen meta: createdAt→lastUpdatedAt)."
        )
    elif events:
        notes.append("Источник: events.jsonl (spawn → последняя активность subagent).")
    else:
        notes.append(
            "Только run-log: интервал между записями, cap 10 мин/проход — грубая оценка. "
            "Запустите sync или archive_subagent_passes для точных данных."
        )
    if log_passes and archived:
        uncovered = sorted(
            set(_aggregate_by_step(log_passes)) - set(_aggregate_by_step(archived))
        )
        if uncovered:
            notes.append(f"Без архива, оценка по run-log: {', '.join(uncovered)}.")
    if agent_run_ids and len(agent_run_ids) > 1:
        notes.append(f"Агрегат run-ов: {', '.join(agent_run_ids)}.")

    primary_source = "agent-logs" if archived else "events" if event_passes else "run-log"

    return {
        "total_sec": round(total, 1),
        "total_label": _fmt_duration(total),
        "wall_sec": round(wall_sec, 1) if wall_sec else None,
        "started_at": started,
        "ended_at": ended,
        "primary_source": primary_source,
        "steps": steps,
        "passes": passes,
        "notes": notes,
    }


def main() -> None:
    import argparse

    from artifact_paths import workspace_root
    from build_pipeline_graph import aggregate_run_history, load_aggregate_run_bundle, load_single_run_bundle, resolve_viewer_run_id

    parser = argparse.ArgumentParser(description="Step timings from agent-logs")
    parser.add_argument("slug")
    parser.add_argument("--workspace", type=Path, default=None)
    parser.add_argument("--run-id", default="auto")
    parser.add_argument("--cli", default="qwen")
    args = parser.parse_args()

    root = (args.workspace or workspace_root()).resolve()
    schema = load_schema()["pipelines"]["spec"]
    rid = resolve_viewer_run_id(root, args.slug, args.run_id)
    manifest = load_manifest(root, args.slug)
    cli = manifest.get("cli") or args.cli
    if aggregate_run_history(args.run_id):
        _, run_log, events, _, _, agent_run_ids = load_aggregate_run_bundle(
            root, args.slug, schema, through_run_id=rid
        )
    else:
        _, run_log, events, _, _ = load_single_run_bundle(root, args.slug, rid, schema)
        agent_run_ids = [rid]

    payload = build_step_timings(
        schema=schema,
        run_log=run_log,
        events=events,
        root=root,
        slug=args.slug,
        cli=cli,
        agent_run_ids=agent_run_ids,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

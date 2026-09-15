#!/usr/bin/env python3
"""Build runtime pipeline graph JSON from schema + agent-logs."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from agent_logs import (
    agent_logs_dir,
    events_path,
    load_manifest,
    metrics_path,
    run_log_path,
)
from artifact_paths import feature_dir, workspace_root
from pipeline_divergence import (
    analyze_divergence,
    filter_divergence_for_restart,
    finalize_divergence,
)
from pipeline_active_task import feature_active_task_path, load_active_task_for_slug
from pipeline_common import pipeline_step_order, subagent_for_step
from pipeline_dispatch import build_dispatch
from pipeline_runtime import DEFAULT_PIPELINE_ID, dispatch_supported
from pipeline_restart import (
    build_cli_commands,
    clear_restart_marker_if_ready,
    format_cli_block,
    load_restart_marker,
    redo_steps_from,
)
from feature_status import build_status
from calibration_paths import (
    baseline_spec_path,
    calibration_run_dir,
    delta_analysis_path,
    gold_spec_path,
    human_review_path,
    inputs_lock_path,
    load_calibration_manifest,
    proposals_table_path,
    rerun_dir,
    scorecard_path,
)
from pipeline_step_details import attach_node_details

SCHEMA_PATH = Path(__file__).resolve().parent / "pipeline_schema.json"

STATE_PENDING = "pending"
STATE_OK = "ok"
STATE_FAIL = "fail"
STATE_RETRY = "retry"
STATE_ACTIVE = "active"
STATE_SKIPPED = "skipped"
STATE_REDO = "redo"
STATE_STALE = "stale"
STATE_NEXT = "next"

RESULT_COLORS = {
    STATE_OK: "#22c55e",
    STATE_FAIL: "#ef4444",
    STATE_RETRY: "#eab308",
    STATE_ACTIVE: "#3b82f6",
    STATE_PENDING: "#94a3b8",
    STATE_SKIPPED: "#64748b",
    STATE_REDO: "#e879f9",
    STATE_STALE: "#57534e",
    STATE_NEXT: "#a855f7",
}

SESSION_IDLE_SECONDS = 180

CALIBRATION_STEPS = frozenset(
    {
        "snapshot-baseline",
        "capture-review",
        "analyze-delta",
        "analyze-telemetry",
        "propose-calibration",
        "apply-calibration",
        "benchmark-rerun",
        "calibrate",
    }
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slug")
    parser.add_argument("--run-id", default="auto")
    parser.add_argument("--pipeline", choices=("auto", "spec", "calibration"), default="auto")
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _run_log_nonempty(root: Path, slug: str, rid: str) -> bool:
    rd = run_log_path(root, slug, rid)
    return rd.is_file() and rd.stat().st_size > 0


def _latest_run_with_run_log(root: Path, slug: str) -> str | None:
    runs_root = agent_logs_dir(root, slug) / "runs"
    if not runs_root.is_dir():
        return None
    best: tuple[float, str] | None = None
    for child in runs_root.iterdir():
        if not child.is_dir() or not child.name.startswith("run-"):
            continue
        rid = child.name
        log = run_log_path(root, slug, rid)
        if not log.is_file() or log.stat().st_size == 0:
            continue
        mtime = log.stat().st_mtime
        if best is None or mtime > best[0]:
            best = (mtime, rid)
    return best[1] if best else None


def _run_sort_key(run_id: str) -> int:
    try:
        return int(run_id.replace("run-", ""))
    except ValueError:
        return 999_999


def list_agent_run_ids(root: Path, slug: str) -> list[str]:
    """Ordered run-NNN ids for slug (manifest + disk)."""
    manifest = load_manifest(root, slug)
    from_manifest = manifest.get("runs") or []
    runs_root = agent_logs_dir(root, slug) / "runs"
    from_disk: list[str] = []
    if runs_root.is_dir():
        from_disk = [
            p.name for p in runs_root.iterdir() if p.is_dir() and p.name.startswith("run-")
        ]
    return sorted(set(from_manifest) | set(from_disk), key=_run_sort_key)


def aggregate_run_history(run_id: str | None) -> bool:
    """Viewer default: merge all agent runs for one slug (auto/all/aggregate)."""
    return run_id in (None, "auto", "all", "aggregate")


def resolve_viewer_run_id(root: Path, slug: str, run_id: str | None) -> str:
    """Read-only: never creates manifest or new runs."""
    if run_id and run_id not in ("auto", "all", "aggregate"):
        return run_id
    manifest = load_manifest(root, slug)
    current = manifest.get("current_run")
    if current and _run_log_nonempty(root, slug, current):
        return current
    latest = _latest_run_with_run_log(root, slug)
    if latest:
        return latest
    if current:
        ev = events_path(root, slug, current)
        if ev.is_file() and ev.stat().st_size > 0:
            return current
    if current:
        return current
    runs = manifest.get("runs") or []
    if runs:
        return runs[-1]
    return "run-001"


def _tag_rows(rows: list[dict], agent_run_id: str) -> None:
    for row in rows:
        row.setdefault("agent_run_id", agent_run_id)


def load_single_run_bundle(
    root: Path,
    slug: str,
    rid: str,
    schema: dict,
) -> tuple[list[dict], list[dict], list[dict], set[str], list[dict]]:
    run_log = read_jsonl(run_log_path(root, slug, rid))
    events = read_jsonl(events_path(root, slug, rid))
    reached, spawn_rows = collect_spawn_steps(events, schema)
    history = filter_history_by_schema(merge_history(run_log, spawn_rows), schema)
    _tag_rows(history, rid)
    _tag_rows(run_log, rid)
    return history, run_log, events, reached, spawn_rows


def load_aggregate_run_bundle(
    root: Path,
    slug: str,
    schema: dict,
    *,
    through_run_id: str,
) -> tuple[list[dict], list[dict], list[dict], set[str], int, list[str]]:
    """Merge run-log + spawn events across runs up to through_run_id (inclusive)."""
    run_ids = list_agent_run_ids(root, slug)
    if through_run_id in run_ids:
        run_ids = run_ids[: run_ids.index(through_run_id) + 1]

    history: list[dict] = []
    run_log: list[dict] = []
    events: list[dict] = []
    reached: set[str] = set()
    spawn_total = 0
    included: list[str] = []

    for rid in run_ids:
        h, rl, ev, reached_run, spawns = load_single_run_bundle(root, slug, rid, schema)
        if not h and not rl and not spawns:
            continue
        included.append(rid)
        history.extend(h)
        run_log.extend(rl)
        events.extend(ev)
        reached |= reached_run
        spawn_total += len(spawns)

    sort_history_by_ts(history)
    sort_history_by_ts(run_log)
    return history, run_log, events, reached, spawn_total, included


def detect_pipeline(history: list[dict], requested: str) -> str:
    if requested != "auto":
        return requested
    steps = {row.get("step") for row in history}
    if steps & CALIBRATION_STEPS:
        return "calibration"
    return "spec"


def schema_step_ids(schema: dict) -> set[str]:
    return {n["id"] for n in schema.get("nodes", [])}


def filter_history_by_schema(history: list[dict], schema: dict) -> list[dict]:
    step_ids = schema_step_ids(schema)
    return [r for r in history if (r.get("step") or "") in step_ids]


def resolve_viewer_calibration_run_id(root: Path, slug: str) -> str | None:
    """Read-only: current calibration run for viewer (never creates runs)."""
    manifest = load_calibration_manifest(root, slug)
    current = manifest.get("current_run")
    if current:
        return current
    runs = manifest.get("runs") or []
    if runs:
        return runs[-1]
    runs_root = calibration_run_dir(root, slug, "run-001").parent
    if runs_root.is_dir():
        dirs = sorted(
            p.name for p in runs_root.iterdir() if p.is_dir() and p.name.startswith("run-")
        )
        return dirs[-1] if dirs else None
    return None


def _artifact_ts(path: Path, manifest_ts: str | None = None) -> str:
    if manifest_ts:
        return manifest_ts
    if path.is_file():
        dt = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_calibration_artifact_history(root: Path, slug: str, cal_run_id: str) -> list[dict]:
    """Synthetic run-log rows from Calibration/<slug>/runs/<id>/ artifacts."""
    manifest = load_calibration_manifest(root, slug)
    lock = inputs_lock_path(root, slug, cal_run_id)
    inputs: dict = {}
    if lock.is_file():
        try:
            inputs = json.loads(lock.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            inputs = {}

    subagents = {
        "snapshot-baseline": None,
        "capture-review": "review-capturer",
        "analyze-delta": "regression-analyst",
        "analyze-telemetry": "session-telemetry-analyst",
        "propose-calibration": "calibration-proposer",
        "apply-calibration": "calibration-applier",
        "benchmark-rerun": "benchmark-runner",
        "cal-done": None,
    }

    def artifact_row(step: str, ts: str, note: str) -> dict:
        return {
            "ts": ts,
            "step": step,
            "subagent": subagents.get(step),
            "result": "ok",
            "source": "calibration-artifact",
            "note": note,
        }

    rows: list[dict] = []
    baseline = baseline_spec_path(root, slug, cal_run_id)
    if lock.is_file() or baseline.is_file():
        ts = inputs.get("snapshotted_at") or manifest.get("last_snapshot")
        ts = _artifact_ts(lock if lock.is_file() else baseline, ts)
        rows.append(artifact_row("snapshot-baseline", ts, "baseline snapshot"))

    review = human_review_path(root, slug, cal_run_id)
    gold = gold_spec_path(root, slug, cal_run_id)
    if review.is_file():
        rows.append(artifact_row("capture-review", _artifact_ts(review), "human-review.md"))
    elif gold.is_file():
        ts = _artifact_ts(gold, manifest.get("last_gold_sync"))
        rows.append(artifact_row("capture-review", ts, "gold spec synced"))

    delta = delta_analysis_path(root, slug, cal_run_id)
    if delta.is_file():
        rows.append(artifact_row("analyze-delta", _artifact_ts(delta), "delta-analysis.md"))

    agent_run = inputs.get("agent_logs_run")
    if agent_run:
        tel = agent_logs_dir(root, slug) / "runs" / agent_run / "telemetry-analysis.md"
        if tel.is_file():
            rows.append(artifact_row("analyze-telemetry", _artifact_ts(tel), "telemetry-analysis.md"))

    proposals = proposals_table_path(root, slug, cal_run_id)
    if proposals.is_file():
        rows.append(artifact_row("propose-calibration", _artifact_ts(proposals), "proposals.md"))

    brief = rerun_dir(root, slug, cal_run_id) / "brief.txt"
    if brief.is_file():
        rows.append(artifact_row("benchmark-rerun", _artifact_ts(brief), "benchmark rerun prepared"))

    score = scorecard_path(root, slug, cal_run_id)
    if score.is_file():
        rows.append(artifact_row("cal-done", _artifact_ts(score), "scorecard.json"))

    return rows


def merge_calibration_history(
    run_log: list[dict],
    spawn_rows: list[dict],
    artifact_rows: list[dict],
) -> list[dict]:
    merged = merge_history(run_log, spawn_rows)
    keys = {(r.get("step"), r.get("ts")) for r in merged}
    for row in artifact_rows:
        key = (row.get("step"), row.get("ts"))
        if key in keys:
            continue
        merged.append(row)
        keys.add(key)
    sort_history_by_ts(merged)
    return merged


def parse_iso_ts(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


_EPOCH_UTC = datetime.min.replace(tzinfo=timezone.utc)


def history_sort_key(row: dict) -> tuple[datetime, str]:
    """Chronological key — never sort ISO timestamps as plain strings (06.288Z < 06Z lexically)."""
    parsed = parse_iso_ts(row.get("ts"))
    return (parsed or _EPOCH_UTC, row.get("ts") or "")


def sort_history_by_ts(rows: list[dict]) -> None:
    rows.sort(key=history_sort_key)


def last_event_time(events: list[dict]) -> datetime | None:
    for event in reversed(events):
        parsed = parse_iso_ts(event.get("ts"))
        if parsed:
            return parsed
    return None


def is_session_live(events: list[dict], idle_seconds: int = SESSION_IDLE_SECONDS) -> bool:
    """True only if telemetry shows activity within idle_seconds (avoid stale 'running')."""
    last = last_event_time(events)
    if not last:
        return False
    now = datetime.now(timezone.utc)
    return (now - last).total_seconds() < idle_seconds


def collect_spawn_steps(events: list[dict], schema: dict) -> tuple[set[str], list[dict]]:
    """Steps inferred from agent.spawn in events.jsonl."""
    reached: set[str] = set()
    spawn_rows: list[dict] = []
    for event in events:
        if event.get("type") != "agent.spawn":
            continue
        subagent = event.get("subagent_type")
        step = subagent_to_step(schema, subagent)
        if not step:
            continue
        reached.add(step)
        spawn_rows.append(
            {
                "ts": event.get("ts"),
                "step": step,
                "subagent": subagent,
                "result": "ok",
                "source": "events",
                "note": event.get("description"),
            }
        )
    return reached, spawn_rows


def infer_active_subagent(events: list[dict]) -> dict | None:
    if not is_session_live(events):
        return None
    last_spawn = None
    for event in reversed(events):
        if event.get("type") == "agent.spawn":
            last_spawn = event
            break
    if not last_spawn:
        return None
    return {
        "subagent": last_spawn.get("subagent_type"),
        "description": last_spawn.get("description"),
        "ts": last_spawn.get("ts"),
    }


def subagent_to_step(schema: dict, subagent: str | None) -> str | None:
    if not subagent:
        return None
    for node in schema["nodes"]:
        if node.get("subagent") == subagent:
            return node["id"]
    return None


def _layout_vertical_chain(
    nodes: list[dict],
    *,
    center_x: float = 340,
    start_y: float = 70,
    step_y: float = 105,
) -> list[dict]:
    """Top-to-bottom main column (calibration and simple flows)."""
    order = [n["id"] for n in nodes if n.get("kind") in ("orchestrator", "step", "terminal", "meta")]
    positions: dict[str, tuple[float, float]] = {}
    y = start_y
    for node_id in order:
        positions[node_id] = (center_x, y)
        y += step_y
    return _apply_positions(nodes, positions)


def _layout_spec_vertical(nodes: list[dict]) -> list[dict]:
    """Top-to-bottom spec pipeline: main spine, side branches, routing hub on the left."""
    center_x = 440.0
    left_x = 150.0
    routing_x = 40.0
    right_x = 740.0
    step_y = 112.0
    main_chain = [
        "spec-orchestrator",
        "find-context",
        "write-feature",
        "check-feature",
        "check-feature-code",
        "done",
    ]
    positions: dict[str, tuple[float, float]] = {}
    y = 64.0
    for node_id in main_chain:
        positions[node_id] = (center_x, y)
        y += step_y

    cf_y = positions["check-feature"][1]
    cc_y = positions["check-feature-code"][1]
    wf_y = positions["write-feature"][1]
    orch_y = positions["spec-orchestrator"][1]

    positions["resolve-gaps"] = (left_x, cf_y)
    positions["resolve-code-alignment"] = (left_x, cc_y)
    positions["challenge-feature"] = (right_x, cf_y - 50)
    positions["resolve-challenges"] = (right_x, cf_y + 50)
    positions["archive-session"] = (right_x, orch_y + 18)
    positions["analyze-routing"] = (routing_x, (wf_y + cf_y) / 2)

    return _apply_positions(nodes, positions)


def _apply_positions(nodes: list[dict], positions: dict[str, tuple[float, float]]) -> list[dict]:
    out = []
    fallback_y = 70
    for node in nodes:
        copy = dict(node)
        px, py = positions.get(node["id"], (80, fallback_y))
        copy["position"] = {"x": px, "y": py}
        fallback_y += 40
        out.append(copy)
    return out


def layout_nodes(nodes: list[dict], pipeline_id: str) -> list[dict]:
    """Assign preset x/y for cytoscape (top-to-bottom)."""
    if pipeline_id == "calibration":
        return _layout_vertical_chain(nodes)
    return _layout_spec_vertical(nodes)


def apply_history(schema: dict, history: list[dict]) -> tuple[dict[str, str], list[dict]]:
    node_states = {n["id"]: STATE_PENDING for n in schema["nodes"]}
    orch = schema.get("orchestrator")
    if orch:
        node_states[orch] = STATE_OK

    traversed_edges: list[dict] = []
    step_ids = {n["id"] for n in schema["nodes"]}
    prev_step: str | None = orch

    ordered = sorted(history, key=history_sort_key)
    for row in ordered:
        step = row.get("step") or ""
        result = row.get("result") or "ok"
        if step not in step_ids:
            continue

        if result == "fail":
            node_states[step] = STATE_FAIL
        elif result == "retry":
            node_states[step] = STATE_RETRY
        else:
            node_states[step] = STATE_OK

        if prev_step and prev_step in step_ids:
            edge = _find_edge(schema, prev_step, step)
            traversed_edges.append(
                {
                    "from": prev_step,
                    "to": step,
                    "result": result,
                    "ts": row.get("ts"),
                    "edge_id": edge["id"] if edge else None,
                }
            )
        prev_step = step

    return node_states, traversed_edges


def history_closed_in_run_log(history: list[dict]) -> list[dict]:
    """Rows that SubagentStop recorded (run-log or spawn paired with run-log)."""
    return [r for r in history if (r.get("source") or "run-log") != "events"]


def latest_run_log_result(history: list[dict], step: str) -> str | None:
    """Latest run-log result for step, or None if never closed in run-log."""
    latest: dict | None = None
    latest_ts = None
    for row in history:
        if row.get("step") != step:
            continue
        if (row.get("source") or "run-log") == "events":
            continue
        row_ts = parse_iso_ts(row.get("ts"))
        if latest is None or (row_ts and latest_ts and row_ts >= latest_ts):
            latest = row
            latest_ts = row_ts
    if not latest:
        return None
    return latest.get("result") or STATE_OK


def step_closed_ok_in_run_log(history: list[dict], step: str) -> bool:
    result = latest_run_log_result(history, step)
    return result is not None and result not in (STATE_FAIL, STATE_RETRY)


LOG_SPINE = (
    "find-context",
    "write-feature",
    "check-feature",
    "check-feature-code",
)


def log_spine_next_step(log_history: list[dict]) -> str | None:
    """Next gate step required by run-log (main column before branches)."""
    for step in LOG_SPINE:
        result = latest_run_log_result(log_history, step)
        if result is None or result in (STATE_FAIL, STATE_RETRY):
            return step
    return None


def resolve_display_next(
    log_history: list[dict],
    dispatch_snapshot: dict | None,
    pipeline_id: str = DEFAULT_PIPELINE_ID,
) -> tuple[str, str, str]:
    """Viewer next step: run-log spine first, then dispatch for branches."""
    spine = log_spine_next_step(log_history)
    dispatch = dispatch_snapshot or {}
    if spine:
        return spine, subagent_for_step(spine, pipeline_id), "run-log"
    step = dispatch.get("next_step") or ""
    sub = dispatch.get("next_subagent") or ""
    return step, sub, "dispatch"


def build_timeline(history: list[dict]) -> list[dict]:
    """Chronological passes with per-step pass number (1st, 2nd, … invocation)."""
    step_pass: dict[str, int] = {}
    timeline: list[dict] = []
    for index, row in enumerate(sorted(history, key=history_sort_key), start=1):
        step = row.get("step") or ""
        if step:
            step_pass[step] = step_pass.get(step, 0) + 1
            pass_no = step_pass[step]
        else:
            pass_no = 0
        timeline.append(
            {
                **row,
                "seq": index,
                "pass": pass_no,
            }
        )
    return timeline


def mark_superseded_passes(timeline: list[dict]) -> None:
    """Earlier fail/retry on the same step superseded by a later ok pass (hook false fail)."""
    by_step: dict[str, list[dict]] = {}
    for row in timeline:
        step = row.get("step") or ""
        if step:
            by_step.setdefault(step, []).append(row)

    for rows in by_step.values():
        if len(rows) < 2:
            continue
        rows.sort(key=lambda r: (r.get("seq") or 0, history_sort_key(r)))
        latest = rows[-1]
        latest_ok = (latest.get("result") or STATE_OK) not in (STATE_FAIL, STATE_RETRY)
        if not latest_ok:
            continue
        for row in rows[:-1]:
            if (row.get("result") or STATE_OK) in (STATE_FAIL, STATE_RETRY):
                if row.get("display_state") != STATE_STALE:
                    row["display_state"] = STATE_STALE
                    row["superseded_by"] = latest.get("seq")


def apply_restart_state(
    marker: dict | None,
    *,
    node_states: dict[str, str],
    timeline: list[dict],
    terminal_id: str,
    pipeline_id: str = DEFAULT_PIPELINE_ID,
) -> dict | None:
    """Mark rolled-back steps as redo on graph; old telemetry passes as stale."""
    if not marker:
        for row in timeline:
            row["display_state"] = row.get("result") or STATE_OK
        return None

    from_step = marker.get("from_step") or ""
    redo_steps = set(redo_steps_from(from_step, pipeline_id))
    step_order = pipeline_step_order(pipeline_id)
    if not redo_steps:
        for row in timeline:
            row["display_state"] = row.get("result") or STATE_OK
        return None

    marker_ts = parse_iso_ts(marker.get("created_at"))
    completed_after: set[str] = set()
    if marker_ts:
        for row in timeline:
            step = row.get("step") or ""
            ts = parse_iso_ts(row.get("ts"))
            result = row.get("result") or STATE_OK
            if (
                step in redo_steps
                and ts
                and ts >= marker_ts
                and result not in (STATE_FAIL, STATE_RETRY)
            ):
                completed_after.add(step)

    for row in timeline:
        step = row.get("step") or ""
        ts = parse_iso_ts(row.get("ts"))
        base = row.get("result") or STATE_OK
        if step not in redo_steps or not marker_ts:
            row["display_state"] = base
        elif ts and ts >= marker_ts:
            row["display_state"] = base
        else:
            row["display_state"] = STATE_STALE

    if marker_ts:
        post_marker: dict[str, list[dict]] = {}
        for row in timeline:
            step = row.get("step") or ""
            ts = parse_iso_ts(row.get("ts"))
            if step in redo_steps and ts and ts >= marker_ts:
                post_marker.setdefault(step, []).append(row)
        for rows in post_marker.values():
            rows.sort(key=lambda r: r.get("ts") or "")
            latest = rows[-1]
            latest_ok = (latest.get("result") or STATE_OK) not in (STATE_FAIL, STATE_RETRY)
            if latest_ok and len(rows) > 1:
                for row in rows[:-1]:
                    row["display_state"] = STATE_STALE

    pending_redo = redo_steps - completed_after
    for step in redo_steps:
        if step not in node_states:
            continue
        if node_states[step] in (STATE_ACTIVE, STATE_FAIL, STATE_RETRY):
            continue
        if step in completed_after:
            continue
        node_states[step] = STATE_REDO

    if terminal_id in node_states and pending_redo:
        if node_states[terminal_id] in (STATE_OK, STATE_SKIPPED):
            node_states[terminal_id] = STATE_PENDING

    cli_commands = marker.get("cli_commands")
    if not isinstance(cli_commands, dict):
        cli_commands = build_cli_commands(
            marker.get("slug") or "",
            marker.get("next_step") or from_step,
            subagent=marker.get("next_subagent") or "",
        )
    cli_block = marker.get("cli_block") or format_cli_block(cli_commands)

    return {
        "active": True,
        "from_step": from_step,
        "from_seq": marker.get("from_seq"),
        "created_at": marker.get("created_at"),
        "next_command": marker.get("next_command"),
        "next_subagent": marker.get("next_subagent"),
        "cli_commands": cli_commands,
        "cli_block": cli_block,
        "redo_steps": sorted(redo_steps, key=lambda s: step_order.get(s, 999)),
        "completed_after_restart": sorted(completed_after, key=lambda s: step_order.get(s, 999)),
        "pending_redo": sorted(pending_redo, key=lambda s: step_order.get(s, 999)),
    }


def tag_timeline_divergences(timeline: list[dict], items: list[dict]) -> None:
    by_ts: dict[str, list[str]] = {}
    for item in items:
        ts = item.get("ts")
        if not ts:
            continue
        by_ts.setdefault(ts, []).append(item.get("kind") or "issue")
    for row in timeline:
        if row.get("display_state") == "stale":
            row["divergence_kinds"] = []
        else:
            row["divergence_kinds"] = by_ts.get(row.get("ts") or "", [])


MERGE_SPAWN_WINDOW_SEC = 600


def _match_spawn_run_log(
    spawn: dict,
    run_log: list[dict],
    *,
    used: set[int],
) -> int | None:
    """Nearest run-log row for the same step within MERGE_SPAWN_WINDOW_SEC."""
    spawn_ts = parse_iso_ts(spawn.get("ts"))
    step = spawn.get("step")
    if not step:
        return None
    best_idx: int | None = None
    best_delta: float | None = None
    for index, row in enumerate(run_log):
        if index in used or row.get("step") != step:
            continue
        log_ts = parse_iso_ts(row.get("ts"))
        if spawn_ts and log_ts:
            delta = abs((log_ts - spawn_ts).total_seconds())
            if delta > MERGE_SPAWN_WINDOW_SEC:
                continue
        elif spawn_ts or log_ts:
            continue
        else:
            delta = 0.0
        if best_delta is None or delta < best_delta:
            best_idx = index
            best_delta = delta
    return best_idx


def spawn_superseded_by_run_log(
    history: list[dict],
    step: str,
    spawn_ts: str | None,
) -> bool:
    """Run-log already closed this spawn (SubagentStop logged ok after agent.spawn)."""
    spawn_dt = parse_iso_ts(spawn_ts)
    latest: dict | None = None
    latest_ts: datetime | None = None
    for row in history:
        if row.get("step") != step:
            continue
        if (row.get("source") or "") == "events":
            continue
        row_ts = parse_iso_ts(row.get("ts"))
        if row_ts is None:
            continue
        if latest_ts is None or row_ts > latest_ts:
            latest_ts = row_ts
            latest = row
    if not latest:
        return False
    result = latest.get("result") or STATE_OK
    if result in (STATE_FAIL, STATE_RETRY):
        return False
    if spawn_dt and latest_ts and latest_ts < spawn_dt:
        return False
    return True


def merge_history(run_log: list[dict], spawn_rows: list[dict]) -> list[dict]:
    """Chronological passes: pair agent.spawn with run-log (different timestamps)."""
    if not spawn_rows:
        return [{**r, "source": "run-log"} for r in run_log]
    if not run_log:
        return [{**r, "source": "events"} for r in spawn_rows]

    used_log: set[int] = set()
    merged: list[dict] = []
    for spawn in spawn_rows:
        match_idx = _match_spawn_run_log(spawn, run_log, used=used_log)
        if match_idx is None:
            merged.append({**spawn, "source": "events"})
            continue
        used_log.add(match_idx)
        log_row = run_log[match_idx]
        note = log_row.get("note") or spawn.get("note")
        merged.append(
            {
                **log_row,
                "source": "merged",
                "spawn_ts": spawn.get("ts"),
                "note": note,
            }
        )

    for index, row in enumerate(run_log):
        if index not in used_log:
            merged.append({**row, "source": "run-log"})

    sort_history_by_ts(merged)
    return merged


def _find_edge(schema: dict, src: str, dst: str) -> dict | None:
    for edge in schema.get("edges", []):
        if edge.get("from") == src and edge.get("to") == dst:
            return edge
    for edge in schema.get("edges", []):
        if edge.get("from") == src:
            return edge
    return None


def build_graph(
    root: Path,
    slug: str,
    *,
    run_id: str | None = "auto",
    pipeline: str = "auto",
) -> dict:
    schema_root = load_schema()
    manifest = load_manifest(root, slug)
    rid = resolve_viewer_run_id(root, slug, run_id)
    merged_runs = aggregate_run_history(run_id)

    schema_probe = read_jsonl(run_log_path(root, slug, rid))
    if merged_runs:
        _, probe_log, _, _, _, included_runs = load_aggregate_run_bundle(
            root, slug, schema_root["pipelines"]["spec"], through_run_id=rid
        )
        if included_runs:
            schema_probe = probe_log
    pipe_name = detect_pipeline(schema_probe, pipeline)
    schema = schema_root["pipelines"][pipe_name]

    spawn_rows: list[dict] = []
    spawn_event_count = 0
    agent_run_ids: list[str] = [rid]
    if pipe_name == "calibration":
        run_log = read_jsonl(run_log_path(root, slug, rid))
        events = read_jsonl(events_path(root, slug, rid))
        reached_steps, spawn_rows = collect_spawn_steps(events, schema)
        spawn_event_count = len(spawn_rows)
        live = is_session_live(events)
    elif merged_runs:
        history, run_log, events, reached_steps, spawn_event_count, agent_run_ids = (
            load_aggregate_run_bundle(root, slug, schema, through_run_id=rid)
        )
        live_events = read_jsonl(events_path(root, slug, rid))
        live = is_session_live(live_events)
    else:
        history, run_log, events, reached_steps, spawn_rows = load_single_run_bundle(
            root, slug, rid, schema
        )
        spawn_event_count = len(spawn_rows)
        live = is_session_live(events)

    cal_run_id: str | None = None
    if pipe_name == "calibration":
        cal_run_id = resolve_viewer_calibration_run_id(root, slug)
        run_log_cal = [r for r in run_log if (r.get("step") or "") in CALIBRATION_STEPS]
        artifact_rows = (
            build_calibration_artifact_history(root, slug, cal_run_id) if cal_run_id else []
        )
        history = merge_calibration_history(run_log_cal, spawn_rows, artifact_rows)
    log_history = history_closed_in_run_log(history)
    node_states, traversed = apply_history(schema, log_history)
    nodes = layout_nodes([dict(n) for n in schema["nodes"]], pipe_name)

    edge_states: dict[str, str] = {}
    for item in traversed:
        eid = item.get("edge_id")
        if eid:
            res = item.get("result") or "ok"
            edge_states[eid] = STATE_FAIL if res == "fail" else STATE_RETRY if res == "retry" else STATE_OK

    edges = []
    for edge in schema.get("edges", []):
        copy = dict(edge)
        eid = edge["id"]
        copy["state"] = edge_states.get(eid, STATE_PENDING)
        copy["color"] = RESULT_COLORS.get(copy["state"], RESULT_COLORS[STATE_PENDING])
        copy["traversed"] = eid in edge_states
        edges.append(copy)

    current: dict | None = None
    dispatch_snapshot: dict | None = None
    dispatch_next_step = ""
    task_for_slug: dict | None = None
    display_next_step = ""
    display_next_subagent = ""
    display_next_source = ""
    if dispatch_supported(pipe_name):
        dispatch_snapshot = build_dispatch(root, slug, pipeline_id=pipe_name)
        dispatch_next_step = dispatch_snapshot.get("next_step") or ""
        task_for_slug = load_active_task_for_slug(root, slug)
        display_next_step, display_next_subagent, display_next_source = resolve_display_next(
            log_history,
            dispatch_snapshot,
            pipe_name,
        )

    terminal_id = "done" if pipe_name == "spec" else "cal-done"
    if (
        pipe_name == "spec"
        and not live
        and node_states.get("check-feature-code") == STATE_OK
        and terminal_id in node_states
    ):
        node_states[terminal_id] = STATE_OK

    if pipe_name == "spec" and not live:
        branch_optional = {
            "resolve-gaps",
            "challenge-feature",
            "resolve-challenges",
            "resolve-code-alignment",
        }
        meta_optional = {"archive-session"}
        keep_pending = {display_next_step, dispatch_next_step}
        for step in branch_optional | meta_optional:
            if step in keep_pending:
                continue
            if step in node_states and node_states[step] == STATE_PENDING and step not in reached_steps:
                node_states[step] = STATE_SKIPPED

    timeline = build_timeline(history)
    feature_verdict = ""
    dispatch_ready = False
    if pipe_name == "spec":
        if clear_restart_marker_if_ready(root, slug):
            restart_info = None
            marker = None
        else:
            marker = load_restart_marker(root, slug, "spec")
            restart_info = apply_restart_state(
                marker,
                node_states=node_states,
                timeline=timeline,
                terminal_id=terminal_id,
                pipeline_id=pipe_name,
            )
        fs = build_status(root, slug)
        feature_verdict = fs.verdict or ""
        dispatch_ready = bool(
            (dispatch_snapshot or {}).get("ready") or fs.ready
        )
        if dispatch_ready:
            if terminal_id in node_states:
                node_states[terminal_id] = STATE_OK
            if (
                fs.critical_major_mismatch == 0
                and node_states.get("check-feature-code") == STATE_OK
                and node_states.get("resolve-code-alignment")
                in (STATE_REDO, STATE_PENDING)
            ):
                node_states["resolve-code-alignment"] = STATE_SKIPPED
    else:
        marker = load_restart_marker(root, slug, pipe_name)
        restart_info = apply_restart_state(
            marker,
            node_states=node_states,
            timeline=timeline,
            terminal_id=terminal_id,
            pipeline_id=pipe_name,
        )

    mark_superseded_passes(timeline)

    active = infer_active_subagent(events) if live else None
    active_step: str | None = None
    if active:
        active_step = subagent_to_step(schema, active.get("subagent"))
        if pipe_name == "calibration" and not active_step:
            active = None
        elif active_step and spawn_superseded_by_run_log(
            history, active_step, active.get("ts")
        ):
            active = None

    running_step: str | None = None
    if active and active_step and active_step in node_states:
        running_step = active_step
        current = {
            "node_id": active_step,
            "step": active_step,
            "subagent": active.get("subagent"),
            "status": "running",
            "since": active.get("ts"),
            "note": active.get("description"),
        }
    if running_step:
        node_states[running_step] = STATE_ACTIVE
        for node in nodes:
            if node["id"] == running_step:
                node["state"] = STATE_ACTIVE
                node["color"] = RESULT_COLORS[STATE_ACTIVE]
    else:
        last_log = log_history[-1] if log_history else None
        last_result = (last_log.get("result") if last_log else None) or STATE_OK
        next_step = display_next_step if pipe_name == "spec" else ""
        next_subagent = display_next_subagent if pipe_name == "spec" else ""
        next_note = (
            "Следующий шаг по run-log"
            if display_next_source == "run-log"
            else "Следующий шаг по dispatch (ветка)"
        )

        if (
            last_log
            and last_result in (STATE_FAIL, STATE_RETRY)
            and not dispatch_ready
        ):
            current = {
                "node_id": last_log.get("step"),
                "step": last_log.get("step"),
                "subagent": last_log.get("subagent"),
                "status": "idle",
                "result": last_result,
                "ts": last_log.get("ts"),
                "note": last_log.get("note")
                or "Subagent завершился с fail/retry — повторите шаг",
            }
        elif (
            next_step
            and next_step in node_states
            and node_states.get(next_step) == STATE_PENDING
            and not dispatch_ready
        ):
            node_states[next_step] = STATE_NEXT
            current = {
                "node_id": next_step,
                "step": next_step,
                "subagent": next_subagent,
                "status": "next",
                "note": next_note,
            }
        elif last_log:
            note = last_log.get("note") or ""
            if not note:
                if live:
                    note = "Шаг завершён в run-log — оркестратор готов к dispatch"
                else:
                    note = "Session idle — последняя запись run-log"
            current = {
                "node_id": last_log.get("step"),
                "step": last_log.get("step"),
                "subagent": last_log.get("subagent"),
                "status": "idle",
                "result": last_result,
                "ts": last_log.get("ts"),
                "note": note,
            }

    for node in nodes:
        node["state"] = node_states.get(node["id"], STATE_PENDING)
        node["color"] = RESULT_COLORS.get(node["state"], RESULT_COLORS[STATE_PENDING])
        if (
            pipe_name == "spec"
            and dispatch_ready
            and node["id"] == terminal_id
            and feature_verdict
        ):
            node["label"] = feature_verdict

    attach_node_details(
        nodes,
        run_log=run_log,
        events=events,
        root=root,
        slug=slug,
        agent_run_id=rid,
        pipeline=pipe_name,
    )

    stats = {}
    mp = metrics_path(root, slug, rid)
    metrics: dict = {}
    if mp.is_file():
        metrics = json.loads(mp.read_text(encoding="utf-8"))
        stats = {
            "events": metrics.get("counts", {}).get("events"),
            "anomalies": len(metrics.get("anomalies") or []),
            "cli": metrics.get("cli"),
            "session_id": metrics.get("session_id"),
            "time_range": metrics.get("time_range"),
        }
    stats["session_live"] = live

    divergence = analyze_divergence(
        root=root,
        slug=slug,
        schema=schema,
        history=log_history,
        current=current,
        live=live,
        pipeline=pipe_name,
        active_task=task_for_slug,
        log_next_step=display_next_step if display_next_source == "run-log" else "",
    )
    divergence["items"] = filter_divergence_for_restart(
        divergence.get("items") or [],
        timeline=timeline,
        restart_info=restart_info,
    )
    finalize_divergence(divergence)
    tag_timeline_divergences(timeline, divergence.get("items") or [])
    visit_counts = Counter(row.get("step") for row in timeline if row.get("step"))
    for node in nodes:
        node["visit_count"] = visit_counts.get(node["id"], 0)

    last_active = None
    for row in reversed(timeline):
        if row.get("display_state") != STATE_STALE:
            last_active = row
            break
    if last_active is None and timeline:
        last_active = timeline[-1]

    restart_marker_file = feature_dir(root, slug) / ".pipeline-restart.json"
    watch_paths = {
        "run_log": str(run_log_path(root, slug, rid)),
        "events": str(events_path(root, slug, rid)),
        "metrics": str(mp),
    }
    if merged_runs and len(agent_run_ids) > 1:
        watch_paths["run_logs"] = {
            arid: str(run_log_path(root, slug, arid)) for arid in agent_run_ids
        }
        watch_paths["events_all"] = {
            arid: str(events_path(root, slug, arid)) for arid in agent_run_ids
        }
    active_task_file = feature_active_task_path(root, slug)
    if active_task_file.is_file():
        watch_paths["active_task"] = str(active_task_file)
    if restart_marker_file.is_file():
        watch_paths["restart_marker"] = str(restart_marker_file)
    validation_file = agent_logs_dir(root, slug) / "validation.json"
    if validation_file.is_file():
        watch_paths["validation"] = str(validation_file)
    from agent_logs import slug_subagent_passes_path

    slug_passes = slug_subagent_passes_path(root, slug)
    if slug_passes.is_file():
        watch_paths["subagent_passes"] = str(slug_passes)
    if cal_run_id:
        cal_dir = calibration_run_dir(root, slug, cal_run_id)
        watch_paths["calibration_run"] = str(cal_dir)
        score = scorecard_path(root, slug, cal_run_id)
        if score.is_file():
            watch_paths["scorecard"] = str(score)
    dispatch_fingerprint = divergence.get("fingerprint") or {}

    validation: dict | None = None
    timings: dict | None = None
    if pipe_name == "spec":
        try:
            from pipeline_validate import validate_slug

            validation = validate_slug(root, slug, pipeline=pipe_name).to_dict()
        except Exception as exc:  # noqa: BLE001 — viewer must not fail on validate
            validation = {"ok": False, "error": str(exc), "advice": []}
        try:
            from pipeline_timings import build_step_timings

            timings = build_step_timings(
                schema=schema,
                run_log=run_log,
                events=events,
                root=root,
                slug=slug,
                cli=manifest.get("cli") or "qwen",
                agent_run_ids=agent_run_ids,
            )
        except Exception as exc:  # noqa: BLE001
            timings = {"error": str(exc), "steps": [], "passes": [], "notes": []}

    return {
        "slug": slug,
        "run_id": rid,
        "agent_run_ids": agent_run_ids,
        "history_aggregate": merged_runs and pipe_name == "spec",
        "calibration_run_id": cal_run_id,
        "pipeline": pipe_name,
        "pipeline_label": schema.get("label"),
        "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "nodes": nodes,
        "edges": edges,
        "history": history,
        "timeline": timeline,
        "run_log_tail": (
            [r for r in run_log[-20:] if (r.get("step") or "") in CALIBRATION_STEPS]
            if pipe_name == "calibration"
            else run_log[-20:]
        ),
        "last_pass": last_active,
        "visit_counts": dict(visit_counts),
        "history_sources": {
            "run_log_lines": len(run_log),
            "spawn_events": spawn_event_count,
            "agent_runs": len(agent_run_ids),
        },
        "traversed_edges": traversed,
        "current": current,
        "active_task": task_for_slug,
        "stats": stats,
        "watch_paths": watch_paths,
        "manifest": {
            "cli": manifest.get("cli"),
            "last_ingest": manifest.get("last_ingest"),
        },
        "dispatch": dispatch_snapshot or divergence.get("dispatch"),
        "dispatch_fingerprint": dispatch_fingerprint,
        "outcome": (
            {"ready": dispatch_ready, "verdict": feature_verdict or "PASS"}
            if pipe_name == "spec"
            else None
        ),
        "divergence": {
            "summary": divergence.get("summary"),
            "items": divergence.get("items"),
            "by_step": divergence.get("by_step"),
            "kinds": divergence.get("kinds"),
            "fingerprint": dispatch_fingerprint,
        },
        "restart": restart_info,
        "validation": validation,
        "timings": timings,
    }


def main() -> None:
    args = parse_args()
    root = (args.workspace or workspace_root()).resolve()
    graph = build_graph(root, args.slug, run_id=args.run_id, pipeline=args.pipeline)
    indent = 2 if args.pretty else None
    print(json.dumps(graph, ensure_ascii=False, indent=indent))


if __name__ == "__main__":
    main()

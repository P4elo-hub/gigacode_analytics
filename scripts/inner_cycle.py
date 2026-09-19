#!/usr/bin/env python3
"""Mini-graph inside one pipeline cell: task / assemble / done.

A `cycle:` node is a frontend-drawable composite block: inner steps
(`calls` or a runtime adapter), assemble without routing, then the same
exit as any graph node (`close: on_done` — engine default): stamp
`position` on this cell and drop the active-task marker so outer dispatch
can follow the compiled edges.

The outer graph stays on that node until close. No analyze-routing between
inner calls. Queue is a list of {agent, param, artifact}. Default assemble
is concat.
"""

from __future__ import annotations

from pathlib import Path

from pipeline_common import write_cycle_config
from pipeline_pack import DEFAULT_PIPELINE_ID

ACTION_TASK = "task"
ACTION_ASSEMBLE = "assemble"
ACTION_DONE = "done"
CLOSE_ON_DONE = "on_done"
CYCLE_MODES = frozenset({"inner_cycle", "write_feature_cycle"})
DEFAULT_ITEM_FILE = "{slug}.part-{param}.md"
DEFAULT_OUT = "{slug}.md"
DEFAULT_FOLDER = "Feature-writing/{slug}"


def is_cycle_mode(mode: str | None) -> bool:
    return (mode or "") in CYCLE_MODES


def cycle_config_for_step(pipeline_id: str, step: str) -> dict:
    """Cycle block from the graph node, else registry write_feature_cycle."""
    if not step:
        return {}
    try:
        from pipeline_runtime import load_pipeline_schema

        schema = load_pipeline_schema(pipeline_id)
    except (FileNotFoundError, KeyError, ValueError):
        schema = {}
    for node in schema.get("nodes") or []:
        if not isinstance(node, dict) or node.get("id") != step:
            continue
        raw = node.get("cycle")
        if not isinstance(raw, dict):
            break
        cfg = dict(raw)
        cfg.setdefault("step", step)
        cfg.setdefault("subagent", node.get("subagent") or "")
        cfg.setdefault("persistent", True)
        cfg.setdefault("close", CLOSE_ON_DONE)
        return cfg
    fallback = write_cycle_config(pipeline_id)
    if fallback.get("step") == step:
        return dict(fallback)
    return {}


def resolve_cycle_folder(root: Path, slug: str, cycle: dict) -> Path:
    template = str(cycle.get("folder") or DEFAULT_FOLDER)
    return (root / template.replace("{slug}", slug)).resolve()


def resolve_cycle_out(folder: Path, slug: str, cycle: dict) -> Path:
    template = str(cycle.get("out") or DEFAULT_OUT)
    return folder / template.replace("{slug}", slug)


def item_glob(slug: str, cycle: dict) -> str:
    template = str(cycle.get("item_file") or DEFAULT_ITEM_FILE)
    return template.replace("{slug}", slug).replace("{param}", "*")


def expand_calls(slug: str, cycle: dict) -> list[dict]:
    template = str(cycle.get("item_file") or DEFAULT_ITEM_FILE)
    default_agent = str(cycle.get("subagent") or "")
    expanded: list[dict] = []
    for raw in cycle.get("calls") or []:
        if not isinstance(raw, dict):
            continue
        param = str(raw.get("param") or "").strip()
        if not param:
            continue
        agent = str(raw.get("agent") or default_agent)
        artifact = template.replace("{slug}", slug).replace("{param}", param)
        item = dict(raw)
        item["agent"] = agent
        item["param"] = param
        item["artifact"] = artifact
        expanded.append(item)
    return expanded


def next_inner_cycle(
    slug: str,
    folder: Path,
    *,
    calls: list[dict],
    out: Path,
    assemble: str = "concat",
) -> dict:
    """Next action for a composite cell: missing artifact → task; all present → assemble."""
    existing = [
        folder / str(item.get("artifact") or "")
        for item in calls
        if (folder / str(item.get("artifact") or "")).is_file()
    ]
    if not existing and out.is_file():
        return {
            "action": ACTION_DONE,
            "open": False,
            "slug": slug,
            "out": str(out),
            "assemble": assemble,
        }

    missing = [
        item
        for item in calls
        if not (folder / str(item.get("artifact") or "")).is_file()
    ]
    if missing:
        call = missing[0]
        payload = {
            "action": ACTION_TASK,
            "open": True,
            "slug": slug,
            "subagent": call.get("agent"),
            "param": call.get("param"),
            "block_id": call.get("param"),
            "part_file": str(folder / str(call.get("artifact") or "")),
            "remaining": [item.get("param") for item in missing],
            "out": str(out),
            "part_dir": str(folder),
            "assemble": assemble,
        }
        for key in ("skills", "check"):
            if key in call:
                payload[key] = call[key]
        return payload

    return {
        "action": ACTION_ASSEMBLE,
        "open": True,
        "slug": slug,
        "subagent": None,
        "out": str(out),
        "part_dir": str(folder),
        "assemble": assemble,
        "calls": calls,
    }


def apply_concat(decision: dict) -> dict:
    folder = Path(str(decision["part_dir"]))
    out = Path(str(decision["out"]))
    calls = list(decision.get("calls") or [])
    missing = [
        str(item.get("artifact") or "")
        for item in calls
        if not (folder / str(item.get("artifact") or "")).is_file()
    ]
    chunks: list[str] = []
    for item in calls:
        path = folder / str(item.get("artifact") or "")
        if path.is_file():
            chunks.append(path.read_text(encoding="utf-8").strip())
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n\n".join(chunks) + ("\n" if chunks else ""), encoding="utf-8")
    deleted: list[str] = []
    if not missing:
        for item in calls:
            path = folder / str(item.get("artifact") or "")
            if path.is_file():
                path.unlink()
                deleted.append(str(path))
    return {"written": str(out), "missing_parts": missing, "deleted": deleted}


def cycle_closes_on_done(cycle: dict | None) -> bool:
    """Exit condition for a composite cell. Missing `close` means on_done."""
    return str((cycle or {}).get("close") or CLOSE_ON_DONE) == CLOSE_ON_DONE


def close_cycle_cell(
    root: Path,
    slug: str,
    step: str,
    *,
    pipeline_id: str = DEFAULT_PIPELINE_ID,
    result: str = "ok",
) -> dict:
    """Finish the outer graph node: record_position + clear_active_task."""
    from pipeline_active_task import clear_active_task
    from pipeline_position import record_position

    recorded = record_position(root, slug, step, result)
    clear_active_task(root, slug)
    return {
        "closed": True,
        "step": step,
        "result": result,
        "position_recorded": bool(recorded),
        "pipeline_id": pipeline_id,
    }


def close_finished_cycle_marker(
    root: Path,
    slug: str,
    *,
    pipeline_id: str = DEFAULT_PIPELINE_ID,
    active: dict | None = None,
) -> dict | None:
    """If a persistent cycle marker is still up and inner steps are done, close the cell.

    Assemble is not a subagent, so SubagentStop may never run. Dispatch also
    skips the cycle node once the result file exists — close must not depend
    on orchestrator_mode == write_feature_cycle.
    """
    from pipeline_active_task import load_active_task_for_slug

    marker = active if active is not None else load_active_task_for_slug(root, slug)
    if not marker or not marker.get("persistent"):
        return None
    if str(marker.get("slug") or "") != slug:
        return None
    step = str(marker.get("step") or "")
    cfg = cycle_config_for_step(pipeline_id, step)
    if not cfg or not cycle_closes_on_done(cfg):
        return None
    try:
        cycle_next = next_cycle_at(slug, root=root, pipeline_id=pipeline_id, step=step)
    except Exception:  # noqa: BLE001 — close must not break delegate
        return None
    if cycle_next.get("action") != ACTION_DONE:
        return None
    return close_cycle_cell(root, slug, step, pipeline_id=pipeline_id)


def maybe_close_assembled_cell(decision: dict, applied: dict) -> dict | None:
    """Assemble is not a subagent — close here or the outer node never finishes."""
    if applied.get("missing_parts"):
        return None
    root = decision.get("root")
    slug = decision.get("slug")
    step = decision.get("step")
    if not root or not slug or not step:
        return None
    pipeline_id = str(decision.get("pipeline_id") or DEFAULT_PIPELINE_ID)
    cfg = cycle_config_for_step(pipeline_id, str(step))
    if cfg and not cycle_closes_on_done(cfg):
        return None
    closed = close_cycle_cell(
        Path(str(root)),
        str(slug),
        str(step),
        pipeline_id=pipeline_id,
    )
    applied["cell_closed"] = closed
    return closed


def apply_assemble(decision: dict) -> dict:
    if decision.get("action") != ACTION_ASSEMBLE:
        raise ValueError(f"assemble only when action=assemble, got {decision.get('action')!r}")
    kind = str(decision.get("assemble") or "concat")
    if kind == "write_feature":
        from write_feature_cycle import apply_write_feature_assemble

        applied = apply_write_feature_assemble(decision)
    elif kind != "concat":
        raise ValueError(f"unknown assemble {kind!r}")
    else:
        applied = apply_concat(decision)
    maybe_close_assembled_cell(decision, applied)
    return applied


def cycle_artifacts_open(folder: Path, out: Path, slug: str, cycle: dict, started_at: str | None) -> bool:
    """True until assemble: item files remain, or out is missing/older than the cycle."""
    from pipeline_active_task import parse_active_ts
    from datetime import datetime, timezone

    pattern = item_glob(slug, cycle)
    if list(folder.glob(pattern)):
        return True
    if not out.is_file():
        return True
    started = parse_active_ts(started_at)
    if started is None:
        return True
    mtime = datetime.fromtimestamp(out.stat().st_mtime, tz=timezone.utc)
    return mtime < started


def next_cycle_at(
    slug: str,
    *,
    root: Path,
    pipeline_id: str = DEFAULT_PIPELINE_ID,
    step: str | None = None,
    brief: str = "",
    sections: str | None = None,
    profile: str | None = None,
) -> dict:
    step = step or str(write_cycle_config(pipeline_id).get("step") or "")
    cfg = cycle_config_for_step(pipeline_id, step)
    folder = resolve_cycle_folder(root, slug, cfg)
    out = resolve_cycle_out(folder, slug, cfg)
    calls = expand_calls(slug, cfg)
    extra: dict = {}
    if not calls:
        from write_feature_cycle import calls_from_plan

        calls, extra = calls_from_plan(
            slug, folder, brief=brief, sections=sections, profile=profile, cycle=cfg
        )
    assemble = str(cfg.get("assemble") or extra.get("assemble") or "concat")
    decision = next_inner_cycle(slug, folder, calls=calls, out=out, assemble=assemble)
    if extra:
        decision.update({k: v for k, v in extra.items() if k not in decision or not decision.get(k)})
        if decision.get("action") == ACTION_TASK and extra.get("sections"):
            decision["sections"] = extra["sections"]
            decision["check"] = {
                "mode": "check-part",
                "block_id": decision.get("param"),
                "sections": extra["sections"],
            }
        if decision.get("action") == ACTION_ASSEMBLE:
            decision["sections"] = extra.get("sections")
            decision["brief"] = extra.get("brief") or ""
    decision["root"] = str(root)
    decision["step"] = step
    decision["pipeline_id"] = pipeline_id
    return decision

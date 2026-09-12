"""Shared telemetry: event normalization, metrics, artifact writes."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from agent_logs import (
    anomalies_path,
    events_path,
    load_manifest,
    metrics_path,
    raw_dir,
    run_dir,
    save_manifest,
    utc_now_iso,
)

SKILL_PATH_RE = re.compile(
    r"(?:^|/)(?:\.(?:qwen|gigacode|opencode)/skills/|skills/)([\w-]+)/SKILL\.md",
    re.IGNORECASE,
)
CHECK_PART_RE = re.compile(r"write_feature\.py.*--mode\s+check-part")
SKILL_REPEAT_THRESHOLD = 3
TOOL_SPIKE_THRESHOLD = 80
READ_SPIKE_THRESHOLD = 4


def skill_from_path(path: str | None) -> str | None:
    if not path:
        return None
    match = SKILL_PATH_RE.search(path.replace("\\", "/"))
    if match:
        return match.group(1)
    if path.endswith("/SKILL.md"):
        return Path(path).parent.name
    return None


def summarize_tool_call(name: str, args: dict) -> dict:
    if name in ("read_file", "read", "write_file", "write", "edit"):
        fp = args.get("file_path") or args.get("filePath") or args.get("path") or ""
        skill = skill_from_path(str(fp))
        out = {"path": str(fp)}
        if skill:
            out["skill"] = skill
        return out
    if name == "skill":
        return {"skill": args.get("skill") or args.get("name")}
    if name in ("run_shell_command", "bash"):
        cmd = args.get("command") or args.get("cmd") or ""
        return {"command": str(cmd)[:500]}
    if name in ("agent", "task"):
        return {
            "subagent_type": args.get("subagent_type") or args.get("agent_type"),
            "description": (args.get("description") or "")[:200],
        }
    if name in ("grep_search", "grep"):
        return {"pattern": (args.get("pattern") or args.get("query") or "")[:120]}
    if name == "glob":
        return {"pattern": (args.get("glob_pattern") or args.get("pattern") or "")[:120]}
    return {k: v for k, v in args.items() if isinstance(v, (str, int, float, bool))}


def event_from_tool_call(
    *,
    ts: str,
    session_id: str,
    agent: str,
    is_sidechain: bool,
    tool_name: str,
    args: dict,
) -> dict:
    summary = summarize_tool_call(tool_name, args)
    event_type = "tool.call"
    if tool_name == "skill" or summary.get("skill"):
        event_type = "skill.load"
    elif tool_name in ("agent", "task"):
        event_type = "agent.spawn"
    return {
        "ts": ts,
        "type": event_type,
        "session_id": session_id,
        "agent": agent,
        "is_sidechain": is_sidechain,
        "tool": tool_name,
        **{k: v for k, v in summary.items() if v is not None},
    }


def compute_metrics(
    events: list[dict],
    *,
    slug: str,
    run_id: str,
    session_id: str,
    cli: str,
    subagent_count: int = 0,
) -> dict:
    skill_loads: Counter = Counter()
    skill_by_agent: dict[str, Counter] = defaultdict(Counter)
    tool_calls: Counter = Counter()
    check_part_calls = 0
    agent_spawns: Counter = Counter()

    for event in events:
        etype = event.get("type")
        agent = str(event.get("agent") or "unknown")
        if etype == "skill.load":
            skill = event.get("skill") or event.get("tool")
            if skill:
                skill_loads[skill] += 1
                skill_by_agent[agent][skill] += 1
        elif etype == "tool.call":
            tool = event.get("tool") or "unknown"
            tool_calls[tool] += 1
            cmd = event.get("command") or ""
            if CHECK_PART_RE.search(cmd):
                check_part_calls += 1
        elif etype == "agent.spawn":
            sub = event.get("subagent_type") or "unknown"
            agent_spawns[sub] += 1

    anomalies: list[dict] = []
    for skill, count in skill_loads.items():
        if count >= SKILL_REPEAT_THRESHOLD:
            agents = [
                a for a, ctr in skill_by_agent.items() if ctr.get(skill, 0) >= SKILL_REPEAT_THRESHOLD
            ]
            anomalies.append(
                {
                    "id": f"TEL-SKILL-{skill}",
                    "severity": "warn" if count < 10 else "major",
                    "type": "skill.repeat",
                    "skill": skill,
                    "count": count,
                    "threshold": SKILL_REPEAT_THRESHOLD,
                    "agents": agents,
                    "hint": "Скилл грузится слишком часто — добавьте «read once per block» или сузьте router.",
                }
            )

    for agent, ctr in skill_by_agent.items():
        for skill, count in ctr.items():
            if count >= SKILL_REPEAT_THRESHOLD:
                continue
            if count >= READ_SPIKE_THRESHOLD:
                anomalies.append(
                    {
                        "id": f"TEL-AGENT-{agent}-{skill}",
                        "severity": "info",
                        "type": "skill.repeat.agent",
                        "skill": skill,
                        "agent": agent,
                        "count": count,
                        "threshold": READ_SPIKE_THRESHOLD,
                    }
                )

    for agent, total in Counter(e.get("agent") for e in events if e.get("type") == "tool.call").items():
        if total >= TOOL_SPIKE_THRESHOLD:
            anomalies.append(
                {
                    "id": f"TEL-TOOLS-{agent}",
                    "severity": "warn",
                    "type": "tool.spike",
                    "agent": agent,
                    "count": total,
                    "threshold": TOOL_SPIKE_THRESHOLD,
                    "hint": "Много tool calls — возможен retry loop или scope creep.",
                }
            )

    if check_part_calls >= 2:
        anomalies.append(
            {
                "id": "TEL-CHECK-PART",
                "severity": "warn",
                "type": "check_part.retries",
                "count": check_part_calls,
                "hint": "Несколько check-part — writer не проходит gate с первого раза.",
            }
        )

    started = events[1]["ts"] if len(events) > 1 else None
    ended = events[-1]["ts"] if events else None

    return {
        "slug": slug,
        "run_id": run_id,
        "session_id": session_id,
        "cli": cli,
        "ingested_at": utc_now_iso(),
        "time_range": {"started": started, "ended": ended},
        "counts": {
            "events": len(events),
            "subagent_sessions": subagent_count,
            "skill_loads": dict(skill_loads.most_common()),
            "tool_calls": dict(tool_calls.most_common()),
            "agent_spawns": dict(agent_spawns.most_common()),
            "check_part_calls": check_part_calls,
        },
        "anomalies": anomalies,
    }


def write_anomalies_md(root: Path, slug: str, run_id: str, metrics: dict) -> None:
    lines = [
        f"# Session anomalies — {slug} / {run_id}",
        "",
        f"- session: `{metrics.get('session_id')}`",
        f"- cli: `{metrics.get('cli')}`",
        f"- ingested: {metrics.get('ingested_at')}",
        "",
    ]
    anomalies = metrics.get("anomalies") or []
    if not anomalies:
        lines.append("No anomalies above thresholds.")
    else:
        lines.append("| ID | Severity | Type | Detail |")
        lines.append("|----|----------|------|--------|")
        for item in anomalies:
            detail = item.get("hint") or json.dumps(
                {k: v for k, v in item.items() if k not in ("id", "severity", "type", "hint")},
                ensure_ascii=False,
            )
            lines.append(
                f"| {item.get('id')} | {item.get('severity')} | {item.get('type')} | {detail} |"
            )
    anomalies_path(root, slug, run_id).write_text("\n".join(lines) + "\n", encoding="utf-8")


def finalize_run(
    root: Path,
    slug: str,
    run_id: str,
    events: list[dict],
    metrics: dict,
    *,
    cli: str,
    session_id: str,
) -> dict:
    run_dir(root, slug, run_id).mkdir(parents=True, exist_ok=True)
    events_path(root, slug, run_id).write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in events) + "\n",
        encoding="utf-8",
    )
    metrics_path(root, slug, run_id).write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_anomalies_md(root, slug, run_id, metrics)

    manifest = load_manifest(root, slug)
    manifest["slug"] = slug
    manifest.setdefault("runs", [])
    if run_id not in manifest["runs"]:
        manifest["runs"].append(run_id)
    manifest["current_run"] = run_id
    manifest["cli"] = cli
    manifest["last_session_id"] = session_id
    manifest["last_ingest"] = utc_now_iso()
    save_manifest(root, slug, manifest)
    return metrics

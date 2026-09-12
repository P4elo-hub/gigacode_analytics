"""Build per-step summaries for pipeline viewer (hover / click)."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from agent_logs import agent_logs_dir, metrics_path
from calibration_paths import (
    calibration_manifest_path,
    context_gaps_path,
    delta_analysis_path,
    human_review_path,
    inputs_lock_path,
    proposals_table_path,
    rerun_dir,
    scorecard_path,
)

EXCERPT_MAX = 900
TOOLTIP_MAX = 220

STEP_HINTS: dict[str, str] = {
    "spec-orchestrator": "Дирижёр: делегирует subagents, пишет DECISIONS, вызывает ingest.",
    "find-context": "Discovery → context-doc в Feature-context/.",
    "write-feature": "Блочная spec через spec-writer + write_feature.py.",
    "check-feature": "Ревизия spec vs analytics и context-doc.",
    "resolve-gaps": "Закрытие [GAP-*] через DECISIONS.",
    "challenge-feature": "Adversarial вопросы → challenges.md.",
    "resolve-challenges": "Закрытие CH-* из DECISIONS.",
    "check-feature-code": "Аудит spec vs repositories/.",
    "resolve-code-alignment": "Закрытие alignment gaps.",
    "archive-session": "Ingest CLI → agent-logs/ (events, metrics, anomalies).",
    "done": "Verdict PASS / PASS WITH GAPS.",
    "calibration-orchestrator": "Meta-pipeline после human review.",
    "snapshot-baseline": "Заморозка SPEC → Calibration/baseline/.",
    "capture-review": "Gold + human-review.md (REV-*).",
    "analyze-delta": "Diff baseline vs gold + context gaps.",
    "analyze-telemetry": "Разбор anomalies и skill repeats.",
    "propose-calibration": "PROP-* proposals (skill/process).",
    "apply-calibration": "Патч approved skills.",
    "benchmark-rerun": "Изолированный rerun spec-пайплайна.",
    "cal-done": "Scorecard калибровки.",
}


def _excerpt(path: Path, limit: int = EXCERPT_MAX) -> str | None:
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8", errors="ignore").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "\n\n… (truncated)"


def _short(text: str | None, limit: int = TOOLTIP_MAX) -> str:
    if not text:
        return ""
    one = re.sub(r"\s+", " ", text).strip()
    if len(one) <= limit:
        return one
    return one[: limit - 1] + "…"


def _resolve_calibration_run(root: Path, slug: str) -> str | None:
    manifest_path = calibration_manifest_path(root, slug)
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("current_run"):
            return manifest["current_run"]
        runs = manifest.get("runs") or []
        if runs:
            return runs[-1]
    runs_root = root / "Calibration" / slug / "runs"
    if not runs_root.is_dir():
        return None
    dirs = sorted(p.name for p in runs_root.iterdir() if p.is_dir() and p.name.startswith("run-"))
    return dirs[-1] if dirs else None


def _calibration_artifact(root: Path, slug: str, step_id: str) -> tuple[str | None, str | None]:
    run_id = _resolve_calibration_run(root, slug)
    if not run_id:
        return None, None
    mapping = {
        "snapshot-baseline": inputs_lock_path(root, slug, run_id),
        "capture-review": human_review_path(root, slug, run_id),
        "analyze-delta": delta_analysis_path(root, slug, run_id),
        "propose-calibration": proposals_table_path(root, slug, run_id),
        "cal-done": scorecard_path(root, slug, run_id),
    }
    if step_id == "analyze-delta":
        gaps = context_gaps_path(root, slug, run_id)
        parts = []
        for path in (mapping[step_id], gaps):
            if path.is_file():
                parts.append(f"### {path.name}\n{_excerpt(path, 400)}")
        if parts:
            return "\n\n".join(parts), str(mapping[step_id])
    if step_id == "benchmark-rerun":
        brief = rerun_dir(root, slug, run_id) / "brief.txt"
        if brief.is_file():
            return _excerpt(brief, 400), str(brief)
    path = mapping.get(step_id)
    if path and path.is_file():
        return _excerpt(path), str(path)
    return None, None


def _telemetry_analysis(root: Path, slug: str, agent_run_id: str) -> tuple[str | None, str | None]:
    path = agent_logs_dir(root, slug) / "runs" / agent_run_id / "telemetry-analysis.md"
    if path.is_file():
        return _excerpt(path), str(path)
    return None, None


def _spawn_stats(events: list[dict], subagent: str | None) -> tuple[list[dict], Counter, Counter]:
    spawns: list[dict] = []
    if not subagent:
        return spawns, Counter(), Counter()
    for event in events:
        if event.get("type") == "agent.spawn" and event.get("subagent_type") == subagent:
            spawns.append(
                {
                    "ts": event.get("ts"),
                    "description": event.get("description") or "",
                }
            )
    tools: Counter = Counter()
    skills: Counter = Counter()
    needle = subagent.replace("-", "")
    for event in events:
        agent = str(event.get("agent") or "")
        if subagent not in agent and needle not in agent.replace("-", ""):
            continue
        etype = event.get("type")
        if etype == "tool.call":
            tools[str(event.get("tool") or "unknown")] += 1
        elif etype == "skill.load":
            skills[str(event.get("skill") or "?")] += 1
    return spawns, tools, skills


def build_node_detail(
    *,
    step_id: str,
    subagent: str | None,
    kind: str,
    state: str,
    run_log: list[dict],
    events: list[dict],
    root: Path,
    slug: str,
    agent_run_id: str,
    pipeline: str,
) -> dict:
    hint = STEP_HINTS.get(step_id, step_id)
    log_rows = [r for r in run_log if r.get("step") == step_id]
    spawns, tools, skills = _spawn_stats(events, subagent)

    lines: list[str] = [hint, ""]

    if state == "skipped":
        lines.append("Шаг не выполнялся в этой сессии (ветка не выбрана или meta).")
    elif state == "pending":
        lines.append("Телеметрии по шагу пока нет.")
    else:
        if log_rows:
            lines.append("**run-log:**")
            for row in log_rows[-3:]:
                note = f" — {row['note']}" if row.get("note") else ""
                lines.append(
                    f"- {row.get('ts', '?')}: {row.get('result', 'ok')} "
                    f"(attempt {row.get('attempt', 1)}){note}"
                )
        if spawns:
            lines.append("")
            lines.append("**Запуски subagent:**")
            for sp in spawns[-5:]:
                desc = sp.get("description") or "—"
                lines.append(f"- {sp.get('ts', '?')}: {desc}")
        if skills:
            top = ", ".join(f"{k}×{v}" for k, v in skills.most_common(5))
            lines.append("")
            lines.append(f"**Skills:** {top}")
        if tools:
            top = ", ".join(f"{k}×{v}" for k, v in tools.most_common(5))
            lines.append(f"**Tools:** {top}")

    artifact_path: str | None = None
    artifact_text: str | None = None

    if pipeline == "calibration":
        artifact_text, artifact_path = _calibration_artifact(root, slug, step_id)
    if step_id == "analyze-telemetry":
        artifact_text, artifact_path = _telemetry_analysis(root, slug, agent_run_id)
    if step_id == "archive-session":
        mp = metrics_path(root, slug, agent_run_id)
        if mp.is_file():
            artifact_path = str(mp)
            metrics = json.loads(mp.read_text(encoding="utf-8"))
            anomaly_n = len(metrics.get("anomalies") or [])
            lines.append("")
            lines.append(
                f"**Ingest:** {metrics.get('ingested_at', '?')}, "
                f"events={metrics.get('counts', {}).get('events', '?')}, "
                f"anomalies={anomaly_n}"
            )

    if artifact_text:
        lines.append("")
        lines.append(f"**Артефакт** (`{Path(artifact_path).name if artifact_path else '?'}`):")
        lines.append(artifact_text)

    body = "\n".join(lines).strip()
    tooltip_parts = [hint]
    if spawns and spawns[-1].get("description"):
        tooltip_parts.append(spawns[-1]["description"])
    elif log_rows and log_rows[-1].get("note"):
        tooltip_parts.append(str(log_rows[-1]["note"]))
    elif artifact_text:
        tooltip_parts.append(_short(artifact_text.split("\n")[0]))

    return {
        "step_id": step_id,
        "subagent": subagent,
        "state": state,
        "hint": hint,
        "tooltip": _short(" · ".join(tooltip_parts)),
        "body": body,
        "artifact_path": artifact_path,
        "spawn_count": len(spawns),
        "run_log_count": len(log_rows),
    }


def attach_node_details(
    nodes: list[dict],
    *,
    run_log: list[dict],
    events: list[dict],
    root: Path,
    slug: str,
    agent_run_id: str,
    pipeline: str,
) -> None:
    for node in nodes:
        node["detail"] = build_node_detail(
            step_id=node["id"],
            subagent=node.get("subagent"),
            kind=node.get("kind", "step"),
            state=node.get("state", "pending"),
            run_log=run_log,
            events=events,
            root=root,
            slug=slug,
            agent_run_id=agent_run_id,
            pipeline=pipeline,
        )

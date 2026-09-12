#!/usr/bin/env python3
"""Runtime validator: dispatch + telemetry vs workflow rules → actionable advice."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from agent_logs import events_path, load_manifest, run_log_path
from artifact_paths import resolve_slug, spec_path, workspace_root
from build_pipeline_graph import (
    collect_spawn_steps,
    history_closed_in_run_log,
    history_sort_key,
    is_session_live,
    latest_run_log_result,
    load_schema,
    merge_history,
    parse_iso_ts,
    read_jsonl,
)
from pipeline_active_task import load_active_task_for_slug
from feature_status import build_status, needs_check_feature
from pipeline_common import last_successful_step_ts
from pipeline_dispatch import build_dispatch
from pipeline_divergence import SEVERITY_ERROR, analyze_divergence, finalize_divergence

SEVERITY_BLOCK = "block"
SEVERITY_WARN = "warn"
SEVERITY_OK = "ok"

# Grace after last ok run-log before treating idle as a hard stop (hook → next task).
IDLE_HANDOFF_GRACE_SEC = 180


@dataclass
class Advice:
    id: str
    severity: str
    title: str
    detail: str
    workflow_fix: str


@dataclass
class ValidationReport:
    slug: str
    ok: bool
    ready: bool
    must_continue: bool
    next_step: str
    next_subagent: str
    advice: list[Advice] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "slug": self.slug,
            "ok": self.ok,
            "ready": self.ready,
            "must_continue": self.must_continue,
            "next_step": self.next_step,
            "next_subagent": self.next_subagent,
            "advice": [asdict(a) for a in self.advice],
        }


def _add(report: ValidationReport, *, id: str, severity: str, title: str, detail: str, fix: str) -> None:
    report.advice.append(
        Advice(id=id, severity=severity, title=title, detail=detail, workflow_fix=fix)
    )
    if severity == SEVERITY_BLOCK:
        report.ok = False


def validate_slug(root: Path, slug: str, *, pipeline: str = "spec") -> ValidationReport:
    dispatch = build_dispatch(root, slug)
    status = build_status(root, slug)
    report = ValidationReport(
        slug=slug,
        ok=True,
        ready=bool(dispatch.get("ready")),
        must_continue=bool(dispatch.get("must_continue")),
        next_step=dispatch.get("next_step") or "",
        next_subagent=dispatch.get("next_subagent") or "",
    )

    if report.ready:
        _add(
            report,
            id="pipeline-ready",
            severity=SEVERITY_OK,
            title="Spec готов",
            detail=dispatch.get("next_reason") or "PASS / PASS WITH GAPS",
            fix="Финальный ответ пользователю; калибровка — только по запросу.",
        )
        return report

    manifest = load_manifest(root, slug)
    rid = manifest.get("current_run") or "run-001"
    run_log = read_jsonl(run_log_path(root, slug, rid))
    events = read_jsonl(events_path(root, slug, rid))
    live = is_session_live(events)
    schema = load_schema()["pipelines"]["spec"]
    _, spawn_rows = collect_spawn_steps(events, schema)
    history = merge_history(run_log, spawn_rows)
    log_history = history_closed_in_run_log(history)
    last = max(log_history, key=history_sort_key) if log_history else None

    # --- Workflow violations with fixes ---

    if report.must_continue and not live:
        active_for_slug = bool(load_active_task_for_slug(root, slug))
        orchestrator_mode = dispatch.get("orchestrator_mode") or ""
        recent_handoff = False
        if last and (last.get("result") or "ok") == "ok":
            last_ts = parse_iso_ts(last.get("ts"))
            if last_ts is not None:
                recent_handoff = (
                    datetime.now(timezone.utc) - last_ts
                ).total_seconds() <= IDLE_HANDOFF_GRACE_SEC

        if orchestrator_mode == "write_feature_cycle":
            _add(
                report,
                id="write-feature-cycle-idle",
                severity=SEVERITY_WARN,
                title="write-feature: сессия idle между блоками",
                detail=(
                    f"Dispatch в режиме write_feature_cycle "
                    f"(`{report.next_step}`). Оркестратор может работать без subagent."
                ),
                fix="Продолжай цикл spec-writer / assemble. BLOCK не нужен.",
            )
        elif active_for_slug:
            pass
        elif recent_handoff:
            pass
        else:
            _add(
                report,
                id="stopped-while-must-continue",
                severity=SEVERITY_BLOCK,
                title="Пайплайн остановился раньше dispatch",
                detail=(
                    f"Dispatch ждёт `{report.next_step}` → `{report.next_subagent}`, "
                    f"но сессия idle."
                ),
                fix=(
                    "Немедленно: `pipeline_dispatch.py --json` → `task` на `next_subagent`. "
                    "Не завершай ход, не спрашивай «продолжить?»."
                ),
            )

    last_result = None
    if last:
        step = last.get("step") or ""
        last_result = latest_run_log_result(log_history, step) if step else last.get("result")
    if last and last_result in ("fail", "retry"):
        _add(
            report,
            id="last-step-fail",
            severity=SEVERITY_BLOCK,
            title=f"Последний шаг fail: {last.get('step')}",
            detail=last.get("note") or "Subagent вернул fail/retry",
            fix=(
                "1) `append_run_log.py --result fail --note '…'` "
                "2) dispatch 3) повтори `task` на `next_subagent` в том же ходе."
            ),
        )

    if (
        status.decisions_pending_apply
        and dispatch.get("orchestrator_mode") == "ask_user"
    ):
        _add(
            report,
            id="pending-apply-paused",
            severity=SEVERITY_BLOCK,
            title="pending-apply не должен ставить паузу",
            detail=f"В DECISIONS есть pending-apply ({status.decisions_pending_apply})",
            fix="Сразу `task` на gap/challenge/alignment-resolver для apply — без ask_user.",
        )

    if status.decisions_needs_answer and dispatch.get("orchestrator_mode") != "ask_user":
        _add(
            report,
            id="needs-answer-not-asked",
            severity=SEVERITY_BLOCK,
            title="Есть needs-answer в DECISIONS — нужен ask_user",
            detail=f"Строк: {status.decisions_needs_answer}",
            fix=(
                "`pipeline_delegate.py` → action ask_user. НЕ `task`. "
                "Опроси DECISIONS → pending-apply → delegate снова."
            ),
        )

    check_needed, check_reason = needs_check_feature(root, slug=slug, status=status)
    last_check_ts = last_successful_step_ts(root, slug, "check-feature")
    spec = spec_path(root, slug)
    if (
        check_needed
        and check_reason.startswith("SPEC новее GAPS_MAP")
        and last_check_ts is not None
        and spec.is_file()
        and last_check_ts >= spec.stat().st_mtime - 2
        and last
        and last.get("step") == "check-feature"
        and last.get("result") == "ok"
    ):
        _add(
            report,
            id="check-feature-redundant-loop",
            severity=SEVERITY_WARN,
            title="check-feature уже прошёл после правки SPEC",
            detail="Dispatch снова просит check-feature из-за SPEC > GAPS_MAP",
            fix=(
                "check-feature уже ok после правки SPEC — dispatch должен идти дальше "
                "(resolve-gaps / check-feature-code). Если SPEC не менялся — обнови GAPS_MAP "
                "или перезапусти dispatch после ingest."
            ),
        )

    if status.has_challenges and report.next_step == "challenge-feature":
        _add(
            report,
            id="challenge-repeat-blocked",
            severity=SEVERITY_BLOCK,
            title="Повторный challenge-feature запрещён",
            detail=(
                "Файл CHALLENGES уже существует — автоматический re-challenge после apply "
                "не допускается."
            ),
            fix=(
                "Dispatch → check-feature-code (или resolve-challenges, если CH open>0). "
                "Повторный `/challenge-feature` — только по явной команде пользователя."
            ),
        )

    divergence = analyze_divergence(
        root=root,
        slug=slug,
        schema=schema,
        history=history,
        current={"step": last.get("step"), "subagent": last.get("subagent")} if last else None,
        live=live,
        pipeline="spec",
    )
    finalize_divergence(divergence)
    for item in divergence.get("items") or []:
        if item.get("severity") != SEVERITY_ERROR and item.get("kind") == "stopped_early":
            continue
        fix = item.get("hint") or item.get("explain") or "Следуй dispatch."
        _add(
            report,
            id=f"div-{item.get('kind')}",
            severity=item.get("severity") or SEVERITY_WARN,
            title=item.get("title") or item.get("kind") or "divergence",
            detail=item.get("message") or "",
            fix=fix,
        )

    if not report.advice:
        _add(
            report,
            id="workflow-ok",
            severity=SEVERITY_OK,
            title="Workflow в норме",
            detail=f"Следующий шаг: {report.next_step} → {report.next_subagent}",
            fix="Продолжай: dispatch → task → append_run_log → ingest → validate.",
        )

    return report


def format_human(report: ValidationReport) -> str:
    lines = [
        f"## Pipeline validate — {report.slug}",
        "",
        f"**OK:** {'да' if report.ok else 'НЕТ'} · **ready:** {report.ready} · "
        f"**must_continue:** {report.must_continue}",
        f"**Next:** `{report.next_step}` → `{report.next_subagent}`",
        "",
    ]
    for a in report.advice:
        icon = {"ok": "✓", "warn": "⚠", "block": "✖"}.get(a.severity, "·")
        lines.append(f"### {icon} {a.title} (`{a.id}`)")
        if a.detail:
            lines.append(a.detail)
        lines.append(f"**Что делать:** {a.workflow_fix}")
        lines.append("")
    return "\n".join(lines).rstrip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slug", nargs="?")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args(argv)
    root = workspace_root(args.root)
    if not args.slug:
        parser.error("slug required")
    slug = resolve_slug(args.slug, root)
    if slug is None:
        parser.error("cannot resolve slug")

    report = validate_slug(root, slug)
    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(format_human(report))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

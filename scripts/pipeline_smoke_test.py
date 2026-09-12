#!/usr/bin/env python3
"""Smoke test: dispatch, graph builder, pipeline viewer API (spec + calibration)."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from build_pipeline_graph import build_graph  # noqa: E402
from pipeline_dispatch import build_dispatch  # noqa: E402

VIEWER_BASE = "http://127.0.0.1:8765"
SMOKE_SLUG = "pipeline-viewer-smoke"
PRIMARY_SLUG = "composite-active-order-commission"


@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""


@dataclass
class Report:
    checks: list[Check] = field(default_factory=list)

    def add(self, name: str, ok: bool, detail: str = "") -> None:
        self.checks.append(Check(name, ok, detail))

    @property
    def passed(self) -> bool:
        return all(c.ok for c in self.checks)

    def print_report(self) -> None:
        print("=" * 60)
        print("Pipeline smoke test")
        print("=" * 60)
        for c in self.checks:
            mark = "PASS" if c.ok else "FAIL"
            line = f"[{mark}] {c.name}"
            if c.detail:
                line += f"\n       {c.detail}"
            print(line)
        print("-" * 60)
        n_ok = sum(1 for c in self.checks if c.ok)
        print(f"Result: {n_ok}/{len(self.checks)} passed")
        print("=" * 60)


def fetch_json(url: str) -> tuple[dict | None, str | None]:
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8")), None
    except urllib.error.URLError as exc:
        return None, str(exc)
    except json.JSONDecodeError as exc:
        return None, f"JSON: {exc}"


def ensure_smoke_fixtures() -> None:
    """Minimal feature so dispatch/graph have something to read."""
    fw = ROOT / "Feature-writing" / SMOKE_SLUG
    fw.mkdir(parents=True, exist_ok=True)
    spec = fw / f"{SMOKE_SLUG}.md"
    if not spec.is_file():
        spec.write_text(
            f"# {SMOKE_SLUG}\n\nSmoke test spec for pipeline viewer.\n\n[GAP-SMOKE-01]\n",
            encoding="utf-8",
        )
    ctx = ROOT / "Feature-context" / f"{SMOKE_SLUG}.md"
    if not ctx.is_file():
        ctx.write_text(
            f"# Context — {SMOKE_SLUG}\n\nVerified smoke context.\n",
            encoding="utf-8",
        )
    logs = ROOT / "agent-logs" / SMOKE_SLUG / "runs" / "run-001"
    logs.mkdir(parents=True, exist_ok=True)
    manifest = ROOT / "agent-logs" / SMOKE_SLUG / "manifest.json"
    if not manifest.is_file():
        manifest.write_text(
            json.dumps(
                {
                    "slug": SMOKE_SLUG,
                    "current_run": "run-001",
                    "runs": ["run-001"],
                    "cli": "smoke-test",
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    run_log = logs / "run-log.jsonl"
    if not run_log.is_file():
        rows = [
            {
                "ts": "2026-09-12T00:00:01Z",
                "step": "find-context",
                "subagent": "context-researcher",
                "result": "ok",
            },
            {
                "ts": "2026-09-12T00:00:02Z",
                "step": "write-feature",
                "subagent": "spec-writer",
                "result": "ok",
            },
            {
                "ts": "2026-09-12T00:00:03Z",
                "step": "check-feature",
                "subagent": "spec-reviewer",
                "result": "ok",
            },
        ]
        run_log.write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
            encoding="utf-8",
        )


def check_dispatch(report: Report, slug: str) -> None:
    try:
        d = build_dispatch(ROOT, slug)
        ok = bool(d.get("slug")) and "next_step" in d
        report.add(
            f"dispatch:{slug}",
            ok,
            f"mode={d.get('orchestrator_mode')} must_continue={d.get('must_continue')} "
            f"next={d.get('next_step')} → {d.get('next_subagent')}",
        )
    except Exception as exc:
        report.add(f"dispatch:{slug}", False, str(exc))


def check_step_timings(report: Report, slug: str) -> None:
    from build_pipeline_graph import build_graph

    try:
        graph = build_graph(ROOT, slug)
        timings = graph.get("timings") or {}
        steps = timings.get("steps") or []
        rg = next((s for s in steps if s.get("id") == "resolve-gaps"), {})
        ok = (
            bool(steps)
            and (timings.get("total_sec") or 0) > 0
            and timings.get("primary_source") == "agent-logs"
            and (rg.get("passes") or 0) >= 4
        )
        report.add(
            f"step-timings:{slug}",
            ok,
            f"source={timings.get('primary_source')} rg_passes={rg.get('passes')} total={timings.get('total_label', '?')}",
        )
    except Exception as exc:
        report.add(f"step-timings:{slug}", False, str(exc))


def check_ts_sort_node_state(report: Report) -> None:
    """ISO timestamps with/without ms must sort chronologically (06Z after 06.288Z)."""
    from build_pipeline_graph import apply_history, load_schema

    schema = load_schema()["pipelines"]["spec"]
    history = [
        {
            "ts": "2026-09-12T14:47:06.288Z",
            "step": "check-feature",
            "result": "ok",
            "source": "run-log",
        },
        {
            "ts": "2026-09-12T14:47:06Z",
            "step": "check-feature",
            "result": "fail",
            "source": "run-log",
        },
    ]
    node_states, _ = apply_history(schema, history)
    ok = node_states.get("check-feature") == "ok"
    report.add("ts-sort:check-feature", ok, f"state={node_states.get('check-feature')}")


def check_graph_order_gate(report: Report, slug: str) -> None:
    """After write-feature, dispatch must not skip check-feature for graph branches."""
    from feature_status import build_status, needs_check_feature

    try:
        status = build_status(ROOT, slug)
        if not status.has_spec:
            report.add(f"graph-order-gate:{slug}", True, "no spec — skip")
            return
        need, _ = needs_check_feature(ROOT, slug, status)
        if not need:
            report.add(f"graph-order-gate:{slug}", True, "check-feature done — skip")
            return
        d = build_dispatch(ROOT, slug)
        ok = d.get("next_step") == "check-feature"
        report.add(
            f"graph-order-gate:{slug}",
            ok,
            f"next={d.get('next_step')} (must be check-feature before gaps)",
        )
    except Exception as exc:
        report.add(f"graph-order-gate:{slug}", False, str(exc))


def check_log_first_graph(report: Report, slug: str) -> None:
    """Graph state must follow run-log, not stale active-task."""
    runs_dir = ROOT / "agent-logs" / slug / "runs"
    if not runs_dir.is_dir():
        report.add(f"log-first:{slug}", True, "no logs — skip")
        return
    try:
        g = build_graph(ROOT, slug, pipeline="spec")
        nodes = {n["id"]: n["state"] for n in g.get("nodes", [])}
        cur = g.get("current") or {}
        rg_in_log = any(r.get("step") == "resolve-gaps" for r in g.get("timeline", []))
        ok = rg_in_log or nodes.get("check-feature") == "next"
        report.add(
            f"log-first:{slug}",
            ok,
            f"check-feature={nodes.get('check-feature')} resolve-gaps={nodes.get('resolve-gaps')} "
            f"current={cur.get('status')}:{cur.get('step')}",
        )
    except Exception as exc:
        report.add(f"log-first:{slug}", False, str(exc))


def check_graph_aggregate(report: Report, slug: str) -> None:
    """Multi-run slug: earlier steps from run-001 must appear when run-002 is live."""
    runs_dir = ROOT / "agent-logs" / slug / "runs"
    if not runs_dir.is_dir() or len(list(runs_dir.glob("run-*"))) < 2:
        report.add(f"graph-aggregate:{slug}", True, "single run — skip")
        return
    try:
        g = build_graph(ROOT, slug, pipeline="spec")
        runs = g.get("agent_run_ids") or []
        nodes = {n["id"]: n["state"] for n in g.get("nodes", [])}
        ok = (
            g.get("history_aggregate") is True
            and len(runs) >= 2
            and nodes.get("find-context") == "ok"
        )
        report.add(
            f"graph-aggregate:{slug}",
            ok,
            f"runs={runs} find-context={nodes.get('find-context')}",
        )
    except Exception as exc:
        report.add(f"graph-aggregate:{slug}", False, str(exc))


def check_graph(report: Report, slug: str, pipeline: str) -> None:
    try:
        g = build_graph(ROOT, slug, pipeline=pipeline)
        pipe = g.get("pipeline")
        nodes = [n["id"] for n in g.get("nodes", [])]
        timeline_steps = [r.get("step") for r in g.get("timeline", [])]
        ok = pipe == pipeline and nodes
        if pipeline == "calibration":
            bad = [s for s in timeline_steps if s in {"write-feature", "check-feature", "find-context"}]
            ok = ok and not bad
            extra = f" cal_run={g.get('calibration_run_id')} timeline={timeline_steps}"
        else:
            bad = [s for s in timeline_steps if s in {"snapshot-baseline", "cal-done"}]
            ok = ok and not bad
            val = g.get("validation") or {}
            ok = ok and isinstance(val, dict) and "ok" in val and "advice" in val
            extra = (
                f" timeline={timeline_steps[:8]}{'…' if len(timeline_steps) > 8 else ''}"
                f" validate_ok={val.get('ok')}"
            )
        report.add(f"graph:{slug}:{pipeline}", ok, f"nodes={len(nodes)}{extra}")
    except Exception as exc:
        report.add(f"graph:{slug}:{pipeline}", False, str(exc))


def check_viewer_api(report: Report, slug: str, pipeline: str) -> None:
    url = f"{VIEWER_BASE}/api/graph?slug={slug}&pipeline={pipeline}"
    data, err = fetch_json(url)
    if err:
        report.add(f"viewer-api:{pipeline}", False, err)
        return
    api_pipe = data.get("pipeline")
    timeline = [r.get("step") for r in data.get("timeline", [])]
    ok = api_pipe == pipeline
    if pipeline == "calibration":
        ok = ok and "write-feature" not in timeline
    else:
        ok = ok and "snapshot-baseline" not in timeline
        val = data.get("validation") or {}
        ok = ok and isinstance(val, dict) and "advice" in val
    report.add(
        f"viewer-api:{slug}:{pipeline}",
        ok,
        f"pipeline={api_pipe} timeline_len={len(timeline)}",
    )


def check_viewer_health(report: Report) -> None:
    data, err = fetch_json(f"{VIEWER_BASE}/api/health")
    if err:
        report.add("viewer-health", False, err)
        return
    ok = data.get("ok") and data.get("version", 0) >= 5
    report.add("viewer-health", ok, json.dumps(data, ensure_ascii=False))


def check_pipeline_delegate(report: Report, slug: str) -> None:
    from pipeline_delegate import build_delegate

    try:
        result = build_delegate(ROOT, slug, cli="qwen")
        action = result.get("action")
        ok = result.get("ok") is True and action in {
            "task",
            "ask_user",
            "ready",
            "stopped",
            "write_feature_cycle",
        }
        if action == "task":
            ok = ok and bool((result.get("task") or {}).get("subagent_type"))
            ok = ok and bool(result.get("active_task"))
        report.add(
            f"pipeline-delegate:{slug}",
            ok,
            f"action={action} step={(result.get('task') or {}).get('step', '—')}",
        )
    except Exception as exc:
        report.add(f"pipeline-delegate:{slug}", False, str(exc))


def check_challenge_one_pass(report: Report, slug: str) -> None:
    from feature_status import build_status

    try:
        status = build_status(ROOT, slug)
        if not status.has_challenges:
            report.add(
                f"challenge-one-pass:{slug}",
                True,
                "CHALLENGES ещё нет — проверка не применима",
            )
            return
        ok = status.next_step != "challenge-feature"
        report.add(
            f"challenge-one-pass:{slug}",
            ok,
            f"has_challenges open={status.challenges.open} next={status.next_step}",
        )
    except Exception as exc:
        report.add(f"challenge-one-pass:{slug}", False, str(exc))


def check_cli_settings(report: Report) -> None:
    from build_cli_settings import validate_settings, load_json, CLI_DIRS

    for cli, cli_dir in CLI_DIRS.items():
        path = cli_dir / "settings.json"
        if not path.is_file():
            report.add(f"cli-settings:{cli}", False, "missing settings.json")
            continue
        errors = validate_settings(load_json(path), cli)
        report.add(
            f"cli-settings:{cli}",
            not errors,
            "; ".join(errors) if errors else f"allow={len((load_json(path).get('permissions') or {}).get('allow', []))}",
        )


def check_pipeline_before_subagent(report: Report, slug: str) -> None:
    from pipeline_active_task import save_active_task
    from pipeline_before_subagent import validate_task

    save_active_task(
        ROOT,
        slug=slug,
        step="resolve-gaps",
        subagent="gap-resolver",
        cli="qwen",
    )
    allow = validate_task(ROOT, "gap-resolver")["hookSpecificOutput"]["permissionDecision"]
    deny = validate_task(ROOT, "spec-challenger")["hookSpecificOutput"]["permissionDecision"]
    ok = allow == "allow" and deny == "deny"
    report.add(
        f"pipeline-before-subagent:{slug}",
        ok,
        f"match={allow} mismatch={deny}",
    )


def check_pipeline_compile(report: Report) -> None:
    """Phase 1: compiled schema/registry match pipeline.yaml and legacy mapping."""
    import pipeline_compile as compile_mod

    try:
        data = compile_mod.load_yaml(compile_mod.YAML_PATH)
        ok, messages = compile_mod.run_check(data)
        failed = [m for m in messages if m.startswith("parity:") or "differs (" in m]
        detail = "; ".join(failed[:2]) if failed else "schema + registry parity ok"
        report.add("pipeline-compile", ok and not failed, detail)
    except Exception as exc:
        report.add("pipeline-compile", False, str(exc))


def check_dispatch_golden(report: Report) -> None:
    """Phase 0: isolated fixture matrix for build_dispatch contract."""
    import pipeline_dispatch_golden_test as golden

    cases = golden._load_cases()
    if not cases:
        report.add("dispatch-golden", False, f"no fixtures in {golden.FIXTURES_DIR}")
        return
    failed: list[str] = []
    for case in cases:
        case_id = case.get("id") or "?"
        try:
            ok, detail = golden.run_case(case)
        except Exception as exc:
            ok, detail = False, str(exc)
        if not ok:
            failed.append(f"{case_id}: {detail}")
    report.add(
        "dispatch-golden",
        not failed,
        f"{len(cases) - len(failed)}/{len(cases)} cases"
        + (f"; {failed[0]}" if failed else ""),
    )


def check_router_parity(report: Report) -> None:
    """Phase 2: compiled router matches legacy choose_next_step on golden fixtures."""
    import pipeline_router_parity_test as parity

    cases = parity.golden._load_cases()
    if not cases:
        report.add("router-parity", False, "no golden fixtures")
        return
    failed: list[str] = []
    for case in cases:
        case_id = case.get("id") or "?"
        try:
            ok, detail = parity.run_case(case)
        except Exception as exc:
            ok, detail = False, str(exc)
        if not ok:
            failed.append(f"{case_id}: {detail}")
    report.add(
        "router-parity",
        not failed,
        f"{len(cases) - len(failed)}/{len(cases)} cases"
        + (f"; {failed[0]}" if failed else ""),
    )


def check_run_until_done_policy(report: Report, slug: str) -> None:
    d = build_dispatch(ROOT, slug)
    policy = d.get("exit_policy") or {}
    ok = policy.get("continue_on_subagent_fail") is True
    report.add(
        "run-until-done:exit_policy",
        ok,
        json.dumps(policy, ensure_ascii=False),
    )
    if d.get("decisions_pending_apply") and d.get("orchestrator_mode") == "ask_user":
        report.add(
            "run-until-done:pending_apply_not_paused",
            False,
            "pending-apply incorrectly sets ask_user",
        )
    elif d.get("decisions_needs_answer"):
        report.add(
            "run-until-done:needs_answer_pauses",
            d.get("orchestrator_mode") == "ask_user",
            f"mode={d.get('orchestrator_mode')}",
        )


def main() -> int:
    report = Report()
    ensure_smoke_fixtures()

    check_dispatch_golden(report)
    check_router_parity(report)
    check_pipeline_compile(report)
    check_viewer_health(report)
    check_cli_settings(report)
    check_dispatch(report, SMOKE_SLUG)
    check_dispatch(report, PRIMARY_SLUG)
    check_pipeline_delegate(report, SMOKE_SLUG)
    check_pipeline_delegate(report, PRIMARY_SLUG)
    check_pipeline_before_subagent(report, SMOKE_SLUG)
    check_challenge_one_pass(report, PRIMARY_SLUG)
    check_run_until_done_policy(report, PRIMARY_SLUG)

    for slug in (SMOKE_SLUG, PRIMARY_SLUG):
        check_graph(report, slug, "spec")
        check_graph(report, slug, "calibration")
        check_viewer_api(report, slug, "spec")
        check_viewer_api(report, slug, "calibration")

    check_ts_sort_node_state(report)
    check_step_timings(report, "bph-moex-tax")
    check_graph_aggregate(report, "bph-moex-tax")
    check_graph_order_gate(report, "bph-moex-tax")
    check_log_first_graph(report, "bph-moex-tax")

    report.print_report()
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

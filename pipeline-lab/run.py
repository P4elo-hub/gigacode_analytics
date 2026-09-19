#!/usr/bin/env python3
"""Headless lab driver: delegate → apply_fixture → after_subagent → delegate.

No Qwen, no network. Workspace is pipeline-lab/. Pack is pipeline-lab/pack.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

LAB_ROOT = Path(__file__).resolve().parent
REPO_ROOT = LAB_ROOT.parent
SCRIPTS = REPO_ROOT / "scripts"
SCENARIOS = LAB_ROOT / "scenarios"
PACK_DIR = LAB_ROOT / "pack"

sys.path.insert(0, str(LAB_ROOT))
sys.path.insert(0, str(SCRIPTS))

from apply_fixture import STEP_TO_SUBAGENT, apply_fixture, cursor_file, hook_input_for, parse_cursor_doc, save_cursor  # noqa: E402
from pipeline_after_subagent import after_subagent  # noqa: E402
from pipeline_delegate import build_delegate  # noqa: E402
from pipeline_divergence import is_allowed_transition  # noqa: E402
from pipeline_pack import reset_pack_dir, set_pack_dir  # noqa: E402
from pipeline_runtime import load_pipeline_schema  # noqa: E402


def ensure_lab_git(workspace: Path) -> None:
    """Qwen loads .qwen/agents from getProjectRoot(); nearest .git wins.

    A nested repo in pipeline-lab/ keeps thin agents off the parent checkout.
    Temp workspaces used by tests are left alone.
    """
    workspace = workspace.resolve()
    if workspace != LAB_ROOT.resolve():
        return
    git_dir = workspace / ".git"
    if git_dir.exists():
        return
    subprocess.run(
        ["git", "init"],
        cwd=workspace,
        check=True,
        capture_output=True,
        text=True,
    )


MAX_TURNS = 12
CLI = "qwen"
PIPELINE_ID = "spec"
PATH_NAME = ".lab-path.json"


def scenario_ids() -> list[str]:
    return sorted(path.name for path in SCENARIOS.iterdir() if path.is_dir())


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def cleanup_slug(workspace: Path, slug: str) -> None:
    shutil.rmtree(workspace / "Feature-writing" / slug, ignore_errors=True)
    ctx = workspace / "Feature-context" / f"{slug}.md"
    if ctx.is_file():
        ctx.unlink()
    shutil.rmtree(workspace / "agent-logs" / slug, ignore_errors=True)
    active = workspace / ".pipeline-active-task.json"
    if active.is_file():
        try:
            data = json.loads(active.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
        if data.get("slug") == slug:
            active.unlink()


def path_file(workspace: Path, slug: str) -> Path:
    return workspace / "Feature-writing" / slug / PATH_NAME


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def prepare_scenario(scenario_id: str, *, workspace: Path | None = None) -> dict:
    scenario_dir = SCENARIOS / scenario_id
    if not scenario_dir.is_dir():
        raise FileNotFoundError(f"unknown scenario: {scenario_id}")
    workspace = (workspace or LAB_ROOT).resolve()
    slug = scenario_id
    ensure_lab_git(workspace)
    cleanup_slug(workspace, slug)
    cursor = parse_cursor_doc(load_json(scenario_dir / "cursor.json"))
    cursor["scenario"] = scenario_id
    cursor["tick"] = 0
    feature_dir = workspace / "Feature-writing" / slug
    feature_dir.mkdir(parents=True, exist_ok=True)
    save_cursor(cursor_file(workspace, slug), cursor)
    write_json(path_file(workspace, slug), [])
    return {
        "ok": True,
        "scenario": scenario_id,
        "slug": slug,
        "workspace": str(workspace),
        "ticks": len(cursor["ticks"]),
    }


def load_recorded_path(workspace: Path, slug: str) -> list[dict[str, str]]:
    path = path_file(workspace, slug)
    if not path.is_file():
        return []
    raw = load_json(path)
    if not isinstance(raw, list):
        raise ValueError(f"{path}: expected array")
    return raw


def remaining_cursor_ticks(workspace: Path, slug: str) -> int:
    cursor_path = cursor_file(workspace, slug)
    if not cursor_path.is_file():
        return 0
    data = parse_cursor_doc(load_json(cursor_path))
    tick = int(data.get("tick") or 0)
    return max(0, len(data["ticks"]) - tick)


def live_tick(scenario_id: str, *, workspace: Path | None = None) -> dict:
    """One live orchestrator turn: delegate → record path → gate task or stop.

    Same stop rule as headless run_scenario: after the last cursor fixture,
    record the next delegate JSON and stop (do not launch another thin agent).
    """
    scenario_dir = SCENARIOS / scenario_id
    if not scenario_dir.is_dir():
        raise FileNotFoundError(f"unknown scenario: {scenario_id}")
    workspace = (workspace or LAB_ROOT).resolve()
    slug = scenario_id
    feature_dir = workspace / "Feature-writing" / slug
    if not feature_dir.is_dir():
        raise FileNotFoundError(f"run --prepare {scenario_id} first")

    set_pack_dir(PACK_DIR, PIPELINE_ID)
    try:
        payload = build_delegate(
            workspace,
            slug,
            cli=CLI,
            pipeline_id=PIPELINE_ID,
        )
    finally:
        reset_pack_dir()

    entry = turn_entry(payload)
    path = load_recorded_path(workspace, slug)
    path.append(entry)
    write_json(path_file(workspace, slug), path)

    remaining = remaining_cursor_ticks(workspace, slug)
    task = payload.get("task") or {}
    launch = None
    if entry["action"] != "task":
        gate = "stop"
        reason = entry["action"]
    elif remaining <= 0:
        gate = "stop"
        reason = "cursor_exhausted"
    else:
        gate = "task"
        reason = "delegate"
        launch = {
            "subagent_type": str(task.get("subagent_type") or ""),
            "step": entry["step"],
        }
        if not launch["subagent_type"]:
            raise ValueError(f"{scenario_id}: action=task but no subagent_type")

    return {
        "ok": True,
        "scenario": scenario_id,
        "slug": slug,
        "delegate": payload,
        "gate": gate,
        "reason": reason,
        "launch": launch,
        "path": path,
        "cursor_remaining": remaining,
        "instruction": (
            f"task {launch['subagent_type']} (run_in_background: false)"
            if launch
            else f"stop ({reason}) — python3 run.py --compare {scenario_id}"
        ),
    }


def compare_scenario(scenario_id: str, *, workspace: Path | None = None) -> dict:
    scenario_dir = SCENARIOS / scenario_id
    if not scenario_dir.is_dir():
        raise FileNotFoundError(f"unknown scenario: {scenario_id}")
    workspace = (workspace or LAB_ROOT).resolve()
    slug = scenario_id
    expect = load_json(scenario_dir / "expect_path.json")
    actual = load_recorded_path(workspace, slug)
    if actual != expect:
        raise AssertionError(
            f"{scenario_id} path mismatch\n"
            f"  expected: {json.dumps(expect, ensure_ascii=False)}\n"
            f"  actual:   {json.dumps(actual, ensure_ascii=False)}"
        )
    if scenario_id == "lab-03-challenge-not-check":
        steps = [row["step"] for row in actual]
        if "check-feature" in steps:
            raise AssertionError("lab-03: path included check-feature")
        if "resolve-challenges" not in steps:
            raise AssertionError("lab-03: path never reached resolve-challenges")
        agents = [
            (row.get("step") or "")
            for row in actual
            if row.get("action") == "task"
        ]
        if agents and agents[-1] != "resolve-challenges":
            raise AssertionError(
                "lab-03: last task is not resolve-challenges "
                f"(got {agents[-1]!r})"
            )
    if scenario_id == "lab-01-retry-same-step":
        steps = [row["step"] for row in actual if row.get("action") == "task"]
        if len(steps) < 3 or steps[-1] != "analyze-routing":
            raise AssertionError(
                f"lab-01: after ASK_PARENT text expected analyze-routing, got {steps}"
            )
        if steps[-2] != "challenge-feature":
            raise AssertionError(f"lab-01: expected challenge-feature before refresh: {steps}")
    if scenario_id == "lab-06-pending-apply-beats-check":
        steps = [row["step"] for row in actual if row.get("action") == "task"]
        if "check-feature" in steps:
            raise AssertionError("lab-06: path included check-feature")
        if "resolve-challenges" not in steps:
            raise AssertionError("lab-06: path never reached resolve-challenges")
    if scenario_id == "lab-08-ch-apply-leftover-gaps":
        steps = [row["step"] for row in actual if row.get("action") == "task"]
        if "resolve-gaps" in steps:
            raise AssertionError("lab-08: leftover GAP stole to resolve-gaps")
        if "resolve-challenges" not in steps:
            raise AssertionError("lab-08: path never reached resolve-challenges")
    return {
        "ok": True,
        "scenario": scenario_id,
        "path": actual,
        "matched_expect_path": True,
    }


def turn_entry(payload: dict) -> dict[str, str]:
    task = payload.get("task") or {}
    dispatch = payload.get("dispatch") or {}
    step = str(task.get("step") or dispatch.get("next_step") or "")
    action = str(payload.get("action") or "")
    return {"action": action, "step": step}


def assert_lab_03_graph(schema: dict) -> None:
    """Regression: challenge-feature must go to resolve-challenges, not check-feature.

    If the main edge is removed, or check-feature becomes an allowed neighbor,
    lab-03 expect_path fails (dispatch would pick check-feature via needs_check).
    Do not leave the pack graph broken to demonstrate this — the live path is
    the assertion.
    """
    if not is_allowed_transition(schema, "challenge-feature", "resolve-challenges"):
        raise AssertionError(
            "lab-03: missing graph edge challenge-feature → resolve-challenges"
        )
    if is_allowed_transition(schema, "challenge-feature", "check-feature"):
        raise AssertionError(
            "lab-03: challenge-feature → check-feature is allowed (graph regression)"
        )


def run_scenario(
    scenario_id: str,
    *,
    workspace: Path | None = None,
    keep: bool = False,
) -> dict:
    scenario_dir = SCENARIOS / scenario_id
    if not scenario_dir.is_dir():
        raise FileNotFoundError(f"unknown scenario: {scenario_id}")
    cursor = load_json(scenario_dir / "cursor.json")
    expect = load_json(scenario_dir / "expect_path.json")
    if not isinstance(cursor, list) or not isinstance(expect, list):
        raise ValueError(f"{scenario_id}: cursor.json and expect_path.json must be arrays")

    workspace = (workspace or LAB_ROOT).resolve()
    slug = scenario_id
    cleanup_slug(workspace, slug)
    (workspace / "Feature-writing").mkdir(parents=True, exist_ok=True)

    set_pack_dir(PACK_DIR, PIPELINE_ID)
    schema = load_pipeline_schema(PIPELINE_ID)
    if scenario_id == "lab-03-challenge-not-check":
        assert_lab_03_graph(schema)

    path: list[dict[str, str]] = []
    tick_i = 0
    try:
        for _ in range(MAX_TURNS):
            payload = build_delegate(
                workspace,
                slug,
                cli=CLI,
                pipeline_id=PIPELINE_ID,
            )
            entry = turn_entry(payload)
            path.append(entry)
            if entry["action"] != "task":
                break
            if tick_i >= len(cursor):
                break
            tick = cursor[tick_i]
            tick_i += 1
            if not isinstance(tick, dict):
                raise ValueError(f"{scenario_id}: cursor tick {tick_i} is not an object")
            step = str(tick.get("step") or "")
            variant = str(tick.get("variant") or "")
            if step != entry["step"]:
                raise AssertionError(
                    f"{scenario_id} tick {tick_i}: cursor step {step!r} != "
                    f"delegate {entry['step']!r} ({entry['action']})"
                )
            applied = apply_fixture(slug, step, variant, workspace=workspace)
            after_subagent(
                workspace,
                hook_input_for(
                    step,
                    variant,
                    last_message=applied.get("last_message") or "",
                    subagent=STEP_TO_SUBAGENT[step],
                ),
                cli=CLI,
                pipeline_arg=PIPELINE_ID,
            )
        else:
            raise AssertionError(f"{scenario_id}: exceeded {MAX_TURNS} turns")
    finally:
        reset_pack_dir()
        if not keep:
            cleanup_slug(workspace, slug)

    if path != expect:
        raise AssertionError(
            f"{scenario_id} path mismatch\n"
            f"  expected: {json.dumps(expect, ensure_ascii=False)}\n"
            f"  actual:   {json.dumps(path, ensure_ascii=False)}"
        )
    if scenario_id == "lab-03-challenge-not-check":
        steps = [row["step"] for row in path]
        if "check-feature" in steps:
            raise AssertionError("lab-03: path included check-feature")
        if "resolve-challenges" not in steps:
            raise AssertionError("lab-03: path never reached resolve-challenges")
    if scenario_id == "lab-08-ch-apply-leftover-gaps":
        steps = [row["step"] for row in path if row.get("action") == "task"]
        if "resolve-gaps" in steps:
            raise AssertionError("lab-08: leftover GAP stole to resolve-gaps")
        if "resolve-challenges" not in steps:
            raise AssertionError("lab-08: path never reached resolve-challenges")
    return {"ok": True, "scenario": scenario_id, "path": path}


def run_all(*, workspace: Path | None = None, keep: bool = False) -> list[dict]:
    results = []
    for scenario_id in scenario_ids():
        results.append(run_scenario(scenario_id, workspace=workspace, keep=keep))
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--scenario", help="Headless: scenarios/<id>/")
    group.add_argument("--all", action="store_true", help="Headless: every scenario")
    group.add_argument("--prepare", metavar="ID", help="Live: seed cursor and empty path")
    group.add_argument("--tick", metavar="ID", help="Live: delegate + record + gate")
    group.add_argument("--compare", metavar="ID", help="Live: path vs expect_path.json")
    parser.add_argument("--keep", action="store_true", help="Leave workspace artifacts")
    parser.add_argument("--workspace", type=Path, default=LAB_ROOT)
    args = parser.parse_args(argv)

    try:
        if args.prepare:
            row = prepare_scenario(args.prepare, workspace=args.workspace)
            print(json.dumps(row, ensure_ascii=False, indent=2))
            return 0
        if args.tick:
            row = live_tick(args.tick, workspace=args.workspace)
            print(json.dumps(row, ensure_ascii=False, indent=2))
            return 0
        if args.compare:
            row = compare_scenario(args.compare, workspace=args.workspace)
            print(json.dumps(row, ensure_ascii=False, indent=2))
            print(f"PASS {row['scenario']}")
            return 0
        if args.all:
            results = run_all(workspace=args.workspace, keep=args.keep)
            for row in results:
                print(f"PASS {row['scenario']}")
            print(f"{len(results)} scenarios green")
            return 0
        row = run_scenario(args.scenario, workspace=args.workspace, keep=args.keep)
        print(json.dumps(row, ensure_ascii=False, indent=2))
        print(f"PASS {row['scenario']}")
        return 0
    except (AssertionError, FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

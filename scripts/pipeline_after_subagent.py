#!/usr/bin/env python3
"""SubagentStop hook: append_run_log → ingest → validate → inject advice."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from agent_logs import load_manifest, manifest_path, run_log_path
from artifact_paths import workspace_root
from build_pipeline_graph import load_schema, subagent_to_step
from pipeline_active_task import SKIP_SUBAGENTS, clear_active_task, load_active_task_latest
from pipeline_dispatch import build_dispatch
from pipeline_validate import SEVERITY_BLOCK, SEVERITY_WARN, ValidationReport, validate_slug

FAIL_HINTS = re.compile(
    r"(?i)\b(fail(?:ed|ure)?|error|exception|не\s+удал|ошибк|truncat|timeout|abort)\b"
)
RETRY_HINTS = re.compile(r"(?i)\bretry\b")
# Skill table cites «FAIL alignment» — not a subagent failure.
_FALSE_FAIL_SNIPPETS = re.compile(
    r"(?i)(\|\s*fail alignment\s*\||fail alignment\s*\|/resolve-code-alignment)"
)


def parse_hook_input(raw: str) -> dict:
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def infer_result(last_message: str) -> str:
    text = last_message or ""
    scrubbed = _FALSE_FAIL_SNIPPETS.sub("", text)
    if RETRY_HINTS.search(scrubbed):
        return "retry"
    if FAIL_HINTS.search(scrubbed):
        return "fail"
    return "ok"


def resolve_step(schema: dict, *, step: str | None, subagent: str) -> str | None:
    if step:
        return step
    return subagent_to_step(schema, subagent)


def read_jsonl_tail(path: Path, limit: int = 5) -> list[dict]:
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    rows: list[dict] = []
    for line in lines[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def recent_duplicate(path: Path, *, step: str, subagent: str, window_sec: int = 90) -> bool:
    now = datetime.now(timezone.utc)
    for row in reversed(read_jsonl_tail(path, limit=8)):
        if row.get("step") != step or (row.get("subagent") or "") != subagent:
            continue
        ts = row.get("ts")
        if not ts:
            return True
        try:
            parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            return True
        if (now - parsed).total_seconds() <= window_sec:
            return True
    return False


def run_script(root: Path, script: str, *args: str) -> tuple[int, str]:
    cmd = ["python3", str(root / "scripts" / script), *args]
    proc = subprocess.run(
        cmd,
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out.strip()


def validation_path(root: Path, slug: str) -> Path:
    return root / "agent-logs" / slug / "validation.json"


def save_validation(root: Path, slug: str, report: ValidationReport) -> None:
    path = validation_path(root, slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def format_hook_context(report: ValidationReport, *, step: str, subagent: str, result: str) -> str:
    blocks = [
        "PIPELINE HOOK — post-subagent cycle completed.",
        f"Step: {step} → {subagent} ({result})",
        f"Validate OK: {'yes' if report.ok else 'NO'} · must_continue: {report.must_continue}",
        f"Next dispatch: {report.next_step} → {report.next_subagent}",
        "",
    ]
    actionable = [a for a in report.advice if a.severity in (SEVERITY_BLOCK, SEVERITY_WARN)]
    if actionable:
        blocks.append("Workflow advice (follow before next dispatch):")
        for item in actionable:
            icon = "BLOCK" if item.severity == SEVERITY_BLOCK else "WARN"
            blocks.append(f"- [{icon}] {item.title}: {item.workflow_fix}")
    else:
        for item in report.advice:
            if item.severity == "ok":
                blocks.append(item.workflow_fix)
                break
    blocks.append("")
    blocks.append(
        "Orchestrator: run pipeline_dispatch.py --json, then task on next_subagent "
        "in the same turn if must_continue."
    )
    return "\n".join(blocks)


def hook_output(context: str) -> dict:
    return {
        "hookSpecificOutput": {
            "hookEventName": "SubagentStop",
            "additionalContext": context,
        }
    }


def noop_output(reason: str) -> dict:
    return hook_output(f"Pipeline hook skipped: {reason}")


def after_subagent(
    root: Path,
    hook_input: dict,
    *,
    cli: str,
    dry_run: bool = False,
) -> dict:
    agent_type = str(hook_input.get("agent_type") or "").strip()
    if not agent_type:
        return noop_output("no agent_type")
    if agent_type in SKIP_SUBAGENTS:
        return noop_output(f"subagent {agent_type} excluded")

    active = load_active_task_latest(root)
    slug = (active or {}).get("slug") or ""
    step = (active or {}).get("step") or ""
    subagent = (active or {}).get("subagent") or agent_type
    cli = (active or {}).get("cli") or cli

    if subagent != agent_type and not step:
        subagent = agent_type

    schema = load_schema()["pipelines"]["spec"]
    step = resolve_step(schema, step=step or None, subagent=subagent) or step or subagent

    if not slug:
        return noop_output("no active slug — run pipeline_set_active_task.py before task")

    result = infer_result(str(hook_input.get("last_assistant_message") or ""))
    note = ""
    if result != "ok":
        note = (hook_input.get("last_assistant_message") or "")[:240]

    manifest_exists = manifest_path(root, slug).is_file()
    run_log = run_log_path(root, slug, load_manifest(root, slug).get("current_run") or "run-001")

    if dry_run:
        report = validate_slug(root, slug)
        return {
            "dry_run": True,
            "slug": slug,
            "step": step,
            "subagent": subagent,
            "result": result,
            "validation": report.to_dict(),
        }

    if not recent_duplicate(run_log, step=step, subagent=subagent):
        args = [
            "--slug",
            slug,
            "--step",
            step,
            "--subagent",
            subagent,
            "--result",
            result,
        ]
        if note:
            args.extend(["--note", note])
        code, out = run_script(root, "append_run_log.py", *args)
        if code != 0:
            return hook_output(f"append_run_log failed ({code}): {out[:500]}")

    sync_note = ""
    try:
        from sync_pipeline_session import sync_session

        if not manifest_exists:
            run_script(root, "ingest_session_telemetry.py", slug, "--cli", cli, "--new-run", "--copy-raw")
        sync_result = sync_session(root, slug, cli=cli)
        parts = []
        if sync_result.get("ingested"):
            parts.append("ingest")
        if sync_result.get("backfilled"):
            parts.append(f"backfill×{len(sync_result['backfilled'])}")
        archived = sync_result.get("archived") or {}
        if archived.get("passes_archived"):
            parts.append(f"archive×{archived['passes_archived']}")
        sync_note = f" sync: {', '.join(parts) or 'up to date'}"
    except Exception as exc:  # noqa: BLE001 — hook must not crash orchestrator
        sync_note = f" sync warn: {exc!s}"[:200]

    report = validate_slug(root, slug)
    save_validation(root, slug, report)

    keep_active = False
    if active and active.get("persistent") and active.get("step") == "write-feature":
        try:
            keep_active = build_dispatch(root, slug).get("orchestrator_mode") == "write_feature_cycle"
        except Exception:
            keep_active = True
    if not keep_active:
        clear_active_task(root, slug)

    context = format_hook_context(report, step=step, subagent=subagent, result=result)
    if sync_note:
        context += sync_note
    return hook_output(context)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", choices=("qwen", "gigacode", "opencode"), default="qwen")
    parser.add_argument("--workspace", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true", help="No writes; JSON report to stdout")
    parser.add_argument("--stdin-file", type=Path, help="Hook input file (default: stdin)")
    args = parser.parse_args(argv)

    root = (args.workspace or workspace_root()).resolve()
    if args.stdin_file:
        raw = args.stdin_file.read_text(encoding="utf-8")
    else:
        raw = sys.stdin.read()

    hook_input = parse_hook_input(raw)
    payload = after_subagent(root, hook_input, cli=args.cli, dry_run=args.dry_run)

    if args.dry_run:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

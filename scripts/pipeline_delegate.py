#!/usr/bin/env python3
"""Mandatory pre-task gate: dispatch → graph check → active-task → task envelope.

Orchestrator MUST call this before every `task` on a pipeline subagent.
Exit 0 = proceed (task envelope or terminal mode info); 2 = pause (ask_user).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from artifact_paths import resolve_slug, workspace_root
from build_pipeline_graph import load_schema
from pipeline_active_task import save_active_task
from pipeline_common import read_run_log, subagent_for_step
from pipeline_dispatch import build_dispatch
from pipeline_divergence import is_allowed_transition, last_ok_pipeline_step


def build_delegate(root: Path, slug: str, *, cli: str = "qwen") -> dict:
    dispatch = build_dispatch(root, slug)
    mode = dispatch.get("orchestrator_mode") or ""
    next_step = dispatch.get("next_step") or ""
    next_subagent = dispatch.get("next_subagent") or ""

    payload: dict = {
        "ok": True,
        "slug": slug,
        "action": "none",
        "dispatch": dispatch,
        "task": None,
        "active_task": None,
        "transition": None,
        "instruction": "",
    }

    if dispatch.get("ready"):
        payload["action"] = "ready"
        payload["instruction"] = dispatch.get("next_reason") or "Spec готов — финальный ответ пользователю."
        return payload

    if mode == "stopped" or not next_step:
        payload["action"] = "stopped"
        payload["instruction"] = dispatch.get("next_reason") or "Пайплайн остановлен."
        return payload

    if mode == "ask_user":
        payload["action"] = "ask_user"
        payload["ok"] = True
        payload["instruction"] = (
            "НЕ вызывай `task`. Прочитай DECISIONS → `ask_user_question` по строкам "
            "`needs-answer` → запиши Decision/Status → снова `pipeline_delegate.py`."
        )
        return payload

    if mode == "write_feature_cycle":
        active = save_active_task(
            root,
            slug=slug,
            step="write-feature",
            subagent="spec-writer",
            cli=cli,
            pipeline="spec",
            persistent=True,
        )
        payload["action"] = "write_feature_cycle"
        payload["active_task"] = active
        payload["instruction"] = (
            "Цикл write-feature (spec-writer по блокам). Не делегируй resolve/check/code "
            "пока assemble + check-feature не завершены. После assemble — снова "
            "`pipeline_delegate.py` → `task spec-reviewer`."
        )
        return payload

    if mode != "delegate" or not next_subagent:
        payload["ok"] = False
        payload["action"] = "error"
        payload["instruction"] = f"Неизвестный режим orchestrator: {mode!r}"
        return payload

    schema = load_schema()["pipelines"]["spec"]
    last = last_ok_pipeline_step(root, slug)
    from_step = last.get("step") if last else schema.get("orchestrator")
    if from_step and next_step and not is_allowed_transition(schema, from_step, next_step):
        allowed = [
            e.get("to")
            for e in schema.get("edges", [])
            if e.get("from") == from_step
        ]
        payload["ok"] = False
        payload["action"] = "error"
        payload["instruction"] = (
            f"Запрещённый переход `{from_step}` → `{next_step}` — нет ребра в pipeline_schema.json. "
            f"Допустимо из `{from_step}`: {', '.join(allowed) or '—'}. "
            "Вызови только `next_step` из dispatch после `pipeline_delegate.py`."
        )
        return payload

    canonical = subagent_for_step(next_step)
    if canonical and next_subagent != canonical:
        payload["ok"] = False
        payload["action"] = "error"
        payload["instruction"] = (
            f"Mapping error: step `{next_step}` → `{canonical}`, "
            f"dispatch вернул `{next_subagent}`."
        )
        return payload

    active = save_active_task(
        root,
        slug=slug,
        step=next_step,
        subagent=next_subagent,
        cli=cli,
        pipeline="spec",
    )

    payload["action"] = "task"
    payload["task"] = {
        "subagent_type": next_subagent,
        "run_in_background": False,
        "step": next_step,
    }
    payload["active_task"] = active
    payload["transition"] = {
        "from_step": from_step,
        "to_step": next_step,
        "allowed_by_schema": True,
        "warning": None,
    }
    payload["instruction"] = (
        f"Единственный разрешённый вызов: `task` → `{next_subagent}` "
        f"(step `{next_step}`). Причина dispatch: {dispatch.get('next_reason', '')}"
    )
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pipeline-delegate", description=__doc__)
    parser.add_argument("slug")
    parser.add_argument("--root", type=Path, default=".")
    parser.add_argument("--cli", choices=("qwen", "gigacode", "opencode"), default="qwen")
    parser.add_argument(
        "--assert-subagent",
        metavar="SUBAGENT",
        help="Exit 1 if canonical next_subagent differs (orchestrator preflight)",
    )
    args = parser.parse_args(argv)

    root = workspace_root(args.root)
    slug = resolve_slug(args.slug, root)
    if slug is None:
        print(json.dumps({"ok": False, "error": f"unknown slug: {args.slug}"}), ensure_ascii=False)
        return 1

    result = build_delegate(root, slug, cli=args.cli)

    if args.assert_subagent:
        task = result.get("task") or {}
        expected = task.get("subagent_type") or result.get("dispatch", {}).get("next_subagent")
        ok = expected == args.assert_subagent
        print(
            json.dumps(
                {
                    "ok": ok,
                    "expected_subagent": expected,
                    "proposed_subagent": args.assert_subagent,
                    "action": result.get("action"),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0 if ok else 1

    print(json.dumps(result, ensure_ascii=False, indent=2))

    if not result.get("ok"):
        return 1
    if result.get("action") == "ask_user":
        return 2
    if result.get("action") in ("ready", "stopped", "write_feature_cycle"):
        return 0
    if result.get("action") == "task":
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

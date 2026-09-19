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

from artifact_paths import resolve_slug
from pipeline_active_task import save_active_task
from inner_cycle import (
    ACTION_DONE,
    close_cycle_cell,
    close_finished_cycle_marker,
    cycle_closes_on_done,
    cycle_config_for_step,
    is_cycle_mode,
    next_cycle_at,
)
from pipeline_common import subagent_for_step, write_cycle_config
from pipeline_dispatch import build_dispatch
from pipeline_divergence import is_allowed_transition, last_ok_pipeline_step
from pipeline_pack import (
    add_pack_dir_argument,
    apply_pack_dir_from_args,
    workspace_root_for_run,
)
from pipeline_position import resolve_position
from pipeline_runtime import (
    DEFAULT_PIPELINE_ID,
    known_pipeline_ids,
    load_pipeline_schema,
    normalize_pipeline_id,
)


def _edge_error(schema: dict, from_step: str, next_step: str) -> str:
    allowed = [e.get("to") for e in schema.get("edges", []) if e.get("from") == from_step]
    return (
        f"Запрещённый переход `{from_step}` → `{next_step}` — нет ребра в pipeline_schema.json. "
        f"Допустимо из `{from_step}`: {', '.join(allowed) or '—'}. "
        "Вызови только `next_step` из dispatch после `pipeline_delegate.py`."
    )


def build_delegate(
    root: Path,
    slug: str,
    *,
    cli: str = "qwen",
    pipeline_id: str = DEFAULT_PIPELINE_ID,
    from_step: str | None = None,
    to_step: str | None = None,
    _cycle_closed: bool = False,
) -> dict:
    pipe_id = normalize_pipeline_id(pipeline_id)
    if not _cycle_closed:
        closed = close_finished_cycle_marker(root, slug, pipeline_id=pipe_id)
        if closed:
            return build_delegate(
                root,
                slug,
                cli=cli,
                pipeline_id=pipe_id,
                from_step=from_step,
                to_step=to_step,
                _cycle_closed=True,
            )
    dispatch = build_dispatch(root, slug, pipeline_id=pipe_id)
    schema = load_pipeline_schema(pipe_id)
    mode = dispatch.get("orchestrator_mode") or ""
    next_step = to_step or dispatch.get("next_step") or ""
    next_subagent = dispatch.get("next_subagent") or ""

    payload: dict = {
        "ok": True,
        "slug": slug,
        "pipeline_id": pipe_id,
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

    if mode == "orchestrator_only":
        last = last_ok_pipeline_step(root, slug, pipe_id)
        origin = from_step or (last.get("step") if last else schema.get("orchestrator"))
        payload["action"] = "orchestrator_only"
        payload["instruction"] = (
            "Dispatch не настроен для этого pipeline — оркестратор ведёт шаги по markdown. "
            "Рёбра графа проверяются через `--from-step` / `--to-step`."
        )
        if next_step:
            if origin and not is_allowed_transition(schema, origin, next_step):
                payload["ok"] = False
                payload["action"] = "error"
                payload["instruction"] = _edge_error(schema, origin, next_step)
                return payload
            payload["transition"] = {
                "from_step": origin,
                "to_step": next_step,
                "allowed_by_schema": True,
            }
        return payload

    if mode == "stopped" or not next_step:
        payload["action"] = "stopped"
        payload["instruction"] = dispatch.get("next_reason") or "Пайплайн остановлен."
        return payload

    if mode == "ask_user":
        payload["action"] = "ask_user"
        payload["ok"] = True
        # Handshake stays on this step: ask → apply. Do not re-enter the router
        # between the answer and apply — overlay JSON would still say needs-answer.
        if next_step and next_subagent:
            active = save_active_task(
                root,
                slug=slug,
                step=next_step,
                subagent=next_subagent,
                cli=cli,
                pipeline=pipe_id,
                persistent=True,
            )
            payload["task"] = {
                "subagent_type": next_subagent,
                "run_in_background": False,
                "step": next_step,
            }
            payload["active_task"] = active
            payload["instruction"] = (
                "Сейчас НЕ вызывай `task`. Прочитай DECISIONS → `ask_user_question` "
                "по строкам `needs-answer` → запиши Decision и Status "
                "`pending-apply` или `deferred`. "
                f"После ответа сразу `task` → `{next_subagent}` "
                f"(step `{next_step}`, apply). "
                "НЕ вызывай `pipeline_delegate.py` между ответом и apply — "
                "`task` уже в этом JSON. "
                "После возврата apply — снова `pipeline_delegate.py`."
            )
        else:
            payload["instruction"] = (
                "НЕ вызывай `task`. Прочитай DECISIONS → `ask_user_question` "
                "по строкам `needs-answer`."
            )
        return payload

    if is_cycle_mode(mode):
        cycle = cycle_config_for_step(pipe_id, next_step) or write_cycle_config(pipe_id)
        cycle_step = str(cycle.get("step") or next_step or "")
        cycle_subagent = str(cycle.get("subagent") or "")
        try:
            cycle_next = next_cycle_at(
                slug, root=root, pipeline_id=pipe_id, step=cycle_step
            )
        except Exception:  # noqa: BLE001 — cycle hint must not break delegate
            cycle_next = None
        if (
            isinstance(cycle_next, dict)
            and cycle_next.get("action") == ACTION_DONE
            and cycle_closes_on_done(cycle)
            and not _cycle_closed
        ):
            close_cycle_cell(root, slug, cycle_step, pipeline_id=pipe_id)
            return build_delegate(
                root,
                slug,
                cli=cli,
                pipeline_id=pipe_id,
                from_step=from_step,
                to_step=to_step,
                _cycle_closed=True,
            )
        active = save_active_task(
            root,
            slug=slug,
            step=cycle_step,
            subagent=cycle_subagent,
            cli=cli,
            pipeline=pipe_id,
            persistent=bool(cycle.get("persistent", True)),
        )
        payload["action"] = "write_feature_cycle"
        payload["active_task"] = active
        payload["cycle"] = cycle_next
        follow_step = ""
        for edge in schema.get("edges") or []:
            if edge.get("from") == cycle_step and (edge.get("kind") or "main") == "main":
                follow_step = str(edge.get("to") or "")
                break
        follow_agent = subagent_for_step(follow_step, pipe_id) if follow_step else ""
        cycle_hint = ""
        if isinstance(cycle_next, dict) and cycle_next.get("action") == "task":
            cycle_hint = (
                f" Сейчас `task {cycle_next.get('subagent')}` "
                f"param=`{cycle_next.get('param') or cycle_next.get('block_id')}`."
            )
        elif isinstance(cycle_next, dict) and cycle_next.get("action") == "assemble":
            cycle_hint = (
                " Сейчас сборка скриптом клетки (не task агента)."
            )
        elif isinstance(cycle_next, dict) and cycle_next.get("action") == ACTION_DONE:
            cycle_hint = (
                " Клетка закрыта. Не вызывай агента клетки — смотри next_step снаружи."
            )
        payload["instruction"] = (
            f"Цикл {cycle_step} (очередь вызовов внутри клетки). JSON `cycle`: "
            f"`task` / `assemble` / `done`. Routing между пунктами не вызывай. "
            f"После assemble — снова `pipeline_delegate.py` → "
            f"`task {follow_agent or follow_step}`.{cycle_hint}"
        )
        return payload

    if mode != "delegate" or not next_subagent:
        payload["ok"] = False
        payload["action"] = "error"
        payload["instruction"] = f"Неизвестный режим orchestrator: {mode!r}"
        return payload

    last = last_ok_pipeline_step(root, slug, pipe_id)
    standing = resolve_position(root, slug, pipe_id)
    origin = from_step or (standing.get("step") if standing else None) or (
        last.get("step") if last else schema.get("orchestrator")
    )
    if origin and next_step and not is_allowed_transition(schema, origin, next_step):
        payload["ok"] = False
        payload["action"] = "error"
        payload["instruction"] = _edge_error(schema, origin, next_step)
        return payload

    canonical = subagent_for_step(next_step, pipe_id)
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
        pipeline=pipe_id,
    )

    payload["action"] = "task"
    payload["task"] = {
        "subagent_type": next_subagent,
        "run_in_background": False,
        "step": next_step,
    }
    payload["active_task"] = active
    payload["transition"] = {
        "from_step": origin,
        "to_step": next_step,
        "allowed_by_schema": True,
    }
    reason = dispatch.get("next_reason", "")
    payload["instruction"] = (
        f"Единственный разрешённый вызов: `task` → `{next_subagent}` "
        f"(step `{next_step}`). Причина dispatch: {reason}"
    )
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pipeline-delegate", description=__doc__)
    parser.add_argument("slug")
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--cli", choices=("qwen", "gigacode", "opencode"), default="qwen")
    parser.add_argument(
        "--pipeline",
        default=DEFAULT_PIPELINE_ID,
        help=f"Pipeline id (default {DEFAULT_PIPELINE_ID}). Known: {', '.join(known_pipeline_ids())}",
    )
    add_pack_dir_argument(parser)
    parser.add_argument("--from-step", default=None, help="Explicit graph origin for edge check")
    parser.add_argument("--to-step", default=None, help="Explicit graph target for edge check")
    parser.add_argument(
        "--assert-subagent",
        metavar="SUBAGENT",
        help="Exit 1 if canonical next_subagent differs (orchestrator preflight)",
    )
    args = parser.parse_args(argv)

    try:
        apply_pack_dir_from_args(args)
    except FileNotFoundError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), ensure_ascii=False)
        return 1

    root = workspace_root_for_run(args.root)
    slug = resolve_slug(args.slug, root)
    if slug is None:
        print(json.dumps({"ok": False, "error": f"unknown slug: {args.slug}"}), ensure_ascii=False)
        return 1

    try:
        pipeline_id = normalize_pipeline_id(args.pipeline)
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), ensure_ascii=False)
        return 1

    result = build_delegate(
        root,
        slug,
        cli=args.cli,
        pipeline_id=pipeline_id,
        from_step=args.from_step,
        to_step=args.to_step,
    )

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
    if result.get("action") in ("ready", "stopped", "write_feature_cycle", "orchestrator_only"):
        return 0
    if result.get("action") == "task":
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Compare runtime telemetry vs canonical pipeline_dispatch expectations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pipeline_common import STEP_TO_SUBAGENT, read_run_log, subagent_for_step
from pipeline_dispatch import build_dispatch

SEVERITY_ERROR = "error"
SEVERITY_WARN = "warn"

KIND_META: dict[str, dict[str, str]] = {
    "stopped_early": {
        "title": "Пайплайн остановился раньше времени",
        "explain": (
            "Сессия агента уже не активна, но по состоянию артефактов следующий шаг "
            "ещё не выполнен. Оркестратор должен был продолжить сам, без «продолжи»."
        ),
        "hint": "Запустите `/feature-status <slug>` или скажите оркестратору продолжить — "
        "он должен вызвать указанный next step.",
    },
    "live_subagent_mismatch": {
        "title": "Сейчас выполняется не тот субагент",
        "explain": (
            "В телеметрии виден running-субагент, который не совпадает с тем, "
            "кого `pipeline_dispatch.py` считает следующим."
        ),
        "hint": "Оркестратор должен делегировать только `next_subagent` из dispatch.",
    },
    "wrong_subagent_for_step": {
        "title": "Шаг вызван через другого субагента",
        "explain": (
            "Для pipeline-шага есть канонический субагент (см. таблицу в spec-orchestrator), "
            "но в events/run-log зафиксирован другой."
        ),
        "hint": "Проверьте mapping шаг → субагент в `.gigacode/agents/spec-orchestrator.md`.",
    },
    "order_violation": {
        "title": "Нестандартный порядок шагов",
        "explain": (
            "Переход между шагами не совпадает с рёбрами графа в `pipeline_schema.json`. "
            "Иногда это нормально (например, откат к check-feature после правок SPEC), "
            "но часто — признак того, что оркестратор «перепрыгнул» гейт."
        ),
        "hint": "Сравните с каноном: write → check-feature → gaps/challenge → check-feature-code "
        "↔ resolve-code-alignment.",
    },
    "dispatch_ahead_of_log": {
        "title": "Dispatch опережает run-log",
        "explain": (
            "По артефактам dispatch считает, что можно перейти к ветке, "
            "но в run-log обязательный шаг главной колонки ещё не закрыт."
        ),
        "hint": "Сначала `/check-feature` (строка в run-log), затем ветки gaps/challenge.",
    },
    "active_task_without_log": {
        "title": "Active-task не подтверждён run-log",
        "explain": (
            "Оркестратор записал `.pipeline-active-task.json`, но в run-log нет закрытого "
            "прохода этого шага (SubagentStop). Viewer показывает только run-log + live spawn."
        ),
        "hint": "Дождитесь SubagentStop или проверьте hooks; не доверяйте active-task без строки в run-log.",
    },
}

# Частые «откаты» — не error, а мягкое предупреждение с пояснением.
SOFT_ORDER_PAIRS: dict[tuple[str, str], str] = {
    ("check-feature-code", "check-feature"): (
        "После code-audit spec могли поправить — возврат к check-feature допустим "
        "по analytics-workflow, хотя на графе viewer нет такого ребра."
    ),
    ("check-feature-code", "resolve-gaps"): (
        "После code-audit могли открыться GAP — resolve-gaps логичен, "
        "но по схеме графа из check-feature-code ожидается resolve-code-alignment или PASS."
    ),
    ("resolve-gaps", "check-feature"): (
        "Петля resolve-gaps → check-feature — штатная (перепроверка после закрытия gaps)."
    ),
    ("check-feature", "resolve-challenges"): (
        "После check-feature могли открыться CH без нового challenge-feature — "
        "применение pending-apply из DECISIONS разрешено, хотя ребра нет в графе viewer."
    ),
    ("resolve-challenges", "check-feature"): (
        "Петля resolve-challenges → check-feature — штатная."
    ),
    ("resolve-code-alignment", "check-feature-code"): (
        "Петля alignment → повторный code-audit — штатная."
    ),
    ("resolve-code-alignment", "check-feature"): (
        "Правка SPEC по alignment-находкам, затронувшая BR/CN/use case, требует "
        "перепроверки документа — возврат к check-feature штатен, хотя ребра в графе нет."
    ),
    ("check-feature", "resolve-code-alignment"): (
        "check-feature подтвердил, что SPEC отражает применённые решения; остаточные "
        "alignment-находки закрываются в resolve-code-alignment — ребра в графе нет, "
        "петля замыкается через последующий check-feature-code."
    ),
    ("resolve-gaps", "resolve-code-alignment"): (
        "Alignment-находки, адресованные § с открытыми GAP, сначала закрываются "
        "через resolve-gaps — шаг resolve-code-alignment после разрешения гэпов штатен."
    ),
    ("resolve-gaps", "resolve-challenges"): (
        "GAP и CH-ответы живут в одном DECISIONS-файле: применение батча resolve-gaps "
        "может закрыть и challenge-строки, поэтому переход в resolve-challenges допустим."
    ),
}


def _allowed_targets_labeled(schema: dict, from_step: str) -> list[str]:
    labels: list[str] = []
    for edge in schema.get("edges", []):
        if edge.get("from") == from_step:
            target = edge.get("to", "")
            label = edge.get("label")
            labels.append(f"{target}" + (f" ({label})" if label else ""))
    return labels


def _enrich_item(item: dict[str, Any], schema: dict, dispatch: dict) -> dict[str, Any]:
    kind = item.get("kind") or ""
    meta = KIND_META.get(kind, {})
    enriched = {**item, "title": meta.get("title", kind)}

    if kind == "stopped_early":
        reason = dispatch.get("next_reason") or ""
        enriched["detail"] = (
            f"Последний зафиксированный шаг: `{item.get('actual_step')}` "
            f"({item.get('actual_subagent') or '—'}).\n"
            f"Dispatch ожидает: `{item.get('expected_step')}` "
            f"→ `{item.get('expected_subagent')}`.\n"
            f"Причина dispatch: {reason}"
        )
        enriched["hint"] = meta.get("hint", "")

    elif kind == "live_subagent_mismatch":
        enriched["detail"] = (
            f"Running: `{item.get('actual_subagent')}` на шаге `{item.get('actual_step')}`.\n"
            f"Dispatch ждёт: `{item.get('expected_subagent')}` → `{item.get('expected_step')}`."
        )
        enriched["hint"] = meta.get("hint", "")

    elif kind == "wrong_subagent_for_step":
        enriched["detail"] = (
            f"Шаг `{item.get('step')}`: вызван `{item.get('actual_subagent')}`, "
            f"канон — `{item.get('expected_subagent')}`."
        )
        enriched["hint"] = meta.get("hint", "")

    elif kind == "order_violation":
        pair = (item.get("from_step") or "", item.get("to_step") or "")
        allowed = _allowed_targets_labeled(schema, pair[0])
        soft = SOFT_ORDER_PAIRS.get(pair)
        enriched["detail"] = (
            f"Было: `{pair[0]}` → `{pair[1]}`.\n"
            f"По графу из `{pair[0]}` допустимо: {', '.join(allowed) or '—'}."
        )
        if soft:
            enriched["severity"] = SEVERITY_WARN
            enriched["detail"] += f"\n\nКонтекст: {soft}"
        enriched["hint"] = meta.get("hint", "")
        enriched["allowed_targets"] = allowed

    else:
        enriched["detail"] = item.get("message", "")
        enriched["hint"] = meta.get("hint", "")

    enriched["explain"] = meta.get("explain", "")
    enriched["related_steps"] = _related_steps(enriched)
    return enriched


def _related_steps(item: dict[str, Any]) -> list[str]:
    steps: set[str] = set()
    for key in ("step", "from_step", "to_step", "actual_step", "expected_step"):
        value = item.get(key)
        if value:
            steps.add(str(value))
    return sorted(steps)


def _parse_iso_ts(ts: str | None):
    if not ts:
        return None
    from datetime import datetime

    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _previous_step_row(timeline: list[dict], index: int) -> dict | None:
    for i in range(index - 1, -1, -1):
        if timeline[i].get("step"):
            return timeline[i]
    return None


def _crosses_stale_boundary(timeline: list[dict], ts: str | None) -> bool:
    """True if this pass follows immediately after a stale (pre-restart) pass."""
    if not ts:
        return False
    ts_to_idx = {row.get("ts"): i for i, row in enumerate(timeline) if row.get("ts")}
    index = ts_to_idx.get(ts)
    if index is None:
        return False
    prev = _previous_step_row(timeline, index)
    return bool(prev and prev.get("display_state") == "stale")


def filter_divergence_for_restart(
    items: list[dict[str, Any]],
    *,
    timeline: list[dict],
    restart_info: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Drop divergence records tied to stale telemetry after pipeline rollback."""
    if not restart_info or not restart_info.get("active"):
        return items

    stale_ts = {
        row.get("ts")
        for row in timeline
        if row.get("display_state") == "stale" and row.get("ts")
    }
    marker_ts = _parse_iso_ts(restart_info.get("created_at"))
    redo_steps = set(restart_info.get("redo_steps") or [])

    filtered: list[dict[str, Any]] = []
    for item in items:
        kind = item.get("kind") or ""
        ts = item.get("ts")

        if ts and ts in stale_ts:
            continue

        if kind == "order_violation" and _crosses_stale_boundary(timeline, ts):
            # Переход через границу отката (устаревший → новый прогон) — не нарушение.
            continue

        if marker_ts and kind in ("order_violation", "wrong_subagent_for_step"):
            item_ts = _parse_iso_ts(ts)
            if item_ts and item_ts < marker_ts:
                related = set(item.get("related_steps") or _related_steps(item))
                if related & redo_steps:
                    continue

        if kind == "stopped_early" and restart_info.get("pending_redo"):
            # После ручного отката idle до нового прогона — ожидаемо, не «ошибка».
            continue

        filtered.append(item)
    return filtered


def finalize_divergence(divergence: dict[str, Any]) -> None:
    """Recompute summary and by_step after filtering items in-place."""
    items = divergence.get("items") or []
    dispatch = divergence.get("dispatch") or {}
    status = "ok"
    if any(item.get("severity") == SEVERITY_ERROR for item in items):
        status = "error"
    elif items:
        status = "warn"

    prev = divergence.get("summary") or {}
    divergence["items"] = items
    divergence["by_step"] = index_divergence_by_step(items)
    divergence["summary"] = {
        **prev,
        "status": status,
        "count": len(items),
        "message": _build_summary_message(items, dispatch, status),
    }


def index_divergence_by_step(items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_step: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        for step in item.get("related_steps") or _related_steps(item):
            by_step.setdefault(step, []).append(item)
    return by_step


def _build_summary_message(
    items: list[dict],
    dispatch: dict,
    status: str,
) -> str:
    if status == "ok":
        if dispatch.get("ready"):
            return "Расхождений нет — spec готов к сдаче."
        if dispatch.get("must_continue"):
            step = dispatch.get("next_step", "")
            sub = dispatch.get("next_subagent", "")
            return f"Следующий шаг по dispatch: {step} → {sub}"
        return dispatch.get("next_reason") or "Расхождений нет"

    kinds = {item.get("kind") for item in items}
    parts: list[str] = []
    if "stopped_early" in kinds:
        parts.append("пайплайн остановился, не дойдя до next step")
    if "live_subagent_mismatch" in kinds:
        parts.append("сейчас running не тот субагент")
    if "wrong_subagent_for_step" in kinds:
        parts.append("в истории есть шаг с неверным субагентом")
    if "order_violation" in kinds:
        parts.append("в истории есть нестандартные переходы")
    headline = "; ".join(parts) if parts else f"{len(items)} замечаний"
    next_bit = ""
    if dispatch.get("next_step"):
        next_bit = (
            f" Сейчас dispatch ждёт: `{dispatch['next_step']}`"
            f"{(' → `' + dispatch['next_subagent'] + '`') if dispatch.get('next_subagent') else ''}."
        )
    return f"Обнаружено: {headline}.{next_bit}"


def _schema_step_subagent(schema: dict, step: str) -> str | None:
    for node in schema.get("nodes", []):
        if node.get("id") == step:
            return node.get("subagent")
    return subagent_for_step(step)


def _allowed_targets(schema: dict, from_step: str) -> set[str]:
    targets: set[str] = set()
    for edge in schema.get("edges", []):
        if edge.get("from") == from_step:
            targets.add(edge["to"])
    return targets


def _is_allowed_transition(schema: dict, from_step: str, to_step: str) -> bool:
    if from_step == to_step:
        return True
    return to_step in _allowed_targets(schema, from_step)


def is_allowed_transition(schema: dict, from_step: str, to_step: str) -> bool:
    """Public wrapper for pipeline_delegate / PreToolUse graph gate.

    Only edges declared in ``pipeline_schema.json`` are allowed. Historical
    transitions that were previously whitelisted via ``SOFT_ORDER_PAIRS`` are
    now real graph edges in ``pipeline.yaml``.
    """
    return _is_allowed_transition(schema, from_step, to_step)


def run_log_has_ok(root: Path, slug: str, step: str) -> bool:
    """True when the run-log has a closed ok pass of `step` (any run)."""
    from pipeline_common import read_run_log

    for entry in reversed(read_run_log(root, slug)):
        if entry.get("step") == step and entry.get("result") == "ok":
            return True
    return False


def last_ok_pipeline_step(root: Path, slug: str) -> dict | None:
    """Last run-log row with result ok and a pipeline step.

    Orchestrator-owned steps (write-feature) are not subagent calls, so they have no
    canonical run-log row to anchor a transition on. When such a step already has a
    closed ok pass, it becomes the transition origin — otherwise the guard would
    compare an older step (find-context) against the step that follows it.
    """
    from pipeline_common import ORCHESTRATOR_OWNED_STEPS

    fallback: dict | None = None
    for entry in reversed(read_run_log(root, slug)):
        step = entry.get("step") or ""
        if entry.get("result") != "ok":
            continue
        if step and step in ORCHESTRATOR_OWNED_STEPS:
            if run_log_has_ok(root, slug, step):
                return entry
            continue
        if step:
            return entry
        if fallback is None:
            fallback = entry
    return fallback


def _dispatch_fingerprint(root: Path, slug: str) -> dict[str, float]:
    from artifact_paths import (
        alignment_path,
        challenges_map_path,
        challenges_path,
        context_doc_path,
        gaps_map_path,
        spec_path,
    )

    fp: dict[str, float] = {}
    for key, path_fn in (
        ("spec", spec_path),
        ("context", context_doc_path),
        ("gaps_map", gaps_map_path),
        ("challenges", challenges_path),
        ("challenges_map", challenges_map_path),
        ("alignment", alignment_path),
    ):
        path = path_fn(root, slug)
        fp[key] = path.stat().st_mtime if path.is_file() else 0.0
    return fp


def _step_closed_ok_in_run_log(history: list[dict], step: str) -> bool:
    latest: dict | None = None
    latest_ts = None
    for row in history:
        if row.get("step") != step:
            continue
        if (row.get("source") or "run-log") == "events":
            continue
        row_ts = row.get("ts")
        if latest is None or (row_ts and latest_ts and row_ts >= latest_ts):
            latest = row
            latest_ts = row_ts
    if not latest:
        return False
    result = latest.get("result") or "ok"
    return result not in ("fail", "retry")


def analyze_divergence(
    *,
    root: Path,
    slug: str,
    schema: dict,
    history: list[dict],
    current: dict | None,
    live: bool,
    pipeline: str,
    active_task: dict | None = None,
    log_next_step: str = "",
) -> dict[str, Any]:
    """Return dispatch snapshot + list of divergence records for the viewer."""
    if pipeline != "spec":
        return {
            "dispatch": None,
            "items": [],
            "summary": {"status": "n/a", "count": 0, "message": "Dispatch только для spec pipeline"},
        }

    dispatch = build_dispatch(root, slug)
    items: list[dict[str, Any]] = []

    expected_step = dispatch.get("next_step") or ""
    expected_subagent = dispatch.get("next_subagent") or ""
    must_continue = bool(dispatch.get("must_continue"))

    if current and current.get("status") == "running":
        actual_sub = current.get("subagent") or ""
        actual_step = current.get("step") or ""
        if expected_subagent and actual_sub and actual_sub != expected_subagent:
            items.append(
                _enrich_item(
                    {
                        "kind": "live_subagent_mismatch",
                        "severity": SEVERITY_ERROR,
                        "ts": current.get("since") or current.get("ts"),
                        "expected_step": expected_step,
                        "expected_subagent": expected_subagent,
                        "actual_step": actual_step,
                        "actual_subagent": actual_sub,
                        "message": (
                            f"Сейчас running `{actual_sub}` ({actual_step}), "
                            f"dispatch ждёт `{expected_subagent}` ({expected_step})"
                        ),
                    },
                    schema,
                    dispatch,
                )
            )
    elif (
        not live
        and must_continue
        and dispatch.get("orchestrator_mode") == "delegate"
        and (current or {}).get("status") != "next"
    ):
        last = history[-1] if history else None
        last_result = (last.get("result") if last else None) or "ok"
        if last_result not in ("fail", "retry"):
            items.append(
                _enrich_item(
                    {
                        "kind": "stopped_early",
                        "severity": SEVERITY_WARN,
                        "ts": last.get("ts") if last else None,
                        "expected_step": expected_step,
                        "expected_subagent": expected_subagent,
                        "actual_step": last.get("step") if last else None,
                        "actual_subagent": last.get("subagent") if last else None,
                        "message": (
                            f"Сессия idle, но dispatch: must_continue → "
                            f"`{expected_step}` → `{expected_subagent}`"
                        ),
                    },
                    schema,
                    dispatch,
                )
            )

    if log_next_step and expected_step and log_next_step != expected_step:
        items.append(
            _enrich_item(
                {
                    "kind": "dispatch_ahead_of_log",
                    "severity": SEVERITY_WARN,
                    "ts": None,
                    "expected_step": log_next_step,
                    "expected_subagent": subagent_for_step(log_next_step),
                    "actual_step": expected_step,
                    "actual_subagent": expected_subagent,
                    "message": (
                        f"run-log ждёт `{log_next_step}`, dispatch предлагает "
                        f"`{expected_step}` — viewer показывает run-log"
                    ),
                },
                schema,
                dispatch,
            )
        )

    if active_task and active_task.get("slug") == slug:
        task_step = active_task.get("step") or ""
        task_sub = active_task.get("subagent") or ""
        if task_step and not _step_closed_ok_in_run_log(history, task_step):
            items.append(
                _enrich_item(
                    {
                        "kind": "active_task_without_log",
                        "severity": SEVERITY_WARN,
                        "ts": active_task.get("started_at"),
                        "expected_step": expected_step,
                        "expected_subagent": expected_subagent,
                        "actual_step": task_step,
                        "actual_subagent": task_sub,
                        "message": (
                            f"active-task: `{task_sub}` ({task_step}), "
                            f"но в run-log шаг не закрыт. По логам следующий: "
                            f"`{expected_subagent}` ({expected_step})"
                        ),
                    },
                    schema,
                    dispatch,
                )
            )

    ordered = sorted(history, key=lambda row: row.get("ts") or "")
    prev_step: str | None = schema.get("orchestrator")
    for row in ordered:
        step = row.get("step") or ""
        subagent = row.get("subagent") or ""
        if not step:
            continue

        canonical_sub = _schema_step_subagent(schema, step)
        if subagent and canonical_sub and subagent != canonical_sub:
            items.append(
                _enrich_item(
                    {
                        "kind": "wrong_subagent_for_step",
                        "severity": SEVERITY_ERROR,
                        "ts": row.get("ts"),
                        "step": step,
                        "expected_subagent": canonical_sub,
                        "actual_subagent": subagent,
                        "message": (
                            f"{row.get('ts') or '—'}: шаг `{step}` через `{subagent}`, "
                            f"ожидался `{canonical_sub}`"
                        ),
                    },
                    schema,
                    dispatch,
                )
            )

        if prev_step and not _is_allowed_transition(schema, prev_step, step):
            pair = (prev_step, step)
            soft_note = SOFT_ORDER_PAIRS.get(pair)
            if soft_note and pair in {
                ("resolve-gaps", "check-feature"),
                ("resolve-challenges", "check-feature"),
                ("resolve-code-alignment", "check-feature-code"),
            }:
                pass
            else:
                items.append(
                    _enrich_item(
                        {
                            "kind": "order_violation",
                            "severity": SEVERITY_WARN,
                            "ts": row.get("ts"),
                            "from_step": prev_step,
                            "to_step": step,
                            "message": (
                                f"{row.get('ts') or '—'}: переход `{prev_step}` → `{step}` "
                                "не описан в схеме пайплайна"
                            ),
                        },
                        schema,
                        dispatch,
                    )
                )

        if prev_step and step != prev_step:
            prev_step = step
        elif not prev_step:
            prev_step = step

    status = "ok"
    if any(item["severity"] == SEVERITY_ERROR for item in items):
        status = "error"
    elif items:
        status = "warn"

    message = _build_summary_message(items, dispatch, status)

    return {
        "dispatch": dispatch,
        "items": items,
        "by_step": index_divergence_by_step(items),
        "kinds": KIND_META,
        "summary": {
            "status": status,
            "count": len(items),
            "message": message,
            "expected_step": expected_step,
            "expected_subagent": expected_subagent,
            "must_continue": must_continue,
            "orchestrator_mode": dispatch.get("orchestrator_mode"),
            "dispatch_reason": dispatch.get("next_reason"),
        },
        "step_to_subagent": STEP_TO_SUBAGENT,
        "fingerprint": _dispatch_fingerprint(root, slug),
    }


def main() -> None:
    import argparse
    import json

    from artifact_paths import resolve_slug, workspace_root
    from build_pipeline_graph import load_schema, merge_history, read_jsonl, resolve_viewer_run_id
    from agent_logs import events_path, run_log_path
    from build_pipeline_graph import collect_spawn_steps, infer_active_subagent, is_session_live

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slug")
    parser.add_argument("--run-id", default="auto")
    parser.add_argument("--root", default=".", type=Path)
    args = parser.parse_args()

    root = workspace_root(args.root)
    slug = resolve_slug(args.slug, root)
    if slug is None:
        raise SystemExit("slug not found")

    rid = resolve_viewer_run_id(root, slug, args.run_id)
    schema = load_schema()["pipelines"]["spec"]
    events = read_jsonl(events_path(root, slug, rid))
    run_log = read_jsonl(run_log_path(root, slug, rid))
    _, spawn_rows = collect_spawn_steps(events, schema)
    history = merge_history(run_log, spawn_rows)
    live = is_session_live(events)
    current = None
    if live:
        active = infer_active_subagent(events)
        if active:
            from build_pipeline_graph import subagent_to_step

            step = subagent_to_step(schema, active.get("subagent"))
            current = {
                "step": step,
                "subagent": active.get("subagent"),
                "since": active.get("ts"),
            }

    result = analyze_divergence(
        root=root,
        slug=slug,
        schema=schema,
        history=history,
        current=current,
        live=live,
        pipeline="spec",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

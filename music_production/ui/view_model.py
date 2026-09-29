"""Read-only screen model. It does not write journals or advance the graph."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Optional

from music_production.orchestration.engine import HUMAN_STEPS, OrchestrationEngine
from music_production.orchestration.state_store import read_json, read_jsonl

GATE_ACTIONS = {
    "PACKAGE_APPROVAL": (
        ("APPROVE_PACKAGE", "Утвердить пакет"),
        ("CHANGE_LYRICS", "Изменить текст"),
        ("CHANGE_PRODUCTION", "Изменить звучание"),
        ("STOP", "Остановить"),
    ),
    "REVISION_ESCALATION": (
        ("ACCEPT_REVISION", "Принять правку"),
        ("RETRY_REVISION", "Повторить правку"),
        ("ROLLBACK", "Откатить к родителю"),
        ("STOP", "Остановить"),
    ),
    "FINAL_APPROVAL": (
        ("APPROVE_FINAL", "Утвердить финал"),
        ("REQUEST_REVISION", "Запросить правку"),
        ("STOP", "Остановить"),
    ),
    "BASE_SELECTION": (
        ("SELECT_AS_BASE", "Выбрать базой"),
        ("REGENERATE_BATCH", "Сгенерировать заново"),
        ("COMBINE_DIRECTION", "Совместить направления"),
        ("CHANGE_LYRICS", "Изменить текст"),
        ("CHANGE_PRODUCTION", "Изменить звучание"),
        ("STOP", "Остановить"),
    ),
}

MOCK_AUDIO_MESSAGE = (
    "Mock URI: аудиобайты отсутствуют; прослушивание недоступно"
)
MOCK_QC_NOTICE = "mock, музыка не анализировалась"


def _token(payload: dict) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def decision_id_for(identity: dict) -> str:
    return "decision-" + _token(identity)[:32]


def audio_availability(track_dir: Path, audio_uri: object) -> dict:
    uri = audio_uri if isinstance(audio_uri, str) else ""
    if uri.startswith("mock://"):
        return {
            "audio_uri": uri,
            "audio_available": False,
            "audio_block_reason": "mock_uri",
        }
    if not _relative_audio_uri(uri):
        return {
            "audio_uri": uri,
            "audio_available": False,
            "audio_block_reason": "unavailable",
        }
    path = _audio_file(track_dir, uri)
    if path is None:
        return {
            "audio_uri": uri,
            "audio_available": False,
            "audio_block_reason": "unavailable",
        }
    return {
        "audio_uri": uri,
        "audio_available": True,
        "audio_block_reason": None,
    }


def _relative_audio_uri(uri: str) -> bool:
    if not uri or "://" in uri or uri.startswith(("/", "\\")):
        return False
    parts = Path(uri).parts
    return parts and ".." not in parts and not any("\\" in part or part in {".", ".."} for part in parts)


def _audio_file(track_dir: Path, uri: str) -> Optional[Path]:
    root = track_dir.resolve()
    candidate = (track_dir / uri)
    if candidate.is_symlink():
        return None
    try:
        resolved = candidate.resolve()
    except OSError:
        return None
    if resolved != root and root not in resolved.parents:
        return None
    if not resolved.is_file() or resolved.is_symlink():
        return None
    return resolved


def resolve_audio_file(track_dir: Path, audio_uri: str) -> Optional[Path]:
    if not _relative_audio_uri(audio_uri):
        return None
    return _audio_file(track_dir, audio_uri)


def _classify(engine: OrchestrationEngine) -> tuple[str, Optional[str], str]:
    decision = engine.dispatch()
    state = str(engine.state_store.load()["state"])
    if decision.ready:
        outcome = "DONE"
    elif decision.next_step in HUMAN_STEPS:
        outcome = "WAITING_FOR_HUMAN"
    elif decision.next_step == "paused" or state == "PAUSED":
        outcome = "BLOCKED"
    elif state == "FAILED":
        outcome = "FAILED"
    elif decision.stopped:
        outcome = "BLOCKED"
    else:
        outcome = "READY"
    return outcome, decision.next_step or None, str(decision.next_reason or "")


def _knowledge(engine: OrchestrationEngine) -> dict:
    path = engine.state_store.track_dir / "knowledge.json"
    if not path.is_file() or path.is_symlink():
        return {"captured_decision_ids": [], "cases": []}
    document = read_json(path)
    captured = document.get("captured_decision_ids")
    cases = document.get("cases")
    return {
        "captured_decision_ids": list(captured) if isinstance(captured, list) else [],
        "cases": list(cases) if isinstance(cases, list) else [],
    }


def _versions(engine: OrchestrationEngine) -> list[dict]:
    track_dir = engine.state_store.track_dir
    values = []
    for record in engine.handlers.versions.versions.values():
        item = {
            "version_id": record.version_id,
            "parent_version_id": record.parent_version_id,
            "operation": record.operation,
            "prompt_id": record.prompt_id,
            "checksum": record.checksum,
            "status": record.status,
            "provider_job_id": record.provider_job_id,
        }
        item.update(audio_availability(track_dir, record.audio_uri))
        values.append(item)
    values.sort(key=lambda item: item["version_id"])
    return values


def _lineage(versions: list[dict], version_id: Optional[str]) -> list[str]:
    by_id = {item["version_id"]: item for item in versions}
    chain = []
    seen = set()
    current = version_id
    while isinstance(current, str) and current and current not in seen:
        seen.add(current)
        chain.append(current)
        parent = (by_id.get(current) or {}).get("parent_version_id")
        current = parent if isinstance(parent, str) else None
    return chain


def _rollback_ids(versions: list[dict], current_id: Optional[str]) -> list[str]:
    by_id = {item["version_id"]: item for item in versions}
    current = by_id.get(current_id or "")
    parent = None if current is None else current.get("parent_version_id")
    if isinstance(parent, str) and parent:
        return [parent]
    return []


def _candidates(engine: OrchestrationEngine) -> list[dict]:
    document = engine.artifacts.latest("candidates") or {}
    raw = document.get("candidates")
    if not isinstance(raw, list):
        return []
    values = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        candidate_id = item.get("candidate_id")
        version_id = item.get("version_id")
        if not isinstance(candidate_id, str) or not isinstance(version_id, str):
            continue
        values.append(
            {
                "candidate_id": candidate_id,
                "version_id": version_id,
                **audio_availability(
                    engine.state_store.track_dir,
                    item.get("audio_uri"),
                ),
            }
        )
    return values


def _ab_pair(
    versions: list[dict],
    candidates: list[dict],
    comparison: dict,
    current_id: Optional[str],
    base_id: Optional[str],
) -> dict:
    parent = comparison.get("parent_version_id")
    child = comparison.get("child_version_id")
    if isinstance(parent, str) and isinstance(child, str):
        return {"left_version_id": parent, "right_version_id": child}
    if len(candidates) >= 2:
        return {
            "left_version_id": candidates[0]["version_id"],
            "right_version_id": candidates[1]["version_id"],
        }
    if len(candidates) == 1:
        return {
            "left_version_id": candidates[0]["version_id"],
            "right_version_id": base_id or current_id,
        }
    known = {item["version_id"] for item in versions}
    left = current_id if current_id in known else None
    right = base_id if base_id in known and base_id != left else None
    if right is None and isinstance(left, str):
        parent_id = next(
            (
                item.get("parent_version_id")
                for item in versions
                if item["version_id"] == left
            ),
            None,
        )
        if isinstance(parent_id, str):
            right = parent_id
    return {"left_version_id": left, "right_version_id": right}


def _jobs(engine: OrchestrationEngine) -> list[dict]:
    path = engine.state_store.track_dir / "jobs.json"
    if not path.is_file() or path.is_symlink():
        return []
    raw = read_json(path).get("jobs")
    return list(raw) if isinstance(raw, list) else []


def _expert_cases(engine: OrchestrationEngine) -> list[dict]:
    path = engine.state_store.track_dir / "expert-cases.jsonl"
    if not path.is_file() or path.is_symlink():
        return []
    return read_jsonl(path)


def _token_gate(engine: OrchestrationEngine, gate: Optional[str], captured: list) -> str:
    """Keep the token stable while a recorded decision waits for capture."""

    if gate:
        return gate
    pending = engine.decisions.current()
    pending_id = pending.get("decision_id")
    if isinstance(pending_id, str) and pending_id and pending_id not in captured:
        value = pending.get("gate")
        if isinstance(value, str):
            return value
    return ""


def open_gate(engine: OrchestrationEngine) -> Optional[str]:
    _outcome, step, _reason = _classify(engine)
    if step in HUMAN_STEPS:
        from music_production.orchestration.decisions import STEP_TO_GATE

        return STEP_TO_GATE[step]
    return None


def build_view_model(engine: OrchestrationEngine) -> dict:
    state = engine.state_store.load()
    outcome, step, reason = _classify(engine)
    knowledge = _knowledge(engine)
    captured = [item for item in knowledge["captured_decision_ids"] if isinstance(item, str)]
    gate = _token_gate(engine, open_gate(engine), captured) or None
    versions = _versions(engine)
    candidates = _candidates(engine)
    comparison = engine.artifacts.latest("version-comparison") or {}
    qc = engine.artifacts.latest("technical-qc") or {}
    request = engine.artifacts.latest("generation-request") or {}
    brief = engine.artifacts.latest("brief") or {}
    plan = engine.artifacts.latest("revision-plan") or {}
    edit = engine.artifacts.latest("edit-attempt") or {}
    defects = engine.artifacts.records("defect")
    decisions = engine.decisions.all()
    pending = engine.decisions.current()
    pending_id = str(pending.get("decision_id") or "")
    pending_status = None
    if pending_id:
        pending_status = "captured" if pending_id in captured else "pending"
    current_id = state.get("current_version_id")
    current_version = current_id if isinstance(current_id, str) else None
    actions = [
        {"verdict": verdict, "label": label}
        for verdict, label in GATE_ACTIONS.get(gate or "", ())
    ]
    token_payload = {
        "captured_decision_ids": sorted(captured),
        "gate": _token_gate(engine, gate, captured),
        "state": state,
    }
    qc_public = dict(qc)
    if qc_public.get("analyzer") == "mock":
        qc_public["mock_notice"] = MOCK_QC_NOTICE
    return {
        "track_id": engine.track_id,
        "state": state["state"],
        "current_version_id": current_version,
        "base_version_id": state.get("base_version_id"),
        "step": step,
        "gate": gate,
        "outcome": outcome,
        "reason": reason,
        "budget": {
            "brief": brief.get("budget") if isinstance(brief.get("budget"), dict) else None,
            "revision_budget_remaining": state["revision_budget_remaining"],
            "revision_iteration": state["revision_iteration"],
            "open_critical_defects": state["open_critical_defects"],
            "open_major_defects": state["open_major_defects"],
        },
        "jobs": _jobs(engine),
        "versions": versions,
        "lineage": _lineage(versions, current_version),
        "candidates": candidates,
        "ab": _ab_pair(
            versions,
            candidates,
            comparison,
            current_version,
            state.get("base_version_id") if isinstance(state.get("base_version_id"), str) else None,
        ),
        "defects": defects,
        "revision_plan": plan or None,
        "edit_attempt": edit or None,
        "version_comparison": comparison or None,
        "technical_qc": qc_public or None,
        "generation": {
            "prompt_id": request.get("prompt_id"),
            "operation": request.get("operation"),
            "parameters": {
                key: value
                for key, value in request.items()
                if key
                not in {
                    "schema_version",
                    "track_id",
                    "created_at",
                }
            },
        },
        "decisions": decisions,
        "captured_decision_ids": captured,
        "knowledge_cases": knowledge["cases"],
        "expert_cases": _expert_cases(engine),
        "pending_decision": pending or None,
        "pending_status": pending_status,
        "actions": actions,
        "references": {
            "song_package_version_id": (engine.artifacts.latest("song-package") or {}).get(
                "version_id"
            ),
            "candidate_ids": [item["candidate_id"] for item in candidates],
            "current_version_id": current_version,
            "rollback_version_ids": _rollback_ids(versions, current_version),
        },
        "view_token": _token(token_payload),
        "mock_audio_message": MOCK_AUDIO_MESSAGE,
        "mock_qc_notice": MOCK_QC_NOTICE,
    }


def same_decision_fields(stored: dict, proposed: dict) -> bool:
    keys = (
        "track_id",
        "decision_id",
        "gate",
        "verdict",
        "decided_by",
        "comment",
        "candidate_id",
        "version_id",
        "song_package_version_id",
    )
    for key in keys:
        if stored.get(key) != proposed.get(key):
            return False
    return True

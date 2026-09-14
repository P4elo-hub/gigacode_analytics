"""Predicate catalog: core (universal) + domain (per-pack registration)."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from pipeline_pack import DEFAULT_PIPELINE_ID, load_pack, load_pack_module

Predicate = Callable[[Path, str, object], bool]


def _field(status: object, name: str, default=None):
    return getattr(status, name, default)


def _not_has_artifact(field: str) -> Predicate:
    def pred(_root: Path, _task_id: str, status: object) -> bool:
        return not bool(_field(status, field, False))

    pred.__name__ = f"not_{field}"
    return pred


def _field_gt(field: str, threshold: int = 0) -> Predicate:
    def pred(_root: Path, _task_id: str, status: object) -> bool:
        value = _field(status, field, 0)
        try:
            return int(value) > threshold
        except (TypeError, ValueError):
            return False

    pred.__name__ = f"{field}_gt_{threshold}"
    return pred


def _pending_apply_in(field: str = "decisions_pending_apply") -> Predicate:
    return _field_gt(field, 0)


CORE_BUILDERS = {
    "file_missing": _not_has_artifact,
    "field_gt": _field_gt,
    "pending_apply": _pending_apply_in,
}


def core_predicates_from_status(status_spec: dict) -> dict[str, Predicate]:
    """Auto-register not_has_<artifact> from status.yaml artifacts."""
    preds: dict[str, Predicate] = {}
    artifacts = status_spec.get("artifacts") or {}
    for art_id, art in artifacts.items():
        if not isinstance(art, dict):
            continue
        exists_as = str(art.get("exists_as") or f"has_{art_id}")
        preds[f"not_has_{art_id}"] = _not_has_artifact(exists_as)
        preds[f"has_{art_id}"] = lambda r, t, s, f=exists_as: bool(_field(s, f, False))
        preds[f"file_missing_{art_id}"] = preds[f"not_has_{art_id}"]
    preds["field_gt"] = _field_gt("decisions_needs_answer", 0)
    preds["pending_apply"] = _pending_apply_in()
    return preds


def core_predicate_names() -> frozenset[str]:
    return frozenset(
        {
            "file_missing",
            "field_gt",
            "pending_apply",
            "not_has_context",
            "not_has_spec",
            "has_context",
            "has_spec",
        }
    )


def _domain_module(pipeline_id: str):
    return load_pack_module(pipeline_id, "predicates")


def catalog_names(pipeline_id: str = DEFAULT_PIPELINE_ID) -> frozenset[str]:
    names = set(core_predicate_names())
    try:
        status = load_pack(pipeline_id).get("status") or {}
    except FileNotFoundError:
        status = {}
    artifacts = status.get("artifacts") or {}
    for art_id in artifacts:
        names.add(f"not_has_{art_id}")
        names.add(f"has_{art_id}")
        names.add(f"file_missing_{art_id}")
    domain = _domain_module(pipeline_id)
    if domain is not None:
        declared = getattr(domain, "DOMAIN_PREDICATE_NAMES", None)
        if declared:
            names.update(declared)
        impl = getattr(domain, "PREDICATES", None)
        if isinstance(impl, dict):
            names.update(impl.keys())
    return frozenset(names)


def invariant_names(pipeline_id: str = DEFAULT_PIPELINE_ID) -> frozenset[str]:
    names = set()
    domain = _domain_module(pipeline_id)
    if domain is not None:
        declared = getattr(domain, "DOMAIN_INVARIANT_NAMES", None)
        if declared:
            names.update(declared)
    return frozenset(names) or frozenset({"needs-check-feature"})


def predicates_for(pipeline_id: str = DEFAULT_PIPELINE_ID) -> dict[str, Predicate]:
    try:
        status = load_pack(pipeline_id).get("status") or {}
    except FileNotFoundError:
        status = {}
    preds = core_predicates_from_status(status)
    domain = _domain_module(pipeline_id)
    if domain is not None:
        impl = getattr(domain, "PREDICATES", None)
        if isinstance(impl, dict):
            preds.update(impl)
    return preds


def reason_for(when: str, status: object, pipeline_id: str = DEFAULT_PIPELINE_ID) -> str:
    if when in {"not_has_context", "file_missing_context"}:
        return "нет проверенного контекста"
    if when in {"not_has_spec", "file_missing_spec"}:
        return "спецификация не написана"
    domain = _domain_module(pipeline_id)
    if domain is not None and hasattr(domain, "reason_for_predicate"):
        text = domain.reason_for_predicate(when, status)
        if text:
            return text
    return ""


def evaluate_invariant(
    inv_id: str,
    root: Path,
    task_id: str,
    status: object,
    pipeline_id: str = DEFAULT_PIPELINE_ID,
):
    domain = _domain_module(pipeline_id)
    if domain is not None and hasattr(domain, "evaluate_invariant"):
        return domain.evaluate_invariant(inv_id, root, task_id, status)
    return None

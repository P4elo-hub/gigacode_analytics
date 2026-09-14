"""Predicate catalog: core (from status.yaml) + domain (per-pack registration)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
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


def _has_artifact(field: str) -> Predicate:
    def pred(_root: Path, _task_id: str, status: object) -> bool:
        return bool(_field(status, field, False))

    pred.__name__ = str(field)
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
    "has_artifact": _has_artifact,
    "field_gt": _field_gt,
    "pending_apply": _pending_apply_in,
}


def _status_spec(pipeline_id: str) -> dict:
    try:
        return load_pack(pipeline_id).get("status") or {}
    except FileNotFoundError:
        return {}


def _core_cfg(status_spec: dict) -> dict:
    cfg = status_spec.get("core_predicates") or {}
    return cfg if isinstance(cfg, dict) else {}


def core_predicates_from_status(status_spec: dict) -> dict[str, Predicate]:
    """Auto-register artifact and counter predicates from status.yaml."""
    preds: dict[str, Predicate] = {}
    artifacts = status_spec.get("artifacts") or {}
    for art_id, art in artifacts.items():
        if not isinstance(art, dict):
            continue
        exists_as = str(art.get("exists_as") or f"has_{art_id}")
        preds[f"not_has_{art_id}"] = CORE_BUILDERS["file_missing"](exists_as)
        preds[f"has_{art_id}"] = CORE_BUILDERS["has_artifact"](exists_as)
        preds[f"file_missing_{art_id}"] = preds[f"not_has_{art_id}"]

    for item in _core_cfg(status_spec).get("counters") or []:
        if not isinstance(item, dict) or not item.get("field"):
            continue
        field = str(item["field"])
        threshold = int(item.get("gt", 0))
        builder = str(item.get("builder") or "field_gt")
        factory = CORE_BUILDERS.get(builder, CORE_BUILDERS["field_gt"])
        pred = factory(field, threshold) if builder == "field_gt" else factory(field)
        name = str(item.get("name") or f"{field}_gt_{threshold}")
        preds[name] = pred
        alias = item.get("alias")
        if alias:
            preds[str(alias)] = pred
    return preds


def core_predicate_names(pipeline_id: str | None = None) -> frozenset[str]:
    if pipeline_id:
        return frozenset(core_predicates_from_status(_status_spec(pipeline_id)))
    from pipeline_pack import discover_pipeline_ids

    names: set[str] = set()
    for pid in discover_pipeline_ids():
        names.update(core_predicates_from_status(_status_spec(pid)))
    return frozenset(names)


def _domain_module(pipeline_id: str):
    return load_pack_module(pipeline_id, "predicates")


def catalog_names(pipeline_id: str = DEFAULT_PIPELINE_ID) -> frozenset[str]:
    names = set(core_predicates_from_status(_status_spec(pipeline_id)))
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
    names: set[str] = set()
    for inv in _status_spec(pipeline_id).get("invariants") or []:
        if isinstance(inv, dict) and inv.get("id"):
            names.add(str(inv["id"]))
    domain = _domain_module(pipeline_id)
    if domain is not None:
        declared = getattr(domain, "DOMAIN_INVARIANT_NAMES", None)
        if declared:
            names.update(declared)
    return frozenset(names)


def predicates_for(pipeline_id: str = DEFAULT_PIPELINE_ID) -> dict[str, Predicate]:
    preds = core_predicates_from_status(_status_spec(pipeline_id))
    domain = _domain_module(pipeline_id)
    if domain is not None:
        impl = getattr(domain, "PREDICATES", None)
        if isinstance(impl, dict):
            preds.update(impl)
    return preds


def _core_reasons(status_spec: dict) -> dict[str, str]:
    reasons: dict[str, str] = {}
    for art_id, art in (status_spec.get("artifacts") or {}).items():
        if not isinstance(art, dict):
            continue
        msg = art.get("missing_reason")
        if msg:
            text = str(msg)
            reasons[f"not_has_{art_id}"] = text
            reasons[f"file_missing_{art_id}"] = text
    extra = _core_cfg(status_spec).get("reasons") or {}
    if isinstance(extra, dict):
        reasons.update({str(k): str(v) for k, v in extra.items()})
    messages = status_spec.get("messages") or {}
    pred_msgs = messages.get("predicates") if isinstance(messages, dict) else None
    if isinstance(pred_msgs, dict):
        reasons.update({str(k): str(v) for k, v in pred_msgs.items()})
    return reasons


def reason_for(when: str, status: object, pipeline_id: str = DEFAULT_PIPELINE_ID) -> str:
    domain = _domain_module(pipeline_id)
    if domain is not None and hasattr(domain, "reason_for_predicate"):
        text = domain.reason_for_predicate(when, status)
        if text:
            return text
    return _core_reasons(_status_spec(pipeline_id)).get(when, "") or ""


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


def _reason_probe_status() -> SimpleNamespace:
    return SimpleNamespace(
        decisions_needs_answer=0,
        decisions_needs_answer_alignment=0,
        decisions_pending_apply=0,
        decisions_pending_apply_alignment=0,
        open_gaps=[],
        challenges=SimpleNamespace(open=0),
    )


def validate_catalog(pipeline_id: str, dispatch: dict | None = None) -> list[str]:
    """Compile-time catalog checks: declared==impl, every when has reason."""
    errors: list[str] = []
    domain = _domain_module(pipeline_id)
    if domain is not None:
        declared = set(getattr(domain, "DOMAIN_PREDICATE_NAMES", None) or ())
        raw = getattr(domain, "PREDICATES", None)
        impl = raw if isinstance(raw, dict) else {}
        impl_keys = set(impl)
        missing = sorted(declared - impl_keys)
        extra = sorted(impl_keys - declared)
        if missing:
            errors.append(f"{pipeline_id}: DOMAIN_PREDICATE_NAMES missing implementations: {missing}")
        if extra:
            errors.append(f"{pipeline_id}: PREDICATES not declared in DOMAIN_PREDICATE_NAMES: {extra}")
        for name, fn in impl.items():
            if not callable(fn):
                errors.append(f"{pipeline_id}: predicate {name!r} is not callable")
        declared_inv = set(getattr(domain, "DOMAIN_INVARIANT_NAMES", None) or ())
        yaml_inv = {
            str(inv.get("id"))
            for inv in _status_spec(pipeline_id).get("invariants") or []
            if isinstance(inv, dict) and inv.get("id")
        }
        if declared_inv and yaml_inv and declared_inv != yaml_inv:
            errors.append(
                f"{pipeline_id}: DOMAIN_INVARIANT_NAMES ≠ status.yaml invariants: "
                f"{sorted(declared_inv)} vs {sorted(yaml_inv)}"
            )

    status_spec = _status_spec(pipeline_id)
    raw_core = status_spec.get("core_predicates")
    if raw_core not in (None, {}, []) and not isinstance(raw_core, dict):
        errors.append(f"{pipeline_id}: status.core_predicates must be a mapping")
    for item in _core_cfg(status_spec).get("counters") or []:
        if not isinstance(item, dict) or not item.get("field"):
            errors.append(f"{pipeline_id}: core_predicates.counters entry needs field")
            continue
        builder = str(item.get("builder") or "field_gt")
        if builder not in CORE_BUILDERS:
            errors.append(f"{pipeline_id}: unknown core builder {builder!r}")

    if not isinstance(dispatch, dict):
        return errors
    known = catalog_names(pipeline_id)
    implemented = predicates_for(pipeline_id)
    dummy = _reason_probe_status()
    for rule in dispatch.get("rules") or []:
        if not isinstance(rule, dict):
            continue
        when = rule.get("when")
        if not when or when not in known:
            continue
        if when not in implemented:
            errors.append(f"{pipeline_id}: dispatch when {when!r} has no implementation")
            continue
        try:
            text = reason_for(str(when), dummy, pipeline_id)
        except Exception as exc:  # noqa: BLE001 — compile must not crash on a bad reason
            errors.append(f"{pipeline_id}: reason_for({when!r}) failed: {exc}")
            continue
        if not str(text).strip():
            errors.append(f"{pipeline_id}: empty reason_for for when: {when!r}")
    return errors

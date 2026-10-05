"""Phase 13: declarative edge_conditions interpreter (choice A).

Formulas live in pipelines/<id>/routing_conditions.yaml. Runtime dispatch
stays deterministic — no LLM. Domain predicates.py is an optional custom
escape hatch.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

from pipeline_pack import load_pack, pack_folder

Predicate = Callable[[Path, str, object], bool]

ENGINE_FIELDS = frozenset(
    {"has_routing_state", "routing_state_invalid", "routing_state_error"}
)
CLAUSE_KEYS = frozenset(
    {"field", "op", "value", "other", "constant", "constants"}
)


def routing_conditions_path(pipeline_id: str, root: Path | None = None) -> Path:
    return pack_folder(pipeline_id, root) / "routing_conditions.yaml"


def load_routing_conditions(pipeline_id: str, root: Path | None = None) -> dict:
    path = routing_conditions_path(pipeline_id, root)
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore
    except ImportError:
        return _load_routing_conditions_simple(text)
    data = yaml.safe_load(text)
    return data if isinstance(data, dict) else {}


def _extract_top_level_section(text: str, key: str) -> str:
    lines = text.splitlines()
    start = None
    end = len(lines)
    for index, line in enumerate(lines):
        if line.startswith(f"{key}:") and (len(line) == len(key) + 1 or line[len(key) + 1 :].startswith(" ")):
            start = index
            continue
        if start is not None and index > start and line and line[0] not in " \t#" and ":" in line:
            end = index
            break
    if start is None:
        return ""
    return "\n".join(lines[start:end]) + "\n"


def _scan_status_fields(text: str) -> dict[str, dict]:
    fields: dict[str, dict] = {}
    section = ""
    current = ""
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if line == "status_fields:":
            section = "fields"
            continue
        if section == "fields" and line and not line.startswith(" "):
            break
        if section == "fields" and line.startswith("  ") and not line.startswith("    ") and line.endswith(":"):
            current = line.strip().rstrip(":")
            if current and not current.startswith("-"):
                fields[current] = {}
            continue
        if section == "fields" and current and line.startswith("    type:"):
            fields[current]["type"] = line.split(":", 1)[1].strip()
        if section == "fields" and current and line.startswith("    label:"):
            fields[current]["label"] = line.split(":", 1)[1].strip()
    return fields


def _load_routing_conditions_simple(text: str) -> dict:
    from spec_catalog import parse_simple_yaml

    out: dict = {"schema_version": 1, "status_fields": _scan_status_fields(text)}
    for key in ("edge_conditions", "engine_fields", "stale_vs", "validate_ids"):
        block = _extract_top_level_section(text, key)
        if not block.strip():
            continue
        parsed = parse_simple_yaml(block)
        if isinstance(parsed, dict) and key in parsed:
            out[key] = parsed[key]
        elif parsed is not None:
            out[key] = parsed
    return out


def edge_conditions_map(pipeline_id: str, root: Path | None = None) -> dict[str, dict]:
    block = load_routing_conditions(pipeline_id, root).get("edge_conditions") or {}
    if not isinstance(block, dict):
        return {}
    return {str(key): value for key, value in block.items() if isinstance(value, dict)}


def _constants_for(pipeline_id: str, root: Path | None = None) -> dict:
    try:
        pack = load_pack(pipeline_id, root)
    except FileNotFoundError:
        return {}
    raw = (pack.get("status") or {}).get("constants") or {}
    return dict(raw) if isinstance(raw, dict) else {}


def _resolve_path(status: object, path: str):
    current = status
    for part in str(path).split("."):
        if current is None:
            return None
        if isinstance(current, dict):
            current = current.get(part)
            continue
        current = getattr(current, part, None)
    return current


def _is_empty(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, (str, list, tuple, dict, set)):
        return len(value) == 0
    return False


def _as_number(value: object):
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        return value
    try:
        text = str(value).strip()
        if text == "":
            return None
        return int(text) if text.isdigit() or (text.startswith("-") and text[1:].isdigit()) else float(text)
    except (TypeError, ValueError):
        return None


def _rhs(clause: dict, status: object, constants: dict) -> object:
    if "other" in clause:
        return _resolve_path(status, str(clause["other"]))
    if "constant" in clause:
        return constants.get(clause["constant"])
    if "constants" in clause:
        names = clause["constants"] if isinstance(clause["constants"], list) else []
        return [constants.get(name) for name in names]
    return clause.get("value")


def _compare_numbers(left: object, right: object, op: str) -> bool:
    lv, rv = _as_number(left), _as_number(right)
    if lv is None or rv is None or isinstance(lv, bool) or isinstance(rv, bool):
        try:
            if op == "gt":
                return left > right  # type: ignore[operator]
            if op == "gte":
                return left >= right  # type: ignore[operator]
            if op == "lt":
                return left < right  # type: ignore[operator]
            if op == "lte":
                return left <= right  # type: ignore[operator]
        except TypeError:
            return False
        return False
    if op == "gt":
        return lv > rv
    if op == "gte":
        return lv >= rv
    if op == "lt":
        return lv < rv
    if op == "lte":
        return lv <= rv
    return False


def evaluate_clause(clause: dict, status: object, constants: dict | None = None) -> bool:
    const = constants or {}
    op = str(clause.get("op") or "")
    if op == "always":
        return bool(clause.get("value", True))
    field = str(clause.get("field") or "")
    left = _resolve_path(status, field) if field else None
    right = _rhs(clause, status, const)
    if op == "truthy":
        return bool(left)
    if op == "falsy":
        return not bool(left)
    if op == "empty":
        return _is_empty(left)
    if op == "non_empty":
        return not _is_empty(left)
    if op == "eq":
        return left == right
    if op == "neq":
        return left != right
    if op in {"gt", "gte", "lt", "lte"}:
        return _compare_numbers(left, right, op)
    if op == "contains":
        try:
            return right in left  # type: ignore[operator]
        except TypeError:
            return False
    if op == "in":
        try:
            return left in right  # type: ignore[operator]
        except TypeError:
            return False
    raise ValueError(f"unknown edge_conditions op: {op!r}")


def evaluate_edge_condition(
    expr: object,
    status: object,
    *,
    constants: dict | None = None,
    conditions: dict[str, dict] | None = None,
    _stack: tuple[str, ...] = (),
) -> bool:
    """Evaluate a declarative expr against a status object."""
    const = constants or {}
    conds = conditions or {}
    if isinstance(expr, bool):
        return expr
    if not isinstance(expr, dict):
        raise ValueError(f"edge condition expr must be a mapping, got {type(expr).__name__}")
    if "always" in expr and not (CLAUSE_KEYS & expr.keys()):
        return bool(expr["always"])
    if "all" in expr:
        items = expr["all"] if isinstance(expr["all"], list) else []
        return all(
            evaluate_edge_condition(item, status, constants=const, conditions=conds, _stack=_stack)
            for item in items
        )
    if "any" in expr:
        items = expr["any"] if isinstance(expr["any"], list) else []
        return any(
            evaluate_edge_condition(item, status, constants=const, conditions=conds, _stack=_stack)
            for item in items
        )
    if "not" in expr:
        return not evaluate_edge_condition(
            expr["not"], status, constants=const, conditions=conds, _stack=_stack
        )
    if "ref" in expr:
        name = str(expr["ref"])
        if name in _stack:
            raise ValueError(f"edge_conditions ref cycle: {' → '.join(_stack + (name,))}")
        other = conds.get(name) or {}
        result = evaluate_edge_condition(
            other.get("expr"),
            status,
            constants=const,
            conditions=conds,
            _stack=_stack + (name,),
        )
        if expr.get("negate") or str(expr.get("op") or "") == "not":
            return not result
        return result
    return evaluate_clause(expr, status, const)


def collect_field_refs(expr: object) -> set[str]:
    refs: set[str] = set()
    if not isinstance(expr, dict):
        return refs
    if "all" in expr and isinstance(expr["all"], list):
        for item in expr["all"]:
            refs |= collect_field_refs(item)
    if "any" in expr and isinstance(expr["any"], list):
        for item in expr["any"]:
            refs |= collect_field_refs(item)
    if "not" in expr:
        refs |= collect_field_refs(expr["not"])
    if expr.get("field"):
        refs.add(str(expr["field"]).split(".", 1)[0])
    if expr.get("other"):
        refs.add(str(expr["other"]).split(".", 1)[0])
    return refs


def dispatch_rules_from_edge_conditions(edge_conditions: dict[str, dict]) -> list[dict]:
    rules: list[dict] = []
    for name, spec in edge_conditions.items():
        disp = spec.get("dispatch")
        if not isinstance(disp, dict) or "priority" not in disp:
            continue
        try:
            priority = int(disp["priority"])
        except (TypeError, ValueError):
            continue
        rule: dict[str, Any] = {"priority": priority, "when": name, "next": disp.get("next")}
        if disp.get("outcome"):
            rule["outcome"] = disp["outcome"]
        rules.append(rule)
    rules.sort(key=lambda item: int(item["priority"]))
    return rules


def _make_predicate(name: str, spec: dict, conditions: dict[str, dict], constants: dict) -> Predicate:
    expr = spec.get("expr")

    def pred(_root: Path, _task_id: str, status: object) -> bool:
        return evaluate_edge_condition(expr, status, constants=constants, conditions=conditions)

    pred.__name__ = name
    pred.__qualname__ = name
    return pred


@lru_cache(maxsize=16)
def predicates_from_edge_conditions(
    pipeline_id: str,
    root: str | None = None,
    include_core: bool = False,
) -> dict[str, Predicate]:
    base = Path(root) if root else None
    conditions = edge_conditions_map(pipeline_id, base)
    constants = _constants_for(pipeline_id, base)
    preds: dict[str, Predicate] = {}
    for name, spec in conditions.items():
        if spec.get("core") and not include_core:
            continue
        if name.startswith("_"):
            continue
        preds[name] = _make_predicate(name, spec, conditions, constants)
    return preds


def reason_from_edge_condition(when: str, status: object, pipeline_id: str, root: Path | None = None) -> str:
    spec = edge_conditions_map(pipeline_id, root).get(when) or {}
    text = spec.get("reason")
    return str(text) if text else ""


def allowed_expr_fields(pipeline_id: str, root: Path | None = None) -> set[str]:
    allowed = set(ENGINE_FIELDS)
    rc = load_routing_conditions(pipeline_id, root)
    fields = rc.get("status_fields") or {}
    if isinstance(fields, dict):
        allowed.update(str(key) for key in fields)
    extra = rc.get("engine_fields") or []
    if isinstance(extra, list):
        allowed.update(str(item) for item in extra)
    try:
        status = load_pack(pipeline_id, root).get("status") or {}
    except FileNotFoundError:
        status = {}
    artifacts = status.get("artifacts") or {}
    if isinstance(artifacts, dict):
        for art_id, art in artifacts.items():
            if not isinstance(art, dict):
                continue
            allowed.add(str(art.get("exists_as") or f"has_{art_id}"))
    return allowed


def validate_edge_conditions(pipeline_id: str, dispatch: dict | None, root: Path | None = None) -> list[str]:
    """Compile-time: field refs, unique priorities, when: coverage, graph condition ids."""
    conditions = edge_conditions_map(pipeline_id, root)
    if not conditions:
        return []
    errors: list[str] = []
    allowed = allowed_expr_fields(pipeline_id, root)
    priorities: dict[int, str] = {}
    for name, spec in conditions.items():
        expr = spec.get("expr")
        if expr is None:
            errors.append(f"{pipeline_id}: edge_conditions.{name} missing expr")
            continue
        try:
            unknown = sorted(collect_field_refs(expr) - allowed)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{pipeline_id}: edge_conditions.{name} field-ref scan failed: {exc}")
            unknown = []
        if unknown:
            errors.append(f"{pipeline_id}: edge_conditions.{name} unknown fields: {unknown}")
        disp = spec.get("dispatch") if isinstance(spec.get("dispatch"), dict) else None
        if disp and "priority" in disp:
            try:
                priority = int(disp["priority"])
            except (TypeError, ValueError):
                errors.append(f"{pipeline_id}: edge_conditions.{name} dispatch.priority must be int")
                continue
            other = priorities.get(priority)
            if other:
                errors.append(f"{pipeline_id}: duplicate edge_conditions priority {priority} ({other}, {name})")
            else:
                priorities[priority] = name
    if isinstance(dispatch, dict):
        from pipeline_predicates import core_predicate_names

        core = core_predicate_names(pipeline_id)
        for rule in dispatch.get("rules") or []:
            if not isinstance(rule, dict):
                continue
            when = rule.get("when")
            if not when:
                continue
            if when not in conditions and when not in core:
                errors.append(
                    f"{pipeline_id}: dispatch when {when!r} has no edge_conditions or core catalog entry"
                )
        expected = dispatch_rules_from_edge_conditions(conditions)
        actual = []
        for rule in dispatch.get("rules") or []:
            if not isinstance(rule, dict) or not rule.get("when"):
                continue
            item = {"priority": int(rule["priority"]), "when": rule["when"], "next": rule.get("next")}
            if rule.get("outcome"):
                item["outcome"] = rule["outcome"]
            actual.append(item)
        actual.sort(key=lambda item: int(item["priority"]))
        if expected != actual:
            errors.append(
                f"{pipeline_id}: dispatch.rules ≠ edge_conditions.dispatch — "
                "run PYTHONPATH=scripts python3 scripts/pipeline_routing_codegen.py "
                f"--pipeline {pipeline_id} --apply"
            )
    try:
        graph = load_pack(pipeline_id, root).get("graph") or {}
    except FileNotFoundError:
        graph = {}
    for edge in graph.get("edges") or []:
        if not isinstance(edge, dict):
            continue
        cond = edge.get("condition")
        if cond and cond not in conditions:
            errors.append(
                f"{pipeline_id}: graph edge {edge.get('id')} condition {cond!r} not in edge_conditions"
            )
    return errors

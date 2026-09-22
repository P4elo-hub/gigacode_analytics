"""Phase 6 HTTP helpers: assemble overlay pack, validate without disk, apply, init.

Thin wrappers around pipeline_compile / pack_authoring / routing codegen.
Does not edit collectors.py, validate.py, agent markdown, or expr formulas.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

from pipeline_compile import (
    REGISTRY_PATH,
    SCHEMA_PATH,
    _validate_pack_registry,
    compile_outputs,
    merge_compiled_source,
    validate_source,
)
from pipeline_pack import (
    _clear_pack_loader_caches,
    apply_pack_json,
    discover_pipeline_ids,
    export_pack_json,
    load_yaml,
    packs_dir,
)
from pipeline_pack_authoring import (
    PACK_ID_RE,
    init_pack,
    init_pack_golden_hints,
    normalize_pack_payload,
    validate_pack_json,
)
from pipeline_predicates import catalog_names, core_predicate_names

INIT_TEMPLATES = ("routing-state", "full-dispatch", "orchestrator-only")
CLI_AGENT_DIRS = (".qwen", ".gigacode", ".opencode")
NODE_KEYS = ("id", "label", "kind", "subagent", "ask", "cycle")
EDGE_KEYS = (
    "id",
    "from",
    "to",
    "kind",
    "label",
    "condition",
    "condition_label",
    "conditions",
    "condition_labels",
)
CYCLE_KEYS = ("persistent", "assemble", "param", "folder", "out", "item_file", "close", "calls", "ask_queue")
CALL_KEYS = ("agent", "param", "skills", "check", "label", "sections")

_WHEN_RE = re.compile(r"unknown when:\s*'([^']+)'")
_EDGE_RE = re.compile(r"edge\s+(\S+)\s+")
_PRIORITY_RE = re.compile(r"duplicate priority:\s*(\d+)")
_NEXT_RE = re.compile(r"invalid next:\s*'([^']+)'")
_STEP_RE = re.compile(r"(?:registry step|orchestrator_owned step|restartable step)\s+(\S+)")
_GRAPH_EDGE_COND_RE = re.compile(r"graph edge\s+(\S+)\s+condition")


def _as_dict(value: object) -> dict:
    return dict(value) if isinstance(value, dict) else {}


def _as_list(value: object) -> list:
    return list(value) if isinstance(value, list) else []


def _semantic_equal(a: object, b: object) -> bool:
    return json.loads(json.dumps(a, sort_keys=True)) == json.loads(json.dumps(b, sort_keys=True))


def orchestrator_md_missing(pipeline_id: str, root: Path) -> list[str]:
    warnings: list[str] = []
    qwen = root / ".qwen" / "agents" / f"{pipeline_id}-orchestrator.md"
    if not qwen.is_file():
        warnings.append(
            f"нет файла оркестратора .qwen/agents/{pipeline_id}-orchestrator.md — "
            "Markdown агентов не генерируем, скопируйте шаблон вручную"
        )
    return warnings


_RU_TRANSLIT = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "i",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "kh",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "shch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}


def slug_when_id(text: str) -> str:
    raw = str(text or "").strip()
    if not raw:
        return ""
    compact = raw.replace("-", "_")
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", compact):
        return compact.lower()
    out: list[str] = []
    for char in raw.lower():
        if char in _RU_TRANSLIT:
            out.append(_RU_TRANSLIT[char])
        elif char.isascii() and char.isalnum():
            out.append(char)
        else:
            out.append("_")
    slug = re.sub(r"_+", "_", "".join(out)).strip("_")
    return slug or "when_custom"


def invent_condition_id(text: str, taken: set[str]) -> str:
    """Invent status_field / when: id. Free Russian → has_<slug>; bare ids kept as-is."""
    raw = str(text or "").strip()
    if not raw:
        return ""
    compact = raw.replace("-", "_")
    # Already an id — never invent a _2 sibling; caller dedupes via seen.
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", compact):
        return compact.lower()
    slug = slug_when_id(raw)
    base = slug if slug.startswith("has_") or slug.startswith("not_has_") else f"has_{slug}"
    if len(base) > 56:
        base = base[:56].rstrip("_") or "has_custom"
    if not re.match(r"^[a-z]", base):
        base = f"has_{base}"
    candidate = base
    n = 2
    while candidate in taken:
        suffix = f"_{n}"
        candidate = f"{base[: 56 - len(suffix)]}{suffix}"
        n += 1
    return candidate


def edge_when_pairs(edge: dict) -> list[tuple[str, str]]:
    """(when_id, instruction). instruction — русский текст со стрелки; id придумываем сами."""
    pairs: list[tuple[str, str]] = []
    seen: set[str] = set()
    labels = _as_dict(edge.get("condition_labels"))

    def looks_like_id(value: str) -> bool:
        return bool(re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", value.replace("-", "_")))

    def add(raw: object, label: object = "") -> None:
        text = str(raw or "").strip()
        human = str(label or "").strip()
        if not text and not human:
            return
        if text and looks_like_id(text):
            sid = invent_condition_id(text, seen)
            instruction = human or str(labels.get(sid) or "") or text
        elif human and not looks_like_id(human):
            instruction = human
            sid = invent_condition_id(human, seen)
        elif text and not looks_like_id(text):
            instruction = text
            sid = invent_condition_id(text, seen)
        else:
            sid = invent_condition_id(text or human, seen)
            instruction = human or str(labels.get(sid) or "") or (text if text != sid else sid)
        if not sid or sid in seen:
            return
        seen.add(sid)
        pairs.append((sid, instruction or sid))

    add(edge.get("condition"), edge.get("condition_label") or labels.get(str(edge.get("condition") or "")))
    for item in _as_list(edge.get("conditions")):
        if isinstance(item, str):
            add(item, labels.get(item, ""))
        elif isinstance(item, dict):
            add(item.get("id") or item.get("label"), item.get("label") or item.get("instruction"))
    return pairs


def edge_condition_ids(edge: dict) -> list[str]:
    return [sid for sid, _ in edge_when_pairs(edge)]


def sanitize_graph(graph: object) -> dict:
    src = _as_dict(graph)
    nodes: list[dict] = []
    for raw in src.get("nodes") or []:
        if not isinstance(raw, dict) or not raw.get("id"):
            continue
        node = {key: copy.deepcopy(raw[key]) for key in NODE_KEYS if key in raw}
        if raw.get("subagent") is None and "subagent" in raw:
            node["subagent"] = None
        if node.get("kind") not in {"orchestrator", "step", "terminal", "meta"}:
            node["kind"] = "step"
        if node.get("ask"):
            node["ask"] = True
        else:
            node.pop("ask", None)
        cycle = node.get("cycle")
        if isinstance(cycle, dict):
            clean_cycle = {key: copy.deepcopy(cycle[key]) for key in CYCLE_KEYS if key in cycle}
            if isinstance(clean_cycle.get("calls"), list):
                calls = []
                for call in clean_cycle["calls"]:
                    if not isinstance(call, dict):
                        continue
                    item = {key: copy.deepcopy(call[key]) for key in CALL_KEYS if key in call and call[key] not in (None, "", [])}
                    if item.get("agent") or item.get("param"):
                        calls.append(item)
                if calls:
                    clean_cycle["calls"] = calls
                else:
                    clean_cycle.pop("calls", None)
            if "close" not in clean_cycle:
                clean_cycle["close"] = "on_done"
            node["cycle"] = clean_cycle
        else:
            node.pop("cycle", None)
        nodes.append(node)

    edges: list[dict] = []
    for raw in src.get("edges") or []:
        if not isinstance(raw, dict) or not raw.get("from") or not raw.get("to"):
            continue
        edge = {key: raw[key] for key in EDGE_KEYS if key in raw and raw[key] not in (None, "")}
        pairs = edge_when_pairs(raw if isinstance(raw, dict) else {})
        ids = [sid for sid, _ in pairs]
        labels = {sid: human for sid, human in pairs if human}
        if ids:
            edge["condition"] = ids[0]
            if len(ids) > 1:
                edge["conditions"] = ids
            else:
                edge.pop("conditions", None)
            if labels.get(ids[0]):
                edge["condition_label"] = labels[ids[0]]
            if labels:
                edge["condition_labels"] = labels
        else:
            edge.pop("condition", None)
            edge.pop("conditions", None)
            edge.pop("condition_label", None)
            edge.pop("condition_labels", None)
        edges.append(edge)

    out = {
        "label": str(src.get("label") or "").strip() or "pipeline",
        "orchestrator": str(src.get("orchestrator") or "").strip(),
        "nodes": nodes,
        "edges": edges,
    }
    if not out["orchestrator"]:
        for node in nodes:
            if node.get("kind") == "orchestrator":
                out["orchestrator"] = str(node["id"])
                break
    return out


def sanitize_rules(rules: object) -> list[dict]:
    out: list[dict] = []
    for raw in _as_list(rules):
        if not isinstance(raw, dict):
            continue
        raw_when = str(raw.get("when") or "").strip()
        when = slug_when_id(raw_when) or raw_when
        if not when:
            continue
        item: dict[str, Any] = {"when": when}
        try:
            item["priority"] = int(raw.get("priority"))
        except (TypeError, ValueError):
            item["priority"] = raw.get("priority")
        nxt = raw.get("next")
        if nxt in ("", None):
            item["next"] = None
        else:
            item["next"] = str(nxt)
        outcome = str(raw.get("outcome") or "").strip()
        if outcome in {"ready", "stopped"}:
            item["outcome"] = outcome
        out.append(item)
    seen: set[str] = set()
    unique: list[dict] = []
    for item in sorted(out, key=lambda row: (isinstance(row.get("priority"), int) is False, row.get("priority") or 0)):
        when = item.get("when")
        if when in seen:
            continue
        seen.add(str(when))
        unique.append(item)
    return unique


def registry_from_graph(graph: dict, previous: dict | None = None) -> dict:
    prev = _as_dict(previous)
    prev_map = _as_dict(prev.get("step_to_subagent"))
    prev_owned = [str(x) for x in _as_list(prev.get("orchestrator_owned"))]
    prev_gated = [str(x) for x in _as_list(prev.get("gated_subagents"))]
    prev_restart = [str(x) for x in _as_list(prev.get("restartable_steps"))]
    prev_modes = _as_dict(prev.get("delegate_modes"))

    step_to: dict[str, str] = {}
    owned: list[str] = []
    restart: list[str] = []
    current_subs: list[str] = []

    for node in graph.get("nodes") or []:
        if not isinstance(node, dict) or not node.get("id"):
            continue
        nid = str(node["id"])
        kind = node.get("kind") or "step"
        if kind in {"orchestrator", "terminal", "meta"}:
            continue
        restart.append(nid)
        has_cycle = isinstance(node.get("cycle"), dict)
        sub = node.get("subagent")
        sub_s = str(sub).strip() if sub else ""
        if has_cycle or not sub_s:
            owned.append(nid)
            if sub_s:
                current_subs.append(sub_s)
        elif sub_s:
            step_to[nid] = sub_s
            current_subs.append(sub_s)

    owned_set = set(owned)
    restart_set = set(restart)
    owned = [sid for sid in prev_owned if sid in owned_set] + [sid for sid in owned if sid not in set(prev_owned)]
    restart = [sid for sid in prev_restart if sid in restart_set] + [
        sid for sid in restart if sid not in set(prev_restart)
    ]

    current_sub_set = set(current_subs)
    gated = [name for name in prev_gated if name in current_sub_set]
    prev_subs = set(prev_map.values())
    if not prev_gated and not prev_map:
        gated = []
        seen: set[str] = set()
        for name in current_subs:
            if name not in seen:
                gated.append(name)
                seen.add(name)
    else:
        for name in step_to.values():
            if name not in prev_subs and name not in gated:
                gated.append(name)

    node_ids = {str(node.get("id")) for node in (graph.get("nodes") or []) if isinstance(node, dict) and node.get("id")}
    modes: dict[str, Any] = {}
    for name, block in prev_modes.items():
        if isinstance(block, dict) and str(block.get("step") or "") in node_ids:
            modes[str(name)] = copy.deepcopy(block)
    for node in graph.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        cycle = node.get("cycle") if isinstance(node.get("cycle"), dict) else None
        if not cycle:
            continue
        assemble = str(cycle.get("assemble") or "")
        if assemble == "write_feature" and "write_feature_cycle" not in modes:
            modes["write_feature_cycle"] = {
                "step": str(node.get("id") or ""),
                "subagent": str(node.get("subagent") or "spec-writer"),
                "persistent": cycle.get("persistent") is not False,
            }

    out = {
        "step_to_subagent": step_to,
        "orchestrator_owned": owned,
        "gated_subagents": gated,
        "restartable_steps": restart,
    }
    if modes:
        out["delegate_modes"] = modes
    return out


def _known_when_names(payload: dict, root: Path) -> set[str]:
    pack_id = str(payload.get("id") or "")
    names: set[str] = set()
    if pack_id:
        try:
            names.update(catalog_names(pack_id))
        except Exception:
            pass
        try:
            names.update(core_predicate_names(pack_id))
        except Exception:
            pass
    status = _as_dict(payload.get("status"))
    for art_id in _as_dict(status.get("artifacts")):
        names.add(f"not_has_{art_id}")
        names.add(f"file_missing_{art_id}")
    rc = _as_dict(payload.get("routing_conditions"))
    for cond_id in _as_dict(rc.get("edge_conditions")):
        if cond_id and not str(cond_id).startswith("_"):
            names.add(str(cond_id))
    for field_id in _as_dict(rc.get("status_fields")):
        if field_id and not str(field_id).startswith("_"):
            names.add(str(field_id))
    for edge in _as_list(_as_dict(payload.get("graph")).get("edges")):
        if isinstance(edge, dict):
            names.update(edge_condition_ids(edge))
    return names


def prune_orphan_dispatch(payload: dict) -> list[str]:
    node_ids = {
        str(node["id"])
        for node in _as_list(_as_dict(payload.get("graph")).get("nodes"))
        if isinstance(node, dict) and node.get("id")
    }
    notes: list[str] = []
    rc = dict(_as_dict(payload.get("routing_conditions")))
    conditions = dict(_as_dict(rc.get("edge_conditions")))
    for name, spec in list(conditions.items()):
        if not isinstance(spec, dict):
            continue
        disp = spec.get("dispatch") if isinstance(spec.get("dispatch"), dict) else None
        if not disp:
            continue
        nxt = disp.get("next")
        if nxt not in (None, "") and str(nxt) not in node_ids and str(nxt) not in {"ready", "stopped"}:
            notes.append(f"сняли edge_conditions.{name} → {nxt}: клетки нет на холсте")
            spec = dict(spec)
            spec.pop("dispatch", None)
            conditions[name] = spec
    if conditions != _as_dict(rc.get("edge_conditions")):
        rc["edge_conditions"] = conditions
        payload["routing_conditions"] = rc

    # SSOT: dispatch.rules = edge_conditions.dispatch (after orphan prune + before/after stubs)
    from pipeline_edge_conditions import dispatch_rules_from_edge_conditions

    rules = dispatch_rules_from_edge_conditions(conditions)
    dispatch = dict(_as_dict(payload.get("dispatch")))
    # Keep overlay rules that don't have edge_conditions yet — stubs will fill them.
    overlay = sanitize_rules(dispatch.get("rules"))
    have = {str(rule.get("when") or "") for rule in rules}
    for rule in overlay:
        when = str(rule.get("when") or "")
        if not when or when in have:
            continue
        nxt = rule.get("next")
        if nxt not in (None, "") and str(nxt) not in node_ids and str(nxt) not in {"ready", "stopped"}:
            notes.append(f"сняли {when} → {nxt}: клетки нет на холсте")
            continue
        rules.append(rule)
        have.add(when)
    dispatch["rules"] = sanitize_rules(rules)
    payload["dispatch"] = dispatch
    return notes


def reconcile_dispatch_rules(payload: dict) -> None:
    """Final sync: dispatch.rules must equal edge_conditions.dispatch for compile."""
    from pipeline_edge_conditions import dispatch_rules_from_edge_conditions

    rc = _as_dict(payload.get("routing_conditions"))
    conditions = _as_dict(rc.get("edge_conditions"))
    rules = dispatch_rules_from_edge_conditions(conditions)
    dispatch = dict(_as_dict(payload.get("dispatch")))
    dispatch["rules"] = sanitize_rules(rules)
    payload["dispatch"] = dispatch
    _sync_rc_dispatch(payload)


def _sync_rc_dispatch(payload: dict) -> None:
    """Align edge_conditions.dispatch with the overlay table. Never touch expr."""
    rc = payload.get("routing_conditions")
    if not isinstance(rc, dict):
        return
    conditions = rc.get("edge_conditions")
    if not isinstance(conditions, dict):
        return
    for rule in _as_list(_as_dict(payload.get("dispatch")).get("rules")):
        if not isinstance(rule, dict):
            continue
        when = str(rule.get("when") or "")
        spec = conditions.get(when)
        if not isinstance(spec, dict):
            continue
        disp = dict(spec.get("dispatch") or {}) if isinstance(spec.get("dispatch"), dict) else {}
        if "priority" in rule:
            try:
                disp["priority"] = int(rule["priority"])
            except (TypeError, ValueError):
                pass
        if "next" in rule:
            disp["next"] = rule.get("next")
        if rule.get("outcome"):
            disp["outcome"] = rule["outcome"]
        elif "outcome" in disp and rule.get("next"):
            disp.pop("outcome", None)
        spec["dispatch"] = disp


def _apply_codegen_stubs(payload: dict, missing_edges: list[dict]) -> list[str]:
    """From edge Russian text → status_fields.instruction + edge_conditions + dispatch.rules."""
    graph = _as_dict(payload.get("graph"))
    edges = [edge for edge in _as_list(graph.get("edges")) if isinstance(edge, dict)]
    if missing_edges:
        # Prefer the missing list (already filtered), but keep full edges for labels.
        by_id = {str(edge.get("id") or ""): edge for edge in edges}
        edges = []
        for item in missing_edges:
            if not isinstance(item, dict):
                continue
            eid = str(item.get("id") or "")
            edges.append({**(by_id.get(eid) or {}), **item})

    rc = dict(_as_dict(payload.get("routing_conditions")))
    fields = dict(_as_dict(rc.get("status_fields")))
    conditions = dict(_as_dict(rc.get("edge_conditions")))
    dispatch = dict(_as_dict(payload.get("dispatch")))
    rules = sanitize_rules(dispatch.get("rules"))
    have_when = {str(rule.get("when") or "") for rule in rules if rule.get("when")}
    used_pri: set[int] = set()
    for rule in rules:
        try:
            used_pri.add(int(rule.get("priority")))
        except (TypeError, ValueError):
            continue
    for spec in conditions.values():
        if not isinstance(spec, dict):
            continue
        disp = spec.get("dispatch") if isinstance(spec.get("dispatch"), dict) else {}
        try:
            used_pri.add(int(disp.get("priority")))
        except (TypeError, ValueError):
            continue
    cursor = (max(used_pri) + 10) if used_pri else 10
    taken_ids = set(fields) | {k for k in conditions if not str(k).startswith("_")} | have_when
    notes: list[str] = []

    for edge in edges:
        pairs = edge_when_pairs(edge)
        if not pairs:
            continue
        nxt, outcome = None, None
        # local import-free terminal next
        to_id = str(edge.get("to") or "")
        node_kinds = {
            str(node.get("id")): node.get("kind")
            for node in _as_list(graph.get("nodes"))
            if isinstance(node, dict) and node.get("id")
        }
        if to_id in {"done", "ready"} or node_kinds.get(to_id) == "terminal":
            nxt, outcome = None, "ready"
        else:
            nxt, outcome = to_id, None

        for cond_id, instruction in pairs:
            # Only invent status_fields for NEW field-backed conditions.
            # Existing edge_conditions (compound/core) already have expr — do not add a bool field.
            if cond_id not in conditions:
                if cond_id not in fields:
                    fields[cond_id] = {
                        "type": "bool",
                        "instruction": instruction,
                    }
                    notes.append(f"status_fields.{cond_id}: {instruction}")
                else:
                    prev = fields[cond_id]
                    if isinstance(prev, dict) and not str(prev.get("instruction") or "").strip():
                        prev["instruction"] = instruction

            if cond_id not in conditions:
                while cursor in used_pri:
                    cursor += 10
                pri = cursor
                used_pri.add(pri)
                cursor += 10
                disp: dict = {"priority": pri, "next": nxt}
                if outcome:
                    disp["outcome"] = outcome
                    disp["next"] = None
                conditions[cond_id] = {
                    "expr": {"field": cond_id, "op": "truthy"},
                    "dispatch": disp,
                    "label": instruction,
                    "reason": instruction,
                }
                notes.append(f"edge_conditions.{cond_id} P{pri} → {outcome or nxt}")
            else:
                # Do not overwrite existing expr
                spec = conditions[cond_id]
                if isinstance(spec, dict):
                    if not spec.get("label"):
                        spec["label"] = instruction
                    if not spec.get("reason"):
                        spec["reason"] = instruction

            if cond_id not in have_when:
                spec = conditions.get(cond_id) if isinstance(conditions.get(cond_id), dict) else {}
                disp = spec.get("dispatch") if isinstance(spec.get("dispatch"), dict) else {}
                try:
                    pri = int(disp.get("priority"))
                except (TypeError, ValueError):
                    while cursor in used_pri:
                        cursor += 10
                    pri = cursor
                    used_pri.add(pri)
                    cursor += 10
                rule = {"priority": pri, "when": cond_id, "next": disp.get("next", nxt)}
                if disp.get("outcome") or outcome:
                    rule["outcome"] = disp.get("outcome") or outcome
                    rule["next"] = None
                rules.append(rule)
                have_when.add(cond_id)
                notes.append(f"dispatch when:{cond_id} P{pri}")

            taken_ids.add(cond_id)

    # Rewrite graph edges to invented ids + keep Russian as condition_label
    new_edges = []
    for edge in _as_list(graph.get("edges")):
        if not isinstance(edge, dict):
            continue
        pairs = edge_when_pairs(edge)
        clean = dict(edge)
        if pairs:
            ids = [sid for sid, _ in pairs]
            label_map = {sid: human for sid, human in pairs}
            clean["condition"] = ids[0]
            clean["condition_label"] = label_map[ids[0]]
            if len(ids) > 1:
                clean["conditions"] = ids
            else:
                clean.pop("conditions", None)
            clean["condition_labels"] = label_map
        new_edges.append(clean)
    graph["edges"] = new_edges
    payload["graph"] = graph

    rc["status_fields"] = fields
    rc["edge_conditions"] = conditions
    if "schema_version" not in rc:
        rc["schema_version"] = 1
    payload["routing_conditions"] = rc
    dispatch["rules"] = sanitize_rules(rules)
    payload["dispatch"] = dispatch
    return notes


def stub_graph_whens(payload: dict) -> list[str]:
    """Always materialize authored edge texts into routing_conditions + dispatch."""
    return _apply_codegen_stubs(payload, [])


def locate_error(message: str, payload: dict | None = None) -> dict:
    item: dict[str, Any] = {"message": message}
    pack = payload or {}
    graph = _as_dict(pack.get("graph"))
    match = _EDGE_RE.search(message) or _GRAPH_EDGE_COND_RE.search(message)
    if match:
        item["edge"] = match.group(1)
    match = _WHEN_RE.search(message)
    if match:
        item["when"] = match.group(1)
        for rule in _as_list(_as_dict(pack.get("dispatch")).get("rules")):
            if isinstance(rule, dict) and str(rule.get("when") or "") == match.group(1):
                try:
                    item["priority"] = int(rule.get("priority"))
                except (TypeError, ValueError):
                    pass
                nxt = rule.get("next")
                if nxt:
                    item["node"] = str(nxt)
                break
    match = _PRIORITY_RE.search(message)
    if match:
        item["priority"] = int(match.group(1))
    match = _NEXT_RE.search(message)
    if match:
        item["node"] = match.group(1)
    match = _STEP_RE.search(message)
    if match:
        item["node"] = match.group(1).rstrip(".")
    if "graph.orchestrator" in message:
        item["node"] = str(graph.get("orchestrator") or "")
    return {key: value for key, value in item.items() if value not in (None, "")}


def authoring_overlay_errors(payload: dict, root: Path) -> list[dict]:
    errors: list[dict] = []
    graph = _as_dict(payload.get("graph"))
    nodes = [node for node in (graph.get("nodes") or []) if isinstance(node, dict) and node.get("id")]
    ids = {str(node["id"]) for node in nodes}
    orch = [node for node in nodes if node.get("kind") == "orchestrator"]
    if len(orch) != 1:
        errors.append(
            locate_error(
                "нужен ровно один оркестратор" if orch else "нет оркестратора — нужен ровно один",
                payload,
            )
        )
    rules = sanitize_rules(_as_dict(payload.get("dispatch")).get("rules"))
    when_in_rules = {str(rule.get("when") or "") for rule in rules if rule.get("when")}
    known = _known_when_names(payload, root)
    priorities: dict[int, str] = {}

    for rule in rules:
        when = str(rule.get("when") or "")
        loc = {"priority": rule.get("priority"), "when": when or None}
        if not when:
            errors.append({**{k: v for k, v in loc.items() if v not in (None, "")}, "message": "в таблице dispatch пустой when:"})
            continue
        if when not in known:
            errors.append(
                {
                    **{k: v for k, v in loc.items() if v not in (None, "")},
                    "message": f"нет в каталоге when: {when}",
                }
            )
        try:
            priority = int(rule.get("priority"))
        except (TypeError, ValueError):
            errors.append({**{k: v for k, v in loc.items() if v not in (None, "")}, "message": f"priority должен быть числом: {when}"})
            continue
        if priority in priorities:
            errors.append({"priority": priority, "when": when, "message": f"duplicate priority: {priority}"})
        else:
            priorities[priority] = when
        nxt = rule.get("next")
        outcome = rule.get("outcome")
        if nxt in (None, "") and outcome not in {"ready", "stopped"}:
            errors.append({**{k: v for k, v in loc.items() if v not in (None, "")}, "message": f"next=null требует outcome ready|stopped: {when}"})
        elif nxt not in (None, "") and str(nxt) not in ids and str(nxt) not in {"ready", "stopped"}:
            errors.append({"priority": priority, "when": when, "node": str(nxt), "message": f"next {nxt} нет на холсте"})

    for edge in graph.get("edges") or []:
        if not isinstance(edge, dict):
            continue
        eid = str(edge.get("id") or f"{edge.get('from')}→{edge.get('to')}")
        src, dst = str(edge.get("from") or ""), str(edge.get("to") or "")
        if src not in ids or dst not in ids:
            errors.append({"edge": eid, "message": f"ребро {eid} в пустоту (from/to должны быть клетками)"})
        for cond in edge_condition_ids(edge):
            if cond not in known:
                errors.append({"edge": eid, "when": cond, "message": f"нет в каталоге when: {cond}"})
            elif cond not in when_in_rules:
                errors.append(
                    {
                        "edge": eid,
                        "when": cond,
                        "message": f"для {cond} нет строки в таблице dispatch",
                    }
                )
    return errors


def assemble_pack_payload(body: dict, root: Path, *, codegen: bool = False) -> tuple[dict, list[dict], list[str]]:
    """base = export-json | init result; overlay graph + dispatch.rules; recompute registry."""
    data = normalize_pack_payload(body if isinstance(body, dict) else {})
    pack_id = str(data.get("id") or "").strip()
    if not pack_id:
        raise ValueError("id пака обязателен")
    known = set(discover_pipeline_ids(root))
    if pack_id not in known:
        raise FileNotFoundError(
            f"unknown pack: {pack_id} — сначала «Новый пак» (--init-pack), пустой холст в --from-json нельзя"
        )
    base = export_pack_json(pack_id, root)
    payload = copy.deepcopy(base)
    payload["id"] = pack_id
    if data.get("graph"):
        graph = sanitize_graph(data["graph"])
        if not graph.get("label"):
            graph["label"] = str(_as_dict(base.get("graph")).get("label") or pack_id)
        payload["graph"] = graph
    overlay_rules = None
    if isinstance(data.get("dispatch"), dict) and "rules" in data["dispatch"]:
        overlay_rules = data["dispatch"].get("rules")
    elif "dispatch_rules" in data:
        overlay_rules = data.get("dispatch_rules")
    if overlay_rules is not None:
        dispatch = dict(_as_dict(payload.get("dispatch")))
        dispatch["rules"] = sanitize_rules(overlay_rules)
        payload["dispatch"] = dispatch
    payload["registry"] = registry_from_graph(payload.get("graph") or {}, _as_dict(base.get("registry")))
    # status + routing_conditions.expr stay from disk base
    payload["status"] = copy.deepcopy(base.get("status") or {})
    if base.get("routing_conditions"):
        payload["routing_conditions"] = copy.deepcopy(base["routing_conditions"])
    else:
        payload.pop("routing_conditions", None)

    notes: list[str] = []
    notes.extend(prune_orphan_dispatch(payload))
    notes.extend(stub_graph_whens(payload))
    reconcile_dispatch_rules(payload)
    errors = authoring_overlay_errors(payload, root)
    return payload, errors, notes


def _overlay_compile_data(payload: dict, root: Path) -> dict:
    data = merge_compiled_source(root)
    pack_id = str(payload.get("id") or "")
    data.setdefault("pipelines", {})[pack_id] = copy.deepcopy(payload.get("graph") or {})
    data.setdefault("registries", {})[pack_id] = copy.deepcopy(payload.get("registry") or {})
    data.setdefault("dispatch", {})[pack_id] = copy.deepcopy(payload.get("dispatch") or {})
    data.setdefault("status", {})[pack_id] = copy.deepcopy(payload.get("status") or {})
    return data


def _layer1_errors(payload: dict) -> list[dict]:
    return [locate_error(msg, payload) for msg in validate_pack_json(payload)]


def _layer2_errors(payload: dict, root: Path) -> list[dict]:
    data = _overlay_compile_data(payload, root)
    raw = validate_source(data)
    skip_prefix = f"{payload.get('id')}:"
    mapped: list[dict] = []
    for msg in raw:
        if not msg.startswith(skip_prefix):
            mapped.append(locate_error(msg, payload))
            continue
        # Disk-backed edge_conditions (validate_edge_conditions loads YAML).
        # Authoring validate uses in-memory RC below — skip stale disk mismatches.
        if "dispatch.rules ≠ edge_conditions.dispatch" in msg:
            continue
        if "not in edge_conditions" in msg or "has no edge_conditions or core catalog entry" in msg:
            continue
        if "dispatch rule unknown when" in msg:
            continue
        mapped.append(locate_error(msg, payload))

    # In-memory SSOT: assembled routing_conditions ↔ dispatch (what Apply will write)
    from pipeline_edge_conditions import dispatch_rules_from_edge_conditions

    pack_id = str(payload.get("id") or "")
    conditions = _as_dict(_as_dict(payload.get("routing_conditions")).get("edge_conditions"))
    expected = dispatch_rules_from_edge_conditions(conditions)
    actual: list[dict] = []
    for rule in _as_list(_as_dict(payload.get("dispatch")).get("rules")):
        if not isinstance(rule, dict) or not rule.get("when"):
            continue
        try:
            item: dict[str, Any] = {
                "priority": int(rule["priority"]),
                "when": rule["when"],
                "next": rule.get("next"),
            }
        except (TypeError, ValueError, KeyError):
            mapped.append(locate_error(f"{pack_id}: dispatch rule has invalid priority", payload))
            continue
        if rule.get("outcome"):
            item["outcome"] = rule["outcome"]
        actual.append(item)
    actual.sort(key=lambda row: int(row["priority"]))
    if expected != actual:
        mapped.append(
            locate_error(
                f"{pack_id}: dispatch.rules ≠ edge_conditions.dispatch — "
                "сборка не свела таблицу с условиями (нужен reconcile)",
                payload,
            )
        )
    graph = _as_dict(payload.get("graph"))
    for edge in _as_list(graph.get("edges")):
        if not isinstance(edge, dict):
            continue
        for cond in edge_condition_ids(edge):
            if cond and cond not in conditions:
                mapped.append(
                    locate_error(
                        f"{pack_id}: graph edge {edge.get('id')} condition {cond!r} not in edge_conditions",
                        payload,
                    )
                )

    known_agents = set()
    try:
        from pipeline_pack import build_catalog

        known_agents = set(build_catalog(root).get("agents") or [])
    except Exception:
        pass
    node_ids = {
        node.get("id")
        for node in _as_list(graph.get("nodes"))
        if isinstance(node, dict) and node.get("id")
    }
    for msg in _validate_pack_registry(pack_id, _as_dict(payload.get("registry")), node_ids, known_agents):
        mapped.append(locate_error(msg, payload))
    return mapped


def validate_assembled(payload: dict, root: Path, overlay_errors: list[dict] | None = None) -> dict:
    errors = list(overlay_errors or [])
    errors.extend(_layer1_errors(payload))
    if not any("pack JSON" in (item.get("message") or "") for item in errors):
        errors.extend(_layer2_errors(payload, root))
    # de-dupe
    seen: set[str] = set()
    unique: list[dict] = []
    for item in errors:
        key = json.dumps(item, sort_keys=True, ensure_ascii=False)
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return {"ok": not unique, "errors": unique}


def _restore_unchanged_yaml(pipeline_id: str, root: Path, originals: dict[str, str]) -> None:
    folder = packs_dir(root) / pipeline_id
    for key, old_text in originals.items():
        path = folder / f"{key}.yaml"
        if not path.is_file():
            continue
        try:
            if _semantic_equal(load_yaml(path), load_yaml_text(old_text)):
                path.write_text(old_text, encoding="utf-8")
        except Exception:
            continue


def load_yaml_text(text: str) -> dict:
    if not text.strip():
        return {}
    try:
        import yaml  # type: ignore
    except ImportError:
        from spec_catalog import parse_simple_yaml

        data = parse_simple_yaml(text)
    else:
        data = yaml.safe_load(text)
    return data if isinstance(data, dict) else {}


def snapshot_pack_yaml(pipeline_id: str, root: Path) -> dict[str, str]:
    folder = packs_dir(root) / pipeline_id
    originals: dict[str, str] = {}
    for key in ("graph", "dispatch", "status", "registry", "routing_conditions"):
        path = folder / f"{key}.yaml"
        if path.is_file():
            originals[key] = path.read_text(encoding="utf-8")
    return originals


def apply_assembled(payload: dict, root: Path) -> dict:
    pack_id = str(payload.get("id") or "")
    originals = snapshot_pack_yaml(pack_id, root)
    written = apply_pack_json(payload, root)
    _restore_unchanged_yaml(pack_id, root, originals)
    _clear_pack_loader_caches()
    data = merge_compiled_source(root)
    compile_errors = validate_source(data)
    if compile_errors:
        for key, text in originals.items():
            path = packs_dir(root) / pack_id / f"{key}.yaml"
            path.write_text(text, encoding="utf-8")
        _clear_pack_loader_caches()
        raise ValueError("compile failed after write, YAML restored:\n  " + "\n  ".join(compile_errors))
    schema_text, registry_text = compile_outputs(data)
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCHEMA_PATH.write_text(schema_text, encoding="utf-8")
    REGISTRY_PATH.write_text(registry_text, encoding="utf-8")
    _clear_pack_loader_caches()
    return {
        "written": [_rel(path, root) for path in written],
        "compiled": [_rel(SCHEMA_PATH, root), _rel(REGISTRY_PATH, root)],
        "pack": export_pack_json(pack_id, root),
    }


def init_new_pack(pipeline_id: str, template: str, root: Path) -> dict:
    if template not in INIT_TEMPLATES:
        raise ValueError(f"template must be one of: {', '.join(INIT_TEMPLATES)}")
    if not PACK_ID_RE.fullmatch(pipeline_id):
        raise ValueError(f"pack id must be kebab-case, got {pipeline_id!r}")
    if pipeline_id in set(discover_pipeline_ids(root)):
        raise FileExistsError(f"pack already exists: {pipeline_id}")
    written = init_pack(pipeline_id, template, root)
    _clear_pack_loader_caches()
    pack = export_pack_json(pipeline_id, root)
    warnings = orchestrator_md_missing(pipeline_id, root)
    warnings.extend(init_pack_golden_hints(pipeline_id, template))
    if not _as_dict(pack.get("status")):
        warnings.append("шаблон без status — пак неисполняемый")
    return {
        "id": pipeline_id,
        "template": template,
        "pack": pack,
        "warnings": warnings,
        "written": [_rel(path, root) for path in written],
    }


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def preview_payload(payload: dict) -> dict:
    graph = _as_dict(payload.get("graph"))
    return {
        "id": payload.get("id"),
        "label": graph.get("label"),
        "orchestrator": graph.get("orchestrator"),
        "nodes": len(_as_list(graph.get("nodes"))),
        "edges": len(_as_list(graph.get("edges"))),
        "rules": len(_as_list(_as_dict(payload.get("dispatch")).get("rules"))),
        "has_status": bool(payload.get("status")),
        "has_routing_conditions": bool(payload.get("routing_conditions")),
    }

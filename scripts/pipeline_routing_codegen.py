#!/usr/bin/env python3
"""Phase 13: graph/PlantUML/JSON → routing_conditions.yaml + dispatch.yaml.

Runtime formulas stay in edge_conditions (interpreter). This CLI only writes YAML.
Does not invoke analyze-routing. Does not change golden expect.

Inputs (one or more):
  --from-plantuml FILE          edges ``A --> B : label``
  --from-json FILE              pack JSON with graph.edges[].condition
  --from-graph-conditions [FILE]  pack graph.yaml (default pipelines/<id>/graph.yaml)
  (none)                        sync dispatch.rules from existing edge_conditions

Outputs (atomic, merge — do not wipe hand-patched status_fields):
  pipelines/<id>/routing_conditions.yaml
  pipelines/<id>/dispatch.yaml   (rules from edge_conditions.dispatch; invariants kept)
  optional graph.yaml condition / label sync
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from pipeline_edge_conditions import (
    dispatch_rules_from_edge_conditions,
    edge_conditions_map,
    load_routing_conditions,
    routing_conditions_path,
)
from pipeline_pack import _dump_yaml, load_pack, load_yaml, packs_dir, repo_root

PLANTUML_EDGE = re.compile(
    r"^\s*([A-Za-z][\w.-]*)\s+-->\s+([A-Za-z][\w.-]*)(?:\s*:\s*(.+))?\s*$"
)
SLUG_OK = re.compile(r"^[a-z][a-z0-9_]*$")
KNOWN_NOT_HAS = re.compile(r"^not_has_(.+)$")


def slug_condition(label: str) -> str:
    text = (label or "").strip()
    if SLUG_OK.fullmatch(text):
        return text
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return slug or "condition"


def parse_plantuml(text: str) -> list[dict]:
    edges: list[dict] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("@") or line.startswith("'") or line.lower().startswith("skinparam"):
            continue
        match = PLANTUML_EDGE.match(line)
        if not match:
            continue
        src, dst, label = match.group(1), match.group(2), (match.group(3) or "").strip()
        cond = slug_condition(label) if label else ""
        edges.append({"from": src, "to": dst, "label": label, "condition": cond})
    return edges


def _stub_expr(condition_id: str) -> dict:
    match = KNOWN_NOT_HAS.fullmatch(condition_id)
    if match:
        return {"field": f"has_{match.group(1)}", "op": "falsy"}
    # Free-text / authored bool field → truthy (pack authoring Apply contract).
    return {"field": condition_id, "op": "truthy"}


def _next_priority(existing: dict[str, dict]) -> int:
    used = []
    for spec in existing.values():
        disp = spec.get("dispatch") if isinstance(spec.get("dispatch"), dict) else None
        if disp and "priority" in disp:
            try:
                used.append(int(disp["priority"]))
            except (TypeError, ValueError):
                continue
    if not used:
        return 10
    return max(used) + 10


def _terminal_next(node_id: str, graph: dict) -> tuple[object, str | None]:
    if node_id in {"done", "ready"}:
        return None, "ready"
    for node in graph.get("nodes") or []:
        if isinstance(node, dict) and node.get("id") == node_id and node.get("kind") == "terminal":
            return None, "ready"
    return node_id, None


def conditions_from_edges(edges: list[dict], existing: dict[str, dict], graph: dict) -> dict[str, dict]:
    """New/updated edge_conditions entries. Existing expr is never overwritten."""
    updates: dict[str, dict] = {}
    priority_cursor = _next_priority(existing)
    for edge in edges:
        cond = str(edge.get("condition") or slug_condition(str(edge.get("condition_label") or edge.get("label") or "")))
        if not cond:
            continue
        if cond in existing or cond in updates:
            continue
        nxt, outcome = _terminal_next(str(edge.get("to") or ""), graph)
        disp: dict = {"priority": priority_cursor, "next": nxt}
        if outcome:
            disp["outcome"] = outcome
        priority_cursor += 10
        spec = {
            "expr": _stub_expr(cond),
            "dispatch": disp,
            "label": edge.get("label") or edge.get("condition_label") or cond,
            "reason": f"condition {cond}",
        }
        if KNOWN_NOT_HAS.fullmatch(cond):
            spec["core"] = True
        updates[cond] = spec
    return updates


def field_stubs_for(new_conditions: dict[str, dict], existing_fields: dict) -> dict[str, dict]:
    stubs: dict[str, dict] = {}
    for name, spec in new_conditions.items():
        expr = spec.get("expr") if isinstance(spec.get("expr"), dict) else {}
        field = str(expr.get("field") or "")
        if not field or field in existing_fields or field in stubs:
            continue
        stubs[field] = {
            "type": "bool",
            "instruction": (
                f"True iff analyzer sets {field} from feature facts. "
                "Stub from codegen — refine instruction for the pack analyzer."
            ),
        }
    return stubs


def _replace_section(text: str, key: str, block: str) -> str:
    lines = text.splitlines(keepends=True)
    start = None
    end = len(lines)
    for index, line in enumerate(lines):
        stripped = line.split("#", 1)[0]
        if stripped.startswith(f"{key}:") and not line.startswith(" "):
            start = index
            continue
        if start is not None and index > start and line and line[0] not in " \t#\n" and ":" in line:
            end = index
            break
    payload = block if block.endswith("\n") else block + "\n"
    if start is None:
        base = text.rstrip() + "\n"
        return base + payload
    return "".join(lines[:start]) + payload + "".join(lines[end:])


def _dump_section(key: str, value: object) -> str:
    dumped = _dump_yaml({key: value})
    return dumped if dumped.endswith("\n") else dumped + "\n"


def merge_routing_conditions_text(
    existing_text: str,
    *,
    new_conditions: dict[str, dict],
    new_fields: dict[str, dict],
) -> str:
    if existing_text.strip() and not new_conditions and not new_fields:
        return existing_text if existing_text.endswith("\n") else existing_text + "\n"
    data = load_yaml_from_text(existing_text) if existing_text.strip() else {}
    conditions = dict(data.get("edge_conditions") or {})
    conditions.update(new_conditions)
    fields = dict(data.get("status_fields") or {})
    for name, spec in new_fields.items():
        fields.setdefault(name, spec)
    text = existing_text if existing_text.strip() else "schema_version: 1\n"
    if new_fields:
        text = _replace_section(text, "status_fields", _dump_section("status_fields", fields))
    if new_conditions or "edge_conditions:" not in text:
        text = _replace_section(text, "edge_conditions", _dump_section("edge_conditions", conditions))
    return text if text.endswith("\n") else text + "\n"


def load_yaml_from_text(text: str) -> dict:
    try:
        import yaml  # type: ignore
    except ImportError:
        from spec_catalog import parse_simple_yaml

        data = parse_simple_yaml(text)
    else:
        data = yaml.safe_load(text)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError("YAML must be a mapping")
    return data


def _norm_rule(rule: dict) -> dict:
    item = {
        "priority": int(rule["priority"]),
        "when": rule["when"],
        "next": rule.get("next"),
    }
    if rule.get("outcome"):
        item["outcome"] = rule["outcome"]
    return item


def merge_dispatch_text(existing_text: str, rules: list[dict]) -> str:
    data = load_yaml_from_text(existing_text) if existing_text.strip() else {}
    existing_rules = [
        _norm_rule(rule)
        for rule in (data.get("rules") or [])
        if isinstance(rule, dict) and rule.get("when") is not None
    ]
    planned = [_norm_rule(rule) for rule in rules]
    if existing_text.strip() and existing_rules == planned:
        return existing_text if existing_text.endswith("\n") else existing_text + "\n"
    out = dict(data)
    out["rules"] = rules
    if "invariants" not in out:
        out["invariants"] = []
    header = ""
    if existing_text.lstrip().startswith("#"):
        header_lines = []
        for line in existing_text.splitlines(True):
            if line.startswith("#") or line.strip() == "":
                header_lines.append(line)
            else:
                break
        header = "".join(header_lines)
    body = _dump_yaml(out)
    if not body.endswith("\n"):
        body += "\n"
    return header + body


def sync_graph_conditions(graph: dict, edges: list[dict]) -> tuple[dict, bool]:
    updated = dict(graph)
    current = [dict(edge) if isinstance(edge, dict) else edge for edge in (graph.get("edges") or [])]
    index = {(str(e.get("from")), str(e.get("to"))): e for e in current if isinstance(e, dict)}
    changed = False
    for edge in edges:
        src, dst = str(edge.get("from") or ""), str(edge.get("to") or "")
        cond = str(edge.get("condition") or "")
        if not src or not dst or not cond:
            continue
        target = index.get((src, dst))
        if target is None:
            continue
        if target.get("condition") != cond:
            target["condition"] = cond
            changed = True
    updated["edges"] = current
    return updated, changed


def collect_input_edges(args: argparse.Namespace, pipeline_id: str, root: Path) -> list[dict]:
    edges: list[dict] = []
    if args.from_plantuml:
        edges.extend(parse_plantuml(Path(args.from_plantuml).read_text(encoding="utf-8")))
    if args.from_json:
        payload = json.loads(Path(args.from_json).read_text(encoding="utf-8"))
        graph = payload.get("graph") or {}
        for edge in graph.get("edges") or []:
            if isinstance(edge, dict):
                cond = edge.get("condition") or slug_condition(str(edge.get("condition_label") or edge.get("label") or ""))
                item = dict(edge)
                item["condition"] = cond
                edges.append(item)
    if args.from_graph_conditions is not None:
        path = Path(args.from_graph_conditions) if args.from_graph_conditions else packs_dir(root) / pipeline_id / "graph.yaml"
        graph = load_yaml(path) if path.is_file() else {}
        for edge in graph.get("edges") or []:
            if not isinstance(edge, dict):
                continue
            cond = edge.get("condition") or slug_condition(str(edge.get("condition_label") or ""))
            if not cond:
                continue
            item = dict(edge)
            item["condition"] = cond
            edges.append(item)
    return edges


def planned_changes(pipeline_id: str, root: Path, input_edges: list[dict]) -> dict:
    folder = packs_dir(root) / pipeline_id
    try:
        pack = load_pack(pipeline_id, root)
        graph = pack.get("graph") or {}
        dispatch = pack.get("dispatch") or {}
    except FileNotFoundError:
        graph, dispatch = {}, {}
        if (folder / "graph.yaml").is_file():
            graph = load_yaml(folder / "graph.yaml")
        if (folder / "dispatch.yaml").is_file():
            dispatch = load_yaml(folder / "dispatch.yaml")
    existing = edge_conditions_map(pipeline_id, root)
    rc = load_routing_conditions(pipeline_id, root)
    fields = rc.get("status_fields") if isinstance(rc.get("status_fields"), dict) else {}
    new_conditions = conditions_from_edges(input_edges, existing, graph)
    merged = dict(existing)
    merged.update(new_conditions)
    new_fields = field_stubs_for(new_conditions, fields)
    rules = dispatch_rules_from_edge_conditions(merged)
    graph_out, graph_changed = sync_graph_conditions(graph, input_edges)
    return {
        "new_conditions": new_conditions,
        "new_fields": new_fields,
        "merged_conditions": merged,
        "rules": rules,
        "graph": graph_out,
        "graph_changed": graph_changed,
        "dispatch": dispatch,
        "folder": folder,
        "rc_path": routing_conditions_path(pipeline_id, root),
    }


def _atomic_write(path: Path, text: str) -> bool:
    old = path.read_text(encoding="utf-8") if path.is_file() else None
    if old == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)
    return True


def apply_plan(plan: dict, *, write: bool) -> list[str]:
    notes: list[str] = []
    rc_path: Path = plan["rc_path"]
    existing_rc = rc_path.read_text(encoding="utf-8") if rc_path.is_file() else ""
    new_rc = merge_routing_conditions_text(
        existing_rc,
        new_conditions=plan["new_conditions"],
        new_fields=plan["new_fields"],
    )
    dispatch_path = plan["folder"] / "dispatch.yaml"
    existing_dispatch = dispatch_path.read_text(encoding="utf-8") if dispatch_path.is_file() else ""
    new_dispatch = merge_dispatch_text(existing_dispatch, plan["rules"])
    graph_path = plan["folder"] / "graph.yaml"
    existing_graph = graph_path.read_text(encoding="utf-8") if graph_path.is_file() else ""
    new_graph = existing_graph
    if plan["graph_changed"]:
        header = ""
        if existing_graph.lstrip().startswith("#"):
            header_lines = []
            for line in existing_graph.splitlines(True):
                if line.startswith("#") or line.strip() == "":
                    header_lines.append(line)
                else:
                    break
            header = "".join(header_lines)
        body = _dump_yaml(plan["graph"])
        if not body.endswith("\n"):
            body += "\n"
        new_graph = header + body
    if write:
        if _atomic_write(rc_path, new_rc):
            notes.append(f"wrote {rc_path}")
        else:
            notes.append(f"unchanged {rc_path}")
        if _atomic_write(dispatch_path, new_dispatch):
            notes.append(f"wrote {dispatch_path}")
        else:
            notes.append(f"unchanged {dispatch_path}")
        if plan["graph_changed"]:
            if _atomic_write(graph_path, new_graph):
                notes.append(f"wrote {graph_path}")
            else:
                notes.append(f"unchanged {graph_path}")
    else:
        notes.append("dry-run")
        if plan["new_conditions"]:
            notes.append("new edge_conditions:\n" + _dump_yaml(plan["new_conditions"]))
        else:
            notes.append("no new edge_conditions")
        notes.append("dispatch.rules:\n" + _dump_yaml(plan["rules"]))
        if new_rc != existing_rc:
            notes.append("routing_conditions.yaml would change")
        else:
            notes.append("routing_conditions.yaml unchanged")
        if new_dispatch != existing_dispatch:
            notes.append("dispatch.yaml would change")
        else:
            notes.append("dispatch.yaml unchanged")
    return notes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pipeline", required=True)
    parser.add_argument("--from-plantuml", metavar="FILE")
    parser.add_argument("--from-json", metavar="FILE")
    parser.add_argument(
        "--from-graph-conditions",
        nargs="?",
        const="",
        metavar="FILE",
        help="Bootstrap from graph.yaml (omit path → pipelines/<id>/graph.yaml)",
    )
    parser.add_argument("--apply", action="store_true", help="Write YAML under pipelines/<id>/")
    parser.add_argument("--dry-run", action="store_true", help="Print plan, do not write")
    parser.add_argument("--root", type=Path, default=None)
    args = parser.parse_args(argv)
    if not args.apply and not args.dry_run:
        parser.error("specify --apply or --dry-run")
    root = args.root or repo_root()
    edges = collect_input_edges(args, args.pipeline, root)
    plan = planned_changes(args.pipeline, root, edges)
    notes = apply_plan(plan, write=bool(args.apply) and not args.dry_run)
    for note in notes:
        print(note)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

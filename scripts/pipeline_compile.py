#!/usr/bin/env python3
"""Compile pipelines/<id>/ packs → pipeline_schema.json + generated/pipeline_registry.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pipeline_pack import (
    DEFAULT_PIPELINE_ID,
    apply_pack_json,
    build_catalog,
    discover_pipeline_ids,
    merge_compiled_source,
    repo_root,
)

SCRIPTS = Path(__file__).resolve().parent
SCHEMA_PATH = SCRIPTS / "pipeline_schema.json"
REGISTRY_PATH = SCRIPTS / "generated" / "pipeline_registry.json"


def _dispatch_configured(block: object) -> bool:
    if not isinstance(block, dict):
        return False
    rules = block.get("rules")
    invariants = block.get("invariants")
    has_rules = isinstance(rules, list) and bool(rules)
    has_invariants = isinstance(invariants, list) and bool(invariants)
    return has_rules or has_invariants


def validate_dispatch(pipeline_id: str, spec: dict, restartable_steps: list[str], node_ids: set[str]) -> list[str]:
    errors: list[str] = []
    from pipeline_predicates import catalog_names, invariant_names

    known_when = catalog_names(pipeline_id)
    known_inv = invariant_names(pipeline_id)
    valid_steps = set(restartable_steps) | node_ids

    invariants = spec.get("invariants") if isinstance(spec.get("invariants"), list) else []
    if spec.get("invariants") not in (None, [], "[]") and not isinstance(spec.get("invariants"), list):
        errors.append(f"{pipeline_id}: dispatch.invariants must be a list")
    else:
        for inv in invariants:
            if not isinstance(inv, dict):
                errors.append(f"{pipeline_id}: invariant entries must be mappings")
                continue
            inv_id = inv.get("id")
            if inv_id not in known_inv:
                errors.append(f"{pipeline_id}: unknown invariant id: {inv_id!r}")
            step = inv.get("step")
            if step and step not in valid_steps:
                errors.append(f"{pipeline_id}: invariant step invalid: {step!r}")

    rules = spec.get("rules") if isinstance(spec.get("rules"), list) else []
    if spec.get("rules") not in (None, [], "[]") and not isinstance(spec.get("rules"), list):
        errors.append(f"{pipeline_id}: dispatch.rules must be a list")
        return errors

    priorities: set[int] = set()
    for rule in rules:
        if not isinstance(rule, dict):
            errors.append(f"{pipeline_id}: dispatch.rules entries must be mappings")
            continue
        when = rule.get("when")
        if when not in known_when:
            errors.append(f"{pipeline_id}: dispatch rule unknown when: {when!r}")
        try:
            priority = int(rule.get("priority"))
        except (TypeError, ValueError):
            errors.append(f"{pipeline_id}: dispatch rule priority must be int: {when!r}")
            priority = None
        if priority is not None:
            if priority in priorities:
                errors.append(f"{pipeline_id}: duplicate priority: {priority}")
            else:
                priorities.add(priority)
        next_step = rule.get("next")
        outcome = rule.get("outcome")
        if next_step is None:
            if outcome not in {"ready", "stopped"}:
                errors.append(f"{pipeline_id}: next=null requires outcome ready|stopped: {when!r}")
        elif next_step not in valid_steps:
            errors.append(f"{pipeline_id}: invalid next: {next_step!r}")
        if outcome and outcome not in {"ready", "stopped"}:
            errors.append(f"{pipeline_id}: invalid outcome: {outcome!r}")
    return errors


def validate_source(data: dict) -> list[str]:
    errors: list[str] = []
    pipelines = data.get("pipelines")
    registries = data.get("registries") or {}
    if not isinstance(pipelines, dict) or not pipelines:
        errors.append("no pipeline packs found under pipelines/")
        return errors

    seen_steps_global: dict[str, str] = {}
    for pipe_id, pipe in pipelines.items():
        if not isinstance(pipe, dict):
            errors.append(f"pipelines.{pipe_id} must be a mapping")
            continue
        for key in ("label", "orchestrator", "nodes", "edges"):
            if key not in pipe:
                errors.append(f"pipelines.{pipe_id}.{key} required")
        nodes = pipe.get("nodes") or []
        edges = pipe.get("edges") or []
        node_ids = {n.get("id") for n in nodes if isinstance(n, dict)}
        for edge in edges:
            if not isinstance(edge, dict):
                continue
            for end in ("from", "to"):
                target = edge.get(end)
                if target and target not in node_ids:
                    errors.append(f"pipelines.{pipe_id} edge {edge.get('id')} unknown {end}={target}")

        reg = registries.get(pipe_id) or {}
        for field in ("step_to_subagent", "orchestrator_owned", "gated_subagents", "restartable_steps"):
            if field not in reg:
                errors.append(f"registry.{pipe_id}.{field} required")
        step_map = reg.get("step_to_subagent") or {}
        orch_owned = set(reg.get("orchestrator_owned") or [])
        for step, _sub in step_map.items():
            if step in orch_owned:
                errors.append(f"{pipe_id}: step {step} is both orchestrator_owned and mapped")
            prev = seen_steps_global.get(step)
            if prev and prev != pipe_id:
                pass  # uniqueness is per-pipeline; namespace is pipeline_id:step
        for step in node_ids:
            if step:
                seen_steps_global.setdefault(step, pipe_id)

        dispatch = (data.get("dispatch") or {}).get(pipe_id)
        # Option A: pipeline without rules/invariants is valid (no compiled router).
        if _dispatch_configured(dispatch):
            errors.extend(
                validate_dispatch(
                    pipe_id,
                    dispatch,
                    list(reg.get("restartable_steps") or []),
                    {sid for sid in node_ids if sid},
                )
            )
    return errors


def _nodes_meta(pipe: dict) -> list[dict]:
    return [
        {
            "id": node["id"],
            "label": node.get("label", node["id"]),
            "kind": node.get("kind"),
            "subagent": node.get("subagent"),
        }
        for node in pipe.get("nodes", [])
        if isinstance(node, dict) and node.get("id")
    ]


def _normalize_dispatch(spec: dict) -> dict:
    out = dict(spec)
    rules = []
    for rule in spec.get("rules") or []:
        if not isinstance(rule, dict):
            continue
        item = dict(rule)
        if "priority" in item:
            try:
                item["priority"] = int(item["priority"])
            except (TypeError, ValueError):
                pass
        rules.append(item)
    out["rules"] = rules
    if "invariant_after_priority" in out:
        try:
            out["invariant_after_priority"] = int(out["invariant_after_priority"])
        except (TypeError, ValueError):
            pass
    return out


def build_schema(data: dict) -> dict:
    return {"pipelines": data["pipelines"]}


def build_registry(data: dict) -> dict:
    registries = data.get("registries") or {}
    nodes_meta = {pid: _nodes_meta(pipe) for pid, pipe in data["pipelines"].items()}
    per_pipeline: dict[str, dict] = {}
    for pid, reg in registries.items():
        restartable = list(reg.get("restartable_steps") or [])
        per_pipeline[pid] = {
            "step_to_subagent": dict(reg.get("step_to_subagent") or {}),
            "orchestrator_owned": list(reg.get("orchestrator_owned") or []),
            "gated_subagents": list(reg.get("gated_subagents") or []),
            "restartable_steps": restartable,
            "step_order": {name: index for index, name in enumerate(restartable)},
            "delegate_modes": dict(reg.get("delegate_modes") or {})
            if isinstance(reg.get("delegate_modes"), dict)
            else {},
        }

    spec_reg = per_pipeline.get(DEFAULT_PIPELINE_ID) or next(iter(per_pipeline.values()), {})
    dispatch = {}
    for pid, spec in (data.get("dispatch") or {}).items():
        if not isinstance(spec, dict):
            continue
        normalized = _normalize_dispatch(spec)
        if not (normalized.get("rules") or normalized.get("invariants")):
            continue
        dispatch[pid] = normalized
    from pipeline_predicates import catalog_names

    payload = {
        "step_to_subagent": dict(spec_reg.get("step_to_subagent") or {}),
        "orchestrator_owned": list(spec_reg.get("orchestrator_owned") or []),
        "gated_subagents": list(spec_reg.get("gated_subagents") or []),
        "restartable_steps": list(spec_reg.get("restartable_steps") or []),
        "step_order": dict(spec_reg.get("step_order") or {}),
        "nodes": nodes_meta,
        "dispatch": dispatch,
        "status": dict(data.get("status") or {}),
        "pipelines": per_pipeline,
        "predicates": {pid: sorted(catalog_names(pid)) for pid in per_pipeline},
    }
    return payload


def json_text(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def semantic_equal(a: dict, b: dict) -> bool:
    return json.loads(json.dumps(a, sort_keys=True)) == json.loads(json.dumps(b, sort_keys=True))


def diff_report(label: str, expected_text: str, actual_text: str) -> list[str]:
    if expected_text == actual_text:
        return []
    try:
        expected = json.loads(expected_text)
        actual = json.loads(actual_text)
        if semantic_equal(expected, actual):
            return [f"{label}: semantically equal (formatting differs)"]
    except json.JSONDecodeError:
        pass
    return [f"{label}: content differs ({len(expected_text)} vs {len(actual_text)} bytes)"]


def compile_outputs(data: dict) -> tuple[str, str]:
    return json_text(build_schema(data)), json_text(build_registry(data))


_REFERENCE_STEP_TO_SUBAGENT = {
    "find-context": "context-researcher",
    "check-feature": "spec-reviewer",
    "resolve-gaps": "gap-resolver",
    "challenge-feature": "spec-challenger",
    "resolve-challenges": "challenge-resolver",
    "check-feature-code": "code-auditor",
    "resolve-code-alignment": "alignment-resolver",
}
_REFERENCE_ORCHESTRATOR_OWNED = frozenset({"write-feature"})
_REFERENCE_GATED = {
    "context-researcher",
    "spec-writer",
    "spec-reviewer",
    "gap-resolver",
    "spec-challenger",
    "challenge-resolver",
    "code-auditor",
    "alignment-resolver",
}
_REFERENCE_RESTART = (
    "find-context",
    "write-feature",
    "check-feature",
    "resolve-gaps",
    "challenge-feature",
    "resolve-challenges",
    "check-feature-code",
    "resolve-code-alignment",
)
_REFERENCE_SPEC_EDGES = {
    ("spec-orchestrator", "find-context"),
    ("find-context", "write-feature"),
    ("write-feature", "check-feature"),
    ("check-feature", "resolve-gaps"),
    ("check-feature", "resolve-challenges"),
    ("check-feature", "resolve-code-alignment"),
    ("check-feature", "challenge-feature"),
    ("resolve-gaps", "check-feature"),
    ("resolve-gaps", "resolve-challenges"),
    ("resolve-gaps", "resolve-code-alignment"),
    ("check-feature", "check-feature-code"),
    ("challenge-feature", "resolve-challenges"),
    ("resolve-challenges", "check-feature"),
    ("check-feature-code", "check-feature"),
    ("check-feature-code", "resolve-gaps"),
    ("check-feature-code", "resolve-code-alignment"),
    ("resolve-code-alignment", "check-feature-code"),
    ("resolve-code-alignment", "check-feature"),
    ("check-feature-code", "done"),
}


def check_parity_against_legacy(data: dict) -> list[str]:
    messages: list[str] = []
    registry = build_registry(data)
    spec = registry["pipelines"].get(DEFAULT_PIPELINE_ID) or {}
    if spec.get("step_to_subagent") != _REFERENCE_STEP_TO_SUBAGENT:
        messages.append("parity: spec step_to_subagent ≠ legacy STEP_TO_SUBAGENT")
    if set(spec.get("orchestrator_owned") or []) != _REFERENCE_ORCHESTRATOR_OWNED:
        messages.append("parity: spec orchestrator_owned ≠ legacy")
    if set(spec.get("gated_subagents") or []) != _REFERENCE_GATED:
        messages.append("parity: spec gated_subagents ≠ legacy")
    if tuple(spec.get("restartable_steps") or []) != _REFERENCE_RESTART:
        messages.append("parity: spec restartable_steps ≠ legacy")

    schema = build_schema(data)
    spec_edges = {(e["from"], e["to"]) for e in schema["pipelines"]["spec"]["edges"]}
    if spec_edges != _REFERENCE_SPEC_EDGES:
        messages.append("parity: spec pipeline edges changed")
    return messages


def run_check(data: dict) -> tuple[bool, list[str]]:
    messages: list[str] = []
    validation = validate_source(data)
    if validation:
        return False, [f"validation: {item}" for item in validation]

    schema_text, registry_text = compile_outputs(data)
    if SCHEMA_PATH.is_file():
        messages.extend(diff_report("pipeline_schema.json", SCHEMA_PATH.read_text(encoding="utf-8"), schema_text))
    else:
        messages.append("pipeline_schema.json: missing (would be created by --apply)")
    if REGISTRY_PATH.is_file():
        messages.extend(
            diff_report("pipeline_registry.json", REGISTRY_PATH.read_text(encoding="utf-8"), registry_text)
        )
    else:
        messages.append("pipeline_registry.json: missing (would be created by --apply)")
    messages.extend(check_parity_against_legacy(data))
    ok = not any(
        msg.endswith("differs") or msg.startswith("validation:") or msg.startswith("parity:")
        for msg in messages
    )
    return ok, messages


def run_apply(data: dict) -> None:
    validation = validate_source(data)
    if validation:
        raise SystemExit("validation failed:\n  " + "\n  ".join(validation))
    schema_text, registry_text = compile_outputs(data)
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCHEMA_PATH.write_text(schema_text, encoding="utf-8")
    REGISTRY_PATH.write_text(registry_text, encoding="utf-8")
    print(f"Wrote {SCHEMA_PATH.relative_to(SCRIPTS.parent)}")
    print(f"Wrote {REGISTRY_PATH.relative_to(SCRIPTS.parent)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--apply", action="store_true")
    group.add_argument("--catalog", action="store_true", help="JSON palette: agents, skills, steps, predicates")
    group.add_argument("--from-json", metavar="FILE", help="Write pack YAML from JSON, then --apply")
    args = parser.parse_args(argv)
    root = repo_root()

    if args.catalog:
        print(json.dumps(build_catalog(root), ensure_ascii=False, indent=2))
        return 0

    if args.from_json:
        payload = json.loads(Path(args.from_json).read_text(encoding="utf-8"))
        written = apply_pack_json(payload, root)
        for path in written:
            print(f"Wrote {path}")
        data = merge_compiled_source(root)
        run_apply(data)
        return 0

    ids = discover_pipeline_ids(root)
    if not ids:
        print("No pipeline packs in pipelines/", file=sys.stderr)
        return 1
    data = merge_compiled_source(root)

    if args.apply:
        run_apply(data)
        return 0

    ok, messages = run_check(data)
    print("pipeline compile --check")
    print("-" * 40)
    print(f"packs: {', '.join(ids)}")
    if not messages:
        print("[OK]   schema + registry up to date")
        print("[OK]   parity: spec pack unchanged")
    for msg in messages:
        if msg.startswith("parity:") or "differs (" in msg or msg.startswith("validation:"):
            print(f"[FAIL] {msg}")
        else:
            print(f"[OK]   {msg}")
    print("-" * 40)
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

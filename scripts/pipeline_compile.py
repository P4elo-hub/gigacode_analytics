#!/usr/bin/env python3
"""Compile scripts/pipeline.yaml → pipeline_schema.json + generated/pipeline_registry.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
YAML_PATH = SCRIPTS / "pipeline.yaml"
SCHEMA_PATH = SCRIPTS / "pipeline_schema.json"
REGISTRY_PATH = SCRIPTS / "generated" / "pipeline_registry.json"


def load_yaml(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore
    except ImportError:
        from spec_catalog import parse_simple_yaml

        data = parse_simple_yaml(text)
    else:
        data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must be a mapping")
    return data


def validate_dispatch(data: dict, restartable_steps: list[str]) -> list[str]:
    errors: list[str] = []
    dispatch = data.get("dispatch")
    if not isinstance(dispatch, dict):
        errors.append("missing dispatch mapping")
        return errors

    try:
        from pipeline_router import KNOWN_INVARIANTS, KNOWN_PREDICATES, VALID_OUTCOMES, VALID_STEPS
    except ImportError as exc:
        errors.append(f"dispatch validation import failed: {exc}")
        return errors

    valid_steps = set(restartable_steps) | VALID_STEPS
    spec = dispatch.get("spec")
    if not isinstance(spec, dict):
        errors.append("dispatch.spec required")
        return errors

    invariants = spec.get("invariants") or []
    if not isinstance(invariants, list):
        errors.append("dispatch.spec.invariants must be a list")
    else:
        for inv in invariants:
            if not isinstance(inv, dict):
                errors.append("dispatch.spec.invariants entries must be mappings")
                continue
            inv_id = inv.get("id")
            if inv_id not in KNOWN_INVARIANTS:
                errors.append(f"dispatch invariant unknown id: {inv_id!r}")
            step = inv.get("step")
            if step and step not in valid_steps:
                errors.append(f"dispatch invariant step invalid: {step!r}")

    rules = spec.get("rules") or []
    if not isinstance(rules, list):
        errors.append("dispatch.spec.rules must be a list")
        return errors

    priorities: set[int] = set()
    for rule in rules:
        if not isinstance(rule, dict):
            errors.append("dispatch.spec.rules entries must be mappings")
            continue
        when = rule.get("when")
        if when not in KNOWN_PREDICATES:
            errors.append(f"dispatch rule unknown when: {when!r}")
        priority_raw = rule.get("priority")
        try:
            priority = int(priority_raw)
        except (TypeError, ValueError):
            errors.append(f"dispatch rule priority must be int: {when!r}")
            priority = None
        if priority is not None:
            if priority in priorities:
                errors.append(f"dispatch rule duplicate priority: {priority}")
            else:
                priorities.add(priority)

        next_step = rule.get("next")
        outcome = rule.get("outcome")
        if next_step is None:
            if outcome not in VALID_OUTCOMES:
                errors.append(f"dispatch rule next=null requires outcome ready|stopped: {when!r}")
        elif next_step not in valid_steps:
            errors.append(f"dispatch rule invalid next: {next_step!r}")
        if outcome and outcome not in VALID_OUTCOMES:
            errors.append(f"dispatch rule invalid outcome: {outcome!r}")

    return errors


def validate_source(data: dict) -> list[str]:
    errors: list[str] = []
    registry = data.get("registry")
    pipelines = data.get("pipelines")
    if not isinstance(registry, dict):
        errors.append("missing registry mapping")
    if not isinstance(pipelines, dict):
        errors.append("missing pipelines mapping")
        return errors

    for field in ("step_to_subagent", "orchestrator_owned", "gated_subagents", "restartable_steps"):
        if field not in registry:
            errors.append(f"registry.{field} required")

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

    step_map = registry.get("step_to_subagent") or {}
    orch_owned = set(registry.get("orchestrator_owned") or [])
    for step, subagent in step_map.items():
        if step in orch_owned:
            errors.append(f"step {step} is both orchestrator_owned and in step_to_subagent")

    errors.extend(validate_dispatch(data, list(registry.get("restartable_steps") or [])))

    return errors


def build_schema(data: dict) -> dict:
    return {"pipelines": data["pipelines"]}


def build_registry(data: dict) -> dict:
    registry_src = data["registry"]
    restartable = list(registry_src["restartable_steps"])
    nodes_meta: dict[str, list[dict]] = {}
    for pipe_id, pipe in data["pipelines"].items():
        nodes_meta[pipe_id] = [
            {
                "id": node["id"],
                "label": node.get("label", node["id"]),
                "kind": node.get("kind"),
                "subagent": node.get("subagent"),
            }
            for node in pipe.get("nodes", [])
            if isinstance(node, dict) and node.get("id")
        ]
    payload = {
        "step_to_subagent": dict(registry_src["step_to_subagent"]),
        "orchestrator_owned": list(registry_src["orchestrator_owned"]),
        "gated_subagents": list(registry_src["gated_subagents"]),
        "restartable_steps": restartable,
        "step_order": {name: index for index, name in enumerate(restartable)},
        "nodes": nodes_meta,
    }
    dispatch = data.get("dispatch")
    if isinstance(dispatch, dict):
        payload["dispatch"] = dispatch
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
            diff_report(
                "pipeline_registry.json",
                REGISTRY_PATH.read_text(encoding="utf-8"),
                registry_text,
            )
        )
    else:
        messages.append("pipeline_registry.json: missing (would be created by --apply)")

    parity = check_parity_against_legacy(data)
    messages.extend(parity)

    ok = not any(
        msg.endswith("differs") or msg.startswith("validation:") or msg.startswith("parity:")
        for msg in messages
    )
    return ok, messages


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


def check_parity_against_legacy(data: dict) -> list[str]:
    """Compare registry fields with phase-0 hardcoded constants."""
    messages: list[str] = []
    registry = build_registry(data)
    if registry["step_to_subagent"] != _REFERENCE_STEP_TO_SUBAGENT:
        messages.append("parity: step_to_subagent ≠ legacy STEP_TO_SUBAGENT")
    if set(registry["orchestrator_owned"]) != _REFERENCE_ORCHESTRATOR_OWNED:
        messages.append("parity: orchestrator_owned ≠ legacy ORCHESTRATOR_OWNED_STEPS")

    legacy_gated = {
        "context-researcher",
        "spec-writer",
        "spec-reviewer",
        "gap-resolver",
        "spec-challenger",
        "challenge-resolver",
        "code-auditor",
        "alignment-resolver",
    }
    if set(registry["gated_subagents"]) != legacy_gated:
        messages.append("parity: gated_subagents ≠ legacy PIPELINE_GATED_SUBAGENTS")

    legacy_restart = (
        "find-context",
        "write-feature",
        "check-feature",
        "resolve-gaps",
        "challenge-feature",
        "resolve-challenges",
        "check-feature-code",
        "resolve-code-alignment",
    )
    if tuple(registry["restartable_steps"]) != legacy_restart:
        messages.append("parity: restartable_steps ≠ legacy RESTARTABLE_STEPS")

    schema = build_schema(data)
    if SCHEMA_PATH.is_file():
        current = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        if not semantic_equal(schema, current):
            messages.append("parity: compiled schema ≠ pipeline_schema.json")

    spec_edges = {(e["from"], e["to"]) for e in schema["pipelines"]["spec"]["edges"]}
    legacy_edges = {
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
    if spec_edges != legacy_edges:
        messages.append("parity: spec pipeline edges changed")

    return messages


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
    group.add_argument("--check", action="store_true", help="Validate and diff without writing")
    group.add_argument("--apply", action="store_true", help="Generate schema + registry")
    args = parser.parse_args(argv)

    if not YAML_PATH.is_file():
        print(f"Missing {YAML_PATH}", file=sys.stderr)
        return 1

    data = load_yaml(YAML_PATH)

    if args.apply:
        run_apply(data)
        return 0

    ok, messages = run_check(data)
    print("pipeline compile --check")
    print("-" * 40)
    if not messages:
        print("[OK]   pipeline_schema.json: up to date")
        print("[OK]   pipeline_registry.json: up to date")
        print("[OK]   parity: legacy mapping unchanged")
    for msg in messages:
        if msg.startswith("parity:") or "differs (" in msg:
            print(f"[FAIL] {msg}")
        else:
            print(f"[OK]   {msg}")
    print("-" * 40)
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Discover, load, and catalog pipeline packs under pipelines/<id>/."""

from __future__ import annotations

import importlib.util
import json
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

PACK_FILES = ("graph.yaml", "dispatch.yaml", "status.yaml", "registry.yaml")
OPTIONAL_PY = ("collectors.py", "predicates.py", "validate.py")
DEFAULT_PIPELINE_ID = "spec"
PACK_SCHEMA_RELPATH = "scripts/pipeline_pack_schema.json"
CATALOG_VERSION = 1
CATALOG_KEYS = (
    "catalog_version",
    "pipelines",
    "agents",
    "skills",
    "steps",
    "predicates",
    "runtime",
    "pack_files",
    "optional_python",
    "pack_schema",
)
CATALOG_PIPELINE_ITEM_KEYS = ("id", "label", "orchestrator")
CATALOG_PREDICATES_KEYS = ("core", "by_pipeline")
CATALOG_RUNTIME_KEYS = ("pipeline_id", "orchestrator", "dispatch_supported", "loop", "validate")


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def packs_dir(root: Path | None = None) -> Path:
    return (root or repo_root()) / "pipelines"


def load_yaml(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
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
        raise ValueError(f"{path} must be a mapping")
    return data


def discover_pipeline_ids(root: Path | None = None) -> list[str]:
    base = packs_dir(root)
    if not base.is_dir():
        return []
    ids = [
        child.name
        for child in sorted(base.iterdir())
        if child.is_dir() and not child.name.startswith(".") and (child / "graph.yaml").is_file()
    ]
    return ids


@lru_cache(maxsize=16)
def load_pack_module(pipeline_id: str, name: str, root: Path | None = None):
    path = packs_dir(root) / pipeline_id / f"{name}.py"
    if not path.is_file():
        return None
    mod_name = f"pipeline_pack_{pipeline_id}_{name}"
    spec = importlib.util.spec_from_file_location(mod_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module


def load_pack(pipeline_id: str, root: Path | None = None) -> dict[str, Any]:
    folder = packs_dir(root) / pipeline_id
    if not folder.is_dir():
        raise FileNotFoundError(f"missing pack: {folder}")
    pack: dict[str, Any] = {"id": pipeline_id}
    for filename in PACK_FILES:
        path = folder / filename
        key = filename.removesuffix(".yaml")
        pack[key] = load_yaml(path) if path.is_file() else {}
    graph = pack["graph"]
    if "label" not in graph or "orchestrator" not in graph:
        raise ValueError(f"{pipeline_id}: graph.yaml needs label and orchestrator")
    pack["dispatch"] = _normalize_dispatch_block(_as_dict(pack.get("dispatch")))
    pack["status"] = _as_dict(pack.get("status"))
    pack["registry"] = _as_dict(pack.get("registry"))
    pack["registry"]["step_to_subagent"] = _as_dict(pack["registry"].get("step_to_subagent"))
    pack["registry"]["orchestrator_owned"] = _as_list(pack["registry"].get("orchestrator_owned"))
    pack["registry"]["gated_subagents"] = _as_list(pack["registry"].get("gated_subagents"))
    pack["registry"]["restartable_steps"] = _as_list(pack["registry"].get("restartable_steps"))
    pack["registry"]["delegate_modes"] = _as_dict(pack["registry"].get("delegate_modes"))
    pack["status"]["artifacts"] = _as_dict(pack["status"].get("artifacts"))
    pack["status"]["collectors"] = _as_list(pack["status"].get("collectors"))
    pack["status"]["stale"] = _as_list(pack["status"].get("stale"))
    pack["status"]["invariants"] = _as_list(pack["status"].get("invariants"))
    pack["status"]["orchestrator"] = _as_dict(pack["status"].get("orchestrator"))
    pack["status"]["messages"] = _as_dict(pack["status"].get("messages"))
    pack["status"]["display"] = _as_dict(pack["status"].get("display"))
    pack["status"]["constants"] = _as_dict(pack["status"].get("constants"))
    return pack


def _as_dict(value: object) -> dict:
    if isinstance(value, dict):
        return value
    return {}


def _as_list(value: object) -> list:
    if value is None or value == "" or value == "[]":
        return []
    if isinstance(value, list):
        return value
    return []


def _normalize_dispatch_block(spec: dict) -> dict:
    out = dict(spec)
    out["invariants"] = _as_list(spec.get("invariants"))
    out["rules"] = _as_list(spec.get("rules"))
    if "invariant_after_priority" in out:
        try:
            out["invariant_after_priority"] = int(out["invariant_after_priority"])
        except (TypeError, ValueError):
            pass
    return out


def load_all_packs(root: Path | None = None) -> dict[str, dict]:
    return {pid: load_pack(pid, root) for pid in discover_pipeline_ids(root)}


def merge_compiled_source(root: Path | None = None) -> dict:
    """Flatten packs into the compile input shape (pipelines + per-id registry/dispatch/status)."""
    packs = load_all_packs(root)
    pipelines = {}
    registries: dict[str, dict] = {}
    dispatch: dict[str, dict] = {}
    status: dict[str, dict] = {}
    for pid, pack in packs.items():
        graph = dict(pack["graph"])
        pipelines[pid] = graph
        registries[pid] = dict(pack["registry"])
        dispatch[pid] = dict(pack["dispatch"])
        status[pid] = dict(pack["status"])
    return {
        "pipelines": pipelines,
        "registries": registries,
        "dispatch": dispatch,
        "status": status,
    }


def _list_md_stems(folder: Path) -> list[str]:
    if not folder.is_dir():
        return []
    return sorted(path.stem for path in folder.glob("*.md") if path.is_file())


def _list_skill_dirs(folder: Path) -> list[str]:
    if not folder.is_dir():
        return []
    return sorted(
        child.name
        for child in folder.iterdir()
        if child.is_dir() and (child / "SKILL.md").is_file()
    )


def build_catalog(root: Path | None = None) -> dict:
    """Palette for authoring: pipelines, agents, skills, steps, predicates."""
    from pipeline_predicates import catalog_names, core_predicate_names

    base = root or repo_root()
    packs = load_all_packs(base)
    agents: set[str] = set()
    skills: set[str] = set()
    for cli in (".qwen", ".gigacode", ".opencode"):
        agents.update(_list_md_stems(base / cli / "agents"))
        skills.update(_list_skill_dirs(base / cli / "skills"))

    steps: dict[str, list[str]] = {}
    predicates: dict[str, list[str]] = {}
    for pid, pack in packs.items():
        nodes = pack["graph"].get("nodes") or []
        steps[pid] = [n.get("id") for n in nodes if isinstance(n, dict) and n.get("id")]
        predicates[pid] = sorted(catalog_names(pid))

    from pipeline_runtime import runtime_contract

    runtime: dict[str, dict] = {}
    for pid, pack in packs.items():
        try:
            runtime[pid] = runtime_contract(pid)
        except (ValueError, FileNotFoundError, KeyError):
            dispatch = pack.get("dispatch") or {}
            runtime[pid] = {
                "pipeline_id": pid,
                "orchestrator": pack["graph"].get("orchestrator") or "",
                "dispatch_supported": bool(dispatch.get("rules") or dispatch.get("invariants")),
                "loop": [
                    f"python3 scripts/pipeline_delegate.py <task_id> --cli qwen --pipeline {pid}",
                    "action → task | ask_user | write_feature_cycle | orchestrator_only | ready | stopped | error",
                    (
                        "python3 scripts/append_run_log.py --slug <task_id> --step <step> "
                        f"--subagent <agent> --result ok --pipeline {pid}"
                    ),
                    f"python3 scripts/ingest_session_telemetry.py <task_id> --cli qwen --pipeline {pid}",
                    f"python3 scripts/pipeline_validate.py <task_id> --pipeline {pid}",
                ],
                "validate": {
                    "engine": "scripts/pipeline_validate.py",
                    "pack": f"pipelines/{pid}/validate.py",
                    "extra_advice": (packs_dir(base) / pid / "validate.py").is_file(),
                },
            }

    return {
        "catalog_version": CATALOG_VERSION,
        "pipelines": [
            {
                "id": pid,
                "label": pack["graph"].get("label", pid),
                "orchestrator": pack["graph"].get("orchestrator", ""),
            }
            for pid, pack in packs.items()
        ],
        "agents": sorted(agents),
        "skills": sorted(skills),
        "steps": steps,
        "predicates": {
            "core": sorted(core_predicate_names()),
            "by_pipeline": predicates,
        },
        "runtime": runtime,
        "pack_files": list(PACK_FILES),
        "optional_python": list(OPTIONAL_PY),
        "pack_schema": PACK_SCHEMA_RELPATH,
    }


def write_pack_yaml(pipeline_id: str, data: dict, root: Path | None = None) -> list[Path]:
    """Write a pack from JSON (frontend / --from-json). Returns written paths."""
    folder = packs_dir(root) / pipeline_id
    folder.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for key in ("graph", "dispatch", "status", "registry"):
        if key not in data:
            continue
        path = folder / f"{key}.yaml"
        path.write_text(_dump_yaml(data[key]), encoding="utf-8")
        written.append(path)
    return written


def _dump_yaml(payload: object) -> str:
    try:
        import yaml  # type: ignore

        return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)
    except ImportError:
        return _dump_simple_yaml(payload) + "\n"


def _format_yaml_scalar(value: object) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    text = str(value)
    if (
        text == ""
        or text.strip() != text
        or text in {"true", "false", "null", "~"}
        or any(char in text for char in ":#{}[]&*?|>'!%@`,\n")
    ):
        return json.dumps(text, ensure_ascii=False)
    return text


def _dump_simple_yaml(payload: object, indent: int = 0) -> str:
    """Subset matching parse_simple_yaml (no PyYAML required)."""
    pad = "  " * indent
    if isinstance(payload, dict):
        if not payload:
            return ""
        lines = [_dump_mapping_item(str(key), value, indent) for key, value in payload.items()]
        return "\n".join(line for line in lines if line != "")
    if isinstance(payload, list):
        return _dump_simple_list(payload, indent)
    return f"{pad}{_format_yaml_scalar(payload)}"


def _dump_mapping_item(key: str, value: object, indent: int) -> str:
    pad = "  " * indent
    if isinstance(value, dict):
        if not value:
            return f"{pad}{key}:"
        return f"{pad}{key}:\n{_dump_simple_yaml(value, indent + 1)}"
    if isinstance(value, list):
        if not value:
            return f"{pad}{key}:"
        return f"{pad}{key}:\n{_dump_simple_list(value, indent + 1)}"
    return f"{pad}{key}: {_format_yaml_scalar(value)}"


def _dump_simple_list(items: list, indent: int) -> str:
    pad = "  " * indent
    lines: list[str] = []
    for item in items:
        if isinstance(item, dict) and item:
            entries = list(item.items())
            first_key, first_val = entries[0]
            if isinstance(first_val, (dict, list)):
                lines.append(f"{pad}-")
                lines.append(_dump_simple_yaml(item, indent + 1))
            else:
                lines.append(f"{pad}- {first_key}: {_format_yaml_scalar(first_val)}")
                rest = dict(entries[1:])
                if rest:
                    lines.append(_dump_simple_yaml(rest, indent + 1))
        elif isinstance(item, list):
            lines.append(f"{pad}-")
            if item:
                lines.append(_dump_simple_list(item, indent + 1))
        else:
            lines.append(f"{pad}- {_format_yaml_scalar(item)}")
    return "\n".join(line for line in lines if line != "")


def export_pack_json(pipeline_id: str, root: Path | None = None) -> dict:
    """YAML pack → authoring JSON (editor roundtrip)."""
    pack = load_pack(pipeline_id, root)
    return {
        "id": pack["id"],
        "graph": pack["graph"],
        "dispatch": pack["dispatch"],
        "status": pack["status"],
        "registry": pack["registry"],
    }


def apply_pack_json(payload: dict, root: Path | None = None) -> list[Path]:
    from pipeline_pack_authoring import normalize_pack_payload, validate_pack_json

    if not isinstance(payload, dict):
        raise ValueError("invalid pack JSON:\n  pack JSON: payload must be an object")
    data = normalize_pack_payload(payload)
    errors = validate_pack_json(data)
    if errors:
        raise ValueError("invalid pack JSON:\n  " + "\n  ".join(errors))
    pipeline_id = str(data.get("id") or "")
    if not pipeline_id:
        raise ValueError("pack JSON needs id or pipeline_id")
    return write_pack_yaml(pipeline_id, data, root)

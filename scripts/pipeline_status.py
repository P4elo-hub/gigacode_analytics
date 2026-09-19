"""Generic status builder driven by pipelines/<id>/status.yaml."""

from __future__ import annotations

from pathlib import Path

from pipeline_common import step_to_command, subagent_for_step
from pipeline_pack import DEFAULT_PIPELINE_ID, load_pack, load_pack_module, repo_root

_STATUS_CACHE: dict[str, dict] = {}


def load_status_spec(pipeline_id: str = DEFAULT_PIPELINE_ID, *, registry: dict | None = None) -> dict:
    """Status contract for a pipeline. Registry first, then pack YAML."""
    if registry is not None:
        status = (registry.get("status") or {}).get(pipeline_id)
        if isinstance(status, dict) and status:
            return status
        pipes = registry.get("pipelines") or {}
        pipe = pipes.get(pipeline_id) if isinstance(pipes, dict) else None
        if isinstance(pipe, dict) and isinstance(pipe.get("status"), dict):
            return pipe["status"]
    cached = _STATUS_CACHE.get(pipeline_id)
    if cached is not None:
        return cached
    try:
        from pipeline_common import load_pipeline_registry

        data = load_pipeline_registry()
        status = (data.get("status") or {}).get(pipeline_id)
        if isinstance(status, dict) and status:
            _STATUS_CACHE[pipeline_id] = status
            return status
    except (FileNotFoundError, ValueError, KeyError):
        pass
    pack = load_pack(pipeline_id, repo_root())
    status = pack.get("status") or {}
    _STATUS_CACHE[pipeline_id] = status
    return status


def resolve_artifact_path(root: Path, template: str, task_id: str) -> Path:
    return root / template.format(task_id=task_id, slug=task_id)


def resolve_artifact_paths(
    root: Path,
    task_id: str,
    pipeline_id: str = DEFAULT_PIPELINE_ID,
) -> dict[str, Path]:
    spec = load_status_spec(pipeline_id)
    paths: dict[str, Path] = {}
    for art_id, art in (spec.get("artifacts") or {}).items():
        if not isinstance(art, dict):
            continue
        template = art.get("path")
        if template:
            paths[str(art_id)] = resolve_artifact_path(root, str(template), task_id)
    return paths


def collectors_for(pipeline_id: str = DEFAULT_PIPELINE_ID) -> dict:
    collectors_mod = load_pack_module(pipeline_id, "collectors")
    registry = getattr(collectors_mod, "COLLECTORS", {}) if collectors_mod else {}
    return registry if isinstance(registry, dict) else {}


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines()) if path.is_file() else 0


def _mtime(path: Path | None) -> float | None:
    if path is None or not path.is_file():
        return None
    return path.stat().st_mtime


def apply_artifact_presence(status, paths: dict[str, Path], artifacts: dict) -> None:
    """Disk is SSOT for exists_as / lines_as. Overlay JSON cannot hide a file."""
    for art_id, path in paths.items():
        art = artifacts.get(art_id) if isinstance(artifacts.get(art_id), dict) else {}
        exists_as = (art or {}).get("exists_as") or f"has_{art_id}"
        setattr(status, exists_as, path.is_file())
        lines_as = (art or {}).get("lines_as")
        if lines_as:
            setattr(status, lines_as, _line_count(path))


def evaluate_stale_rule(rule: dict, paths: dict[str, Path]) -> bool:
    when = rule.get("when")
    left = _mtime(paths.get(str(rule.get("left") or "")))
    right = _mtime(paths.get(str(rule.get("right") or "")))
    if rule.get("require_left") and left is None:
        return False
    if left is None or right is None:
        return False
    if when == "artifact_older_than":
        return left < right
    if when == "artifact_newer_than":
        return left > right
    return False


def populate_status(status, root: Path, task_id: str, pipeline_id: str = DEFAULT_PIPELINE_ID) -> None:
    spec = load_status_spec(pipeline_id)
    if hasattr(status, "pipeline_id"):
        status.pipeline_id = pipeline_id
    paths = resolve_artifact_paths(root, task_id, pipeline_id)
    artifacts = spec.get("artifacts") or {}
    apply_artifact_presence(status, paths, artifacts)

    registry = collectors_for(pipeline_id)
    for item in spec.get("collectors") or []:
        if not isinstance(item, dict):
            continue
        fn = registry.get(item.get("id"))
        if fn:
            fn(root, task_id, status, paths)

    apply_artifact_presence(status, paths, artifacts)

    stale: list[str] = []
    for rule in spec.get("stale") or []:
        if isinstance(rule, dict) and evaluate_stale_rule(rule, paths):
            stale.append(str(rule.get("id") or ""))
    status.stale = list(dict.fromkeys(item for item in stale if item))

    align_rule = spec.get("alignment_stale")
    if isinstance(align_rule, dict):
        status.alignment_stale = evaluate_stale_rule(align_rule, paths)


def finalize_orchestrator_mode(status, pipeline_id: str = DEFAULT_PIPELINE_ID) -> None:
    spec = load_status_spec(pipeline_id)
    orch = spec.get("orchestrator") or {}
    if status.ready:
        status.orchestrator_mode = "ready"
        status.must_continue = False
        return
    if not status.next_step:
        status.orchestrator_mode = "stopped"
        status.must_continue = False
        return
    from inner_cycle import cycle_config_for_step

    if cycle_config_for_step(pipeline_id, status.next_step):
        status.orchestrator_mode = "write_feature_cycle"
        status.must_continue = True
        return
    write_step = orch.get("write_cycle_step")
    if write_step and status.next_step == write_step:
        status.orchestrator_mode = "write_feature_cycle"
        status.must_continue = True
        return
    ask_field = orch.get("ask_user_when")
    if ask_field and getattr(status, ask_field, 0):
        from pipeline_runtime import node_asks_user

        if node_asks_user(pipeline_id, status.next_step):
            status.orchestrator_mode = "ask_user"
            status.must_continue = False
            return
    status.orchestrator_mode = "delegate"
    status.must_continue = True


def apply_dispatch_fields(status, next_step: str, next_reason: str, pipeline_id: str) -> None:
    status.next_step = next_step
    status.next_reason = next_reason
    if next_step:
        status.next_command = step_to_command(next_step, status.slug)
        status.next_subagent = subagent_for_step(next_step, pipeline_id)
    else:
        status.next_command = ""
        status.next_subagent = ""
    finalize_orchestrator_mode(status, pipeline_id)


def build_status(root: Path, task_id: str, pipeline_id: str = DEFAULT_PIPELINE_ID, *, status=None):
    if status is None:
        from feature_status import FeatureStatus

        status = FeatureStatus(slug=task_id, pipeline_id=pipeline_id)
    populate_status(status, root, task_id, pipeline_id)
    from pipeline_router import apply_router_decision

    apply_router_decision(status, root, task_id, pipeline_id=pipeline_id)
    return status

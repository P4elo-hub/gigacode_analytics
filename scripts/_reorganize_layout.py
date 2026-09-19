#!/usr/bin/env python3
"""One-time layout helper: move scripts into subfolders + root launchers."""

from __future__ import annotations

import shutil
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent

LAYOUT: dict[str, list[str]] = {
    "shared": [
        "artifact_paths.py",
        "resolve_feature_slug.py",
        "pipeline_common.py",
        "telemetry_common.py",
        "calibration_paths.py",
    ],
    "hooks": [
        "pipeline_after_subagent.py",
        "pipeline_before_subagent.py",
    ],
    "telemetry": [
        "append_run_log.py",
        "ingest_session_telemetry.py",
        "ingest_opencode.py",
        "agent_logs.py",
        "archive_subagent_passes.py",
        "sync_pipeline_session.py",
    ],
    "pipeline": [
        "pipeline_dispatch.py",
        "pipeline_delegate.py",
        "pipeline_router.py",
        "pipeline_validate.py",
        "pipeline_status.py",
        "pipeline_predicates.py",
        "pipeline_runtime.py",
        "pipeline_position.py",
        "pipeline_active_task.py",
        "pipeline_set_active_task.py",
        "pipeline_restart.py",
        "pipeline_divergence.py",
        "feature_status.py",
    ],
    "routing": [
        "pipeline_routing_state.py",
        "pipeline_edge_conditions.py",
        "routing_state_baseline.py",
        "routing_state_parity.py",
        "routing_state_replay_from_collectors.py",
    ],
    "authoring": [
        "pipeline_compile.py",
        "pipeline_pack.py",
        "pipeline_pack_authoring.py",
        "pipeline_routing_codegen.py",
        "routing_conditions_extract.py",
    ],
    "analytics": [
        "write_feature.py",
        "find_context.py",
        "refresh_context.py",
        "discovery_focus.py",
        "quality_gates.py",
        "part_checks.py",
        "section_profiles.py",
        "spec_catalog.py",
        "analyze_context_gaps.py",
    ],
    "calibration": [
        "prepare_benchmark_rerun.py",
        "score_calibration_run.py",
        "analyze_spec_delta.py",
        "sync_gold_spec.py",
        "snapshot_baseline.py",
    ],
    "viewer": [
        "build_pipeline_graph.py",
        "pipeline_watch.py",
        "pipeline_timings.py",
        "pipeline_step_details.py",
    ],
    "tooling": [
        "build_cli_settings.py",
    ],
    "testing": [
        "pipeline_smoke_test.py",
        "pipeline_golden_coverage.py",
        "pipeline_golden_coverage_test.py",
        "pipeline_dispatch_golden_test.py",
        "pipeline_routing_state_test.py",
        "routing_state_parity_test.py",
        "feature_status_test.py",
        "pipeline_runtime_test.py",
        "pipeline_registry_test.py",
        "pipeline_pack_test.py",
        "pipeline_predicates_test.py",
        "pipeline_routing_codegen_test.py",
    ],
}

DOCS = [
    "PIPELINE-COMPILE.md",
    "PIPELINE-ROUTING-STATE.md",
    "PIPELINE-PREDICATES.md",
    "PIPELINE-PACK-AUTHORING.md",
    "PIPELINE-STATUS.md",
    "PIPELINE-GOLDEN.md",
    "PIPELINE-PARITY.md",
    "PIPELINE-RUNTIME.md",
    "PIPELINE-ROUTER.md",
    "PIPELINE-REGISTRY.md",
]

BOOTSTRAP = textwrap.dedent(
    """
    import sys
    from pathlib import Path as _Path

    _SCRIPTS_ROOT = _Path(__file__).resolve().parents[1]
    if str(_SCRIPTS_ROOT) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS_ROOT))
    import _paths as _pipeline_paths

    _pipeline_paths.install()
    """
).strip("\n")


def launcher(subdir: str, name: str) -> str:
    return textwrap.dedent(
        f'''\
        #!/usr/bin/env python3
        """Launcher → scripts/{subdir}/{name} (layout reorganisation)."""
        from __future__ import annotations

        import runpy
        import sys
        from pathlib import Path

        _root = Path(__file__).resolve().parent
        _target = _root / "{subdir}" / "{name}"
        if str(_root) not in sys.path:
            sys.path.insert(0, str(_root))
        import _paths

        _paths.install()
        runpy.run_path(str(_target), run_name="__main__")
        '''
    )


def prepend_bootstrap(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "_pipeline_paths.install()" in text or "_paths.install()" in text:
        return
    marker = "from __future__ import annotations\n\n"
    if text.startswith(marker):
        text = text[len(marker) :]
    elif text.startswith("#!/usr/bin/env python3\n"):
        lines = text.splitlines(keepends=True)
        idx = 1
        if idx < len(lines) and lines[idx].strip() == "":
            idx += 1
        head = "".join(lines[:idx])
        rest = "".join(lines[idx:])
        path.write_text(head + BOOTSTRAP + "\n\n" + rest, encoding="utf-8")
        return
    path.write_text(BOOTSTRAP + "\n\n" + text, encoding="utf-8")


def main() -> None:
    for sub in LAYOUT:
        (ROOT / sub).mkdir(parents=True, exist_ok=True)
    (ROOT / "docs").mkdir(parents=True, exist_ok=True)

    for doc in DOCS:
        src = ROOT / doc
        if src.is_file():
            dest = ROOT / "docs" / doc
            if not dest.exists():
                shutil.move(str(src), str(dest))

    for subdir, names in LAYOUT.items():
        for name in names:
            src = ROOT / name
            if not src.is_file():
                continue
            dest = ROOT / subdir / name
            if dest.exists():
                continue
            shutil.move(str(src), str(dest))
            prepend_bootstrap(dest)
            launch = ROOT / name
            launch.write_text(launcher(subdir, name), encoding="utf-8")
            launch.chmod(0o755)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Pack ↔ dispatch-golden coverage (Phase 9).

Every ``pipelines/<id>/`` must have ``fixtures/dispatch_golden/<id>/cases.json``
or ``WAIVER.md`` (waiver only for packs without compiled dispatch rules).
Spec is the platform reference: no waiver, do not shrink the 24+ ids.
See PIPELINE-GOLDEN.md.
"""

from __future__ import annotations

import json
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
FIXTURES_DIR = SCRIPTS / "fixtures" / "dispatch_golden"
CASES_FILENAME = "cases.json"
WAIVER_FILENAME = "WAIVER.md"
SPEC_PIPELINE_ID = "spec"
DISPATCH_MIN_CASES = 1
SPEC_REQUIRED_CASE_IDS = frozenset(
    {
        "01-no-context",
        "02-no-spec",
        "03-spec-needs-check",
        "04-spec-newer-gaps-map",
        "05-open-gaps",
        "06-needs-answer-gaps",
        "07-pending-apply-gaps",
        "08-needs-answer-challenges",
        "09-open-challenges",
        "10-no-challenges-file",
        "11-no-alignment",
        "12-stale-alignment",
        "13-alignment-pass",
        "14-alignment-fail-mismatch",
        "15-alignment-limit-stopped",
        "16-graph-gate-run-log",
        "17-pending-apply-challenges",
        "18-spec-newer-challenges-map",
        "19-alignment-pass-with-gaps",
        "20-alignment-fail-no-critical-mismatch",
        "21-alignment-stale-mismatch",
        "22-needs-answer-alignment-only",
        "23-pending-apply-alignment-only",
        "24-mixed-pending-apply-align-ch",
        "32-ch-pending-leftover-gaps",
        "33-ch-needs-answer-leftover-gaps",
    }
)
SPEC_MIN_CASES = len(SPEC_REQUIRED_CASE_IDS)


def fixtures_dir_for(root: Path | None = None) -> Path:
    if root is None:
        return FIXTURES_DIR
    return Path(root) / "scripts" / "fixtures" / "dispatch_golden"


def list_golden_pipeline_ids(fixtures_dir: Path | None = None) -> list[str]:
    base = fixtures_dir or FIXTURES_DIR
    if not base.is_dir():
        return []
    return sorted(child.name for child in base.iterdir() if child.is_dir())


def load_case_ids(cases_path: Path) -> list[str]:
    if not cases_path.is_file():
        return []
    data = json.loads(cases_path.read_text(encoding="utf-8"))
    rows = data if isinstance(data, list) else [data]
    ids: list[str] = []
    for row in rows:
        if isinstance(row, dict) and row.get("id"):
            ids.append(str(row["id"]))
    return ids


def pack_dispatch_supported(pack: dict) -> bool:
    dispatch = pack.get("dispatch") or {}
    return bool(dispatch.get("rules") or dispatch.get("invariants"))


def has_waiver(golden_dir: Path) -> bool:
    waiver_path = golden_dir / WAIVER_FILENAME
    return waiver_path.is_file() and bool(waiver_path.read_text(encoding="utf-8").strip())


def _spec_reference_problems(
    case_ids: list[str],
    waived: bool,
    spec_min_cases: int,
    spec_required_ids: frozenset[str],
) -> list[str]:
    """Spec is the platform reference: no waiver, do not shrink the 24+ ids."""
    if not case_ids:
        if waived:
            return [
                f"{SPEC_PIPELINE_ID}: WAIVER.md is not allowed — "
                "spec is the platform reference"
            ]
        return [
            f"{SPEC_PIPELINE_ID}: missing {CASES_FILENAME} "
            f"(platform reference, ≥{spec_min_cases} cases)"
        ]
    problems: list[str] = []
    if len(case_ids) < spec_min_cases:
        problems.append(
            f"{SPEC_PIPELINE_ID}: do not shrink golden "
            f"({len(case_ids)} < {spec_min_cases})"
        )
    missing = spec_required_ids - set(case_ids)
    if missing:
        sample = ", ".join(sorted(missing)[:3])
        problems.append(f"{SPEC_PIPELINE_ID}: missing required case ids: {sample}")
    return problems


def golden_coverage_problems(
    *,
    pipeline_ids: list[str],
    fixtures_dir: Path,
    dispatch_supported_ids: set[str],
    spec_min_cases: int = SPEC_MIN_CASES,
    spec_required_ids: frozenset[str] = SPEC_REQUIRED_CASE_IDS,
) -> list[str]:
    """Return human-readable problems. Empty list = coverage ok."""
    problems: list[str] = []
    golden_ids = set(list_golden_pipeline_ids(fixtures_dir))
    known = set(pipeline_ids)

    for pipeline_id in pipeline_ids:
        golden_dir = fixtures_dir / pipeline_id
        cases_path = golden_dir / CASES_FILENAME
        try:
            case_ids = load_case_ids(cases_path)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            problems.append(f"{pipeline_id}: cannot read {CASES_FILENAME}: {exc}")
            continue
        waived = has_waiver(golden_dir)
        supported = pipeline_id in dispatch_supported_ids

        if pipeline_id == SPEC_PIPELINE_ID:
            problems.extend(
                _spec_reference_problems(
                    case_ids, waived, spec_min_cases, spec_required_ids
                )
            )
            continue

        if supported:
            if waived and not case_ids:
                problems.append(
                    f"{pipeline_id}: WAIVER.md is only for no-dispatch packs — "
                    f"add {CASES_FILENAME} (≥{DISPATCH_MIN_CASES} case)"
                )
            elif not case_ids:
                problems.append(
                    f"{pipeline_id}: missing {CASES_FILENAME} "
                    f"(dispatch_supported requires ≥{DISPATCH_MIN_CASES} golden case)"
                )
            elif len(case_ids) < DISPATCH_MIN_CASES:
                problems.append(
                    f"{pipeline_id}: {CASES_FILENAME} has {len(case_ids)} cases, "
                    f"need ≥{DISPATCH_MIN_CASES}"
                )
            continue

        if not case_ids and not waived:
            problems.append(
                f"{pipeline_id}: missing {CASES_FILENAME} or {WAIVER_FILENAME} "
                "(no-dispatch packs need one of the two)"
            )

    for orphan_id in sorted(golden_ids - known):
        problems.append(f"{orphan_id}: golden dir has no pack in pipelines/")

    return problems


def live_golden_coverage_problems(root: Path | None = None) -> list[str]:
    from pipeline_pack import discover_pipeline_ids, load_pack, repo_root

    base = root or repo_root()
    pipeline_ids = discover_pipeline_ids(base)
    load_errors: list[str] = []
    supported: set[str] = set()
    for pipeline_id in pipeline_ids:
        try:
            pack = load_pack(pipeline_id, base)
        except (OSError, ValueError, FileNotFoundError) as exc:
            load_errors.append(f"{pipeline_id}: cannot load pack: {exc}")
            continue
        if pack_dispatch_supported(pack):
            supported.add(pipeline_id)
    return load_errors + golden_coverage_problems(
        pipeline_ids=pipeline_ids,
        fixtures_dir=fixtures_dir_for(root),
        dispatch_supported_ids=supported,
    )


def coverage_detail(pipeline_ids: list[str], problems: list[str]) -> str:
    if problems:
        return "; ".join(problems[:3])
    return f"covered={','.join(pipeline_ids)}"

#!/usr/bin/env python3
"""write-feature adapter: catalog blocks → inner_cycle calls.

The mini-graph walker is inner_cycle.py. This file builds the call list
from approved sections and glues SPEC with catalog headers.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from artifact_paths import feature_dir, spec_path, workspace_root
from inner_cycle import (
    ACTION_ASSEMBLE,
    ACTION_DONE,
    ACTION_TASK,
    apply_assemble as apply_inner_assemble,
    next_cycle_at,
    next_inner_cycle,
)
from pipeline_common import write_cycle_config
from pipeline_pack import DEFAULT_PIPELINE_ID
from section_profiles import DEFAULT_PROFILE, infer_sections
from write_feature import (
    assemble_document,
    delete_working_files,
    list_active_blocks,
    part_filename,
)

CYCLE_PLAN_FILENAME = ".write-feature-cycle.json"


def cycle_plan_path(part_dir: Path) -> Path:
    return part_dir / CYCLE_PLAN_FILENAME


def load_cycle_plan(part_dir: Path) -> dict:
    path = cycle_plan_path(part_dir)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def save_cycle_plan(
    part_dir: Path,
    *,
    sections: str,
    profile: str | None = None,
    brief: str = "",
) -> Path:
    part_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "sections": sections,
        "profile": profile or DEFAULT_PROFILE,
        "brief": brief,
    }
    path = cycle_plan_path(part_dir)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _resolve_sections(
    *,
    brief: str,
    sections: str | None,
    profile: str | None,
    part_dir: Path,
) -> tuple[str, str | None, str | None]:
    plan = load_cycle_plan(part_dir)
    resolved_sections = sections or str(plan.get("sections") or "") or None
    resolved_profile = profile or str(plan.get("profile") or "") or None
    resolved_brief = brief or str(plan.get("brief") or "")
    return resolved_brief, resolved_sections, resolved_profile


def calls_from_plan(
    slug: str,
    part_dir: Path,
    *,
    brief: str = "",
    sections: str | None = None,
    profile: str | None = None,
    cycle: dict | None = None,
) -> tuple[list[dict], dict]:
    """Build inner-cycle calls from the approved spec-catalog blocks."""
    cycle = cycle or {}
    brief, sections, profile = _resolve_sections(
        brief=brief, sections=sections, profile=profile, part_dir=part_dir
    )
    target = infer_sections(brief, sections, profile)
    subagent = str(cycle.get("subagent") or write_cycle_config().get("subagent") or "spec-writer")
    calls: list[dict] = []
    for block in list_active_blocks(target):
        param = str(block["id"])
        calls.append(
            {
                "agent": subagent,
                "param": param,
                "artifact": part_filename(slug, param),
                "skills": list(block.get("active_skills") or []),
            }
        )
    extra = {
        "sections": ",".join(target),
        "brief": brief,
        "assemble": str(cycle.get("assemble") or "write_feature"),
    }
    return calls, extra


def apply_write_feature_assemble(decision: dict) -> dict:
    slug = str(decision["slug"])
    part_dir = Path(str(decision["part_dir"]))
    out = Path(str(decision["out"]))
    sections = str(decision.get("sections") or "") or None
    brief = str(decision.get("brief") or "")
    result = assemble_document(
        brief,
        section_id=sections,
        feature_name=slug,
        part_dir=part_dir,
        profile=None,
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(result.document, encoding="utf-8")
    deleted: list[str] = []
    if not result.missing_parts:
        deleted = delete_working_files(part_dir, slug)
    return {
        "written": str(out),
        "missing_parts": result.missing_parts,
        "deleted": deleted,
    }


def apply_assemble(decision: dict) -> dict:
    if decision.get("assemble") in (None, "", "write_feature"):
        if decision.get("action") != ACTION_ASSEMBLE:
            raise ValueError(f"assemble only when action=assemble, got {decision.get('action')!r}")
        decision = {**decision, "assemble": "write_feature"}
    return apply_inner_assemble(decision)


def next_write_cycle(
    slug: str,
    part_dir: Path,
    *,
    brief: str = "",
    sections: str | None = None,
    profile: str | None = None,
    pipeline_id: str = DEFAULT_PIPELINE_ID,
    spec_file: Path | None = None,
) -> dict:
    cycle = write_cycle_config(pipeline_id)
    try:
        from inner_cycle import cycle_config_for_step

        graph_cycle = cycle_config_for_step(pipeline_id, str(cycle.get("step") or "write-feature"))
        if graph_cycle:
            cycle = {**cycle, **graph_cycle}
    except Exception:  # noqa: BLE001
        pass
    calls, extra = calls_from_plan(
        slug, part_dir, brief=brief, sections=sections, profile=profile, cycle=cycle
    )
    out_spec = spec_file or (part_dir / f"{slug}.md")
    decision = next_inner_cycle(
        slug,
        part_dir,
        calls=calls,
        out=out_spec,
        assemble=str(extra.get("assemble") or "write_feature"),
    )
    if decision.get("action") == ACTION_TASK:
        decision["sections"] = extra["sections"]
        decision["skills"] = next(
            (item.get("skills") or [] for item in calls if item.get("param") == decision.get("param")),
            decision.get("skills") or [],
        )
        decision["check"] = {
            "mode": "check-part",
            "block_id": decision.get("param"),
            "sections": extra["sections"],
        }
    if decision.get("action") == ACTION_ASSEMBLE:
        decision["sections"] = extra["sections"]
        decision["brief"] = extra["brief"]
    return decision


def next_write_cycle_at(
    slug: str,
    *,
    root: Path | None = None,
    part_dir: Path | None = None,
    brief: str = "",
    sections: str | None = None,
    profile: str | None = None,
    pipeline_id: str = DEFAULT_PIPELINE_ID,
) -> dict:
    root = (root or workspace_root()).resolve()
    if part_dir is not None:
        decision = next_write_cycle(
            slug,
            part_dir,
            brief=brief,
            sections=sections,
            profile=profile,
            pipeline_id=pipeline_id,
            spec_file=spec_path(root, slug) if part_dir == feature_dir(root, slug) else part_dir / f"{slug}.md",
        )
        from inner_cycle import cycle_config_for_step

        cfg = cycle_config_for_step(pipeline_id, str(write_cycle_config(pipeline_id).get("step") or "write-feature"))
        decision.setdefault("root", str(root))
        decision.setdefault("step", str(cfg.get("step") or "write-feature"))
        decision.setdefault("pipeline_id", pipeline_id)
        return decision
    return next_cycle_at(
        slug,
        root=root,
        pipeline_id=pipeline_id,
        brief=brief,
        sections=sections,
        profile=profile,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slug", help="Feature slug")
    parser.add_argument("--workspace", type=Path, default=None)
    parser.add_argument("--part-dir", type=Path, default=None)
    parser.add_argument("--brief", default="")
    parser.add_argument("--sections", default=None)
    parser.add_argument("--profile", default=None)
    parser.add_argument("--pipeline", default=DEFAULT_PIPELINE_ID)
    parser.add_argument("--save-plan", action="store_true", help="Write .write-feature-cycle.json")
    parser.add_argument("--assemble", action="store_true", help="If next is assemble, write SPEC")
    args = parser.parse_args(argv)

    root = (args.workspace or workspace_root()).resolve()
    folder = args.part_dir or feature_dir(root, args.slug)
    if args.save_plan:
        if not args.sections:
            parser.error("--save-plan requires --sections")
        path = save_cycle_plan(
            folder, sections=args.sections, profile=args.profile, brief=args.brief
        )
        print(json.dumps({"saved": str(path)}, ensure_ascii=False))
        return 0

    decision = next_write_cycle_at(
        args.slug,
        root=root,
        part_dir=folder,
        brief=args.brief,
        sections=args.sections,
        profile=args.profile,
        pipeline_id=args.pipeline,
    )
    if args.assemble:
        if decision.get("action") != ACTION_ASSEMBLE:
            print(json.dumps(decision, ensure_ascii=False, indent=2))
            return 1
        applied = apply_assemble(decision)
        decision = next_write_cycle_at(
            args.slug,
            root=root,
            part_dir=folder,
            brief=args.brief,
            sections=args.sections,
            profile=args.profile,
            pipeline_id=args.pipeline,
        )
        decision["assembled"] = applied
        if decision.get("action") == ACTION_DONE and not (applied.get("cell_closed") or {}).get("closed"):
            from inner_cycle import close_cycle_cell, cycle_config_for_step

            cfg = cycle_config_for_step(
                args.pipeline,
                str(write_cycle_config(args.pipeline).get("step") or "write-feature"),
            )
            decision["cell_closed"] = close_cycle_cell(
                root,
                args.slug,
                str(cfg.get("step") or "write-feature"),
                pipeline_id=args.pipeline,
            )
    print(json.dumps(decision, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

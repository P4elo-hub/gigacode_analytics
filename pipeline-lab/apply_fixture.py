#!/usr/bin/env python3
"""Copy a lab fixture into pipeline-lab workspace by (slug, step, variant)."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

LAB_ROOT = Path(__file__).resolve().parent
FIXTURES_DIR = LAB_ROOT / "fixtures"
SCENARIOS_DIR = LAB_ROOT / "scenarios"
CURSOR_NAME = ".lab-cursor.json"
VARIANTS = ("ok", "fail", "retry", "empty", "dirty", "pending-apply")

STEP_TO_SUBAGENT = {
    "find-context": "context-researcher",
    "write-feature": "spec-writer",
    "analyze-routing": "routing-analyzer",
    "check-feature": "spec-reviewer",
    "resolve-gaps": "gap-resolver",
    "challenge-feature": "spec-challenger",
    "resolve-challenges": "challenge-resolver",
    "check-feature-code": "code-auditor",
    "resolve-code-alignment": "alignment-resolver",
}

# Generic fixture names → destination under workspace (slug substituted later).
GENERIC_DEST = {
    "last_message.txt": "Feature-writing/{slug}/last_message.txt",
    "context.md": "Feature-context/{slug}.md",
    "discovery.md": "Feature-context/{slug}-discovery.md",
    "spec.md": "Feature-writing/{slug}/{slug}.md",
    "check.md": "Feature-writing/{slug}/{slug}-check.md",
    "decisions.md": "Feature-writing/{slug}/{slug}-decisions.md",
    "gaps-resolved.md": "Feature-writing/{slug}/{slug}-gaps-resolved.md",
    "challenges.md": "Feature-writing/{slug}/{slug}-challenges.md",
    "challenges-resolved.md": "Feature-writing/{slug}/{slug}-challenges-resolved.md",
    "code-alignment.md": "Feature-writing/{slug}/{slug}-code-alignment.md",
    "routing-state.json": "Feature-writing/{slug}/{slug}-routing-state.json",
}

STEP_FILES: dict[str, tuple[str, ...]] = {
    "find-context": ("context.md", "last_message.txt"),
    "write-feature": ("spec.md", "last_message.txt"),
    "analyze-routing": ("routing-state.json", "last_message.txt"),
    "check-feature": ("spec.md", "check.md", "routing-state.json", "last_message.txt"),
    "resolve-gaps": ("spec.md", "gaps-resolved.md", "decisions.md", "routing-state.json", "last_message.txt"),
    "challenge-feature": ("challenges.md", "last_message.txt"),
    "resolve-challenges": ("challenges.md", "challenges-resolved.md", "decisions.md", "last_message.txt"),
    "resolve-code-alignment": ("spec.md", "code-alignment.md", "decisions.md", "last_message.txt"),
    "check-feature-code": ("code-alignment.md", "last_message.txt"),
}


def fixture_dir(step: str, variant: str) -> Path:
    return FIXTURES_DIR / step / variant


def cursor_file(workspace: Path, slug: str) -> Path:
    return workspace / "Feature-writing" / slug / CURSOR_NAME


def parse_cursor_doc(raw: object) -> dict:
    if isinstance(raw, list):
        return {"ticks": raw, "tick": 0}
    if not isinstance(raw, dict):
        raise ValueError("cursor must be a list or object")
    if "ticks" in raw:
        ticks = raw["ticks"]
        if not isinstance(ticks, list):
            raise ValueError("cursor.ticks must be a list")
        data = dict(raw)
        data["ticks"] = ticks
        data["tick"] = int(raw.get("tick") or 0)
        return data
    if raw.get("variant"):
        return {
            "ticks": [{"step": raw.get("step"), "variant": raw["variant"]}],
            "tick": int(raw.get("tick") or 0),
        }
    raise ValueError("cursor needs ticks[] or variant")


def load_cursor(workspace: Path, slug: str) -> tuple[dict | None, Path | None]:
    path = cursor_file(workspace, slug)
    if path.is_file():
        return parse_cursor_doc(json.loads(path.read_text(encoding="utf-8"))), path
    scenario = SCENARIOS_DIR / slug / "cursor.json"
    if scenario.is_file():
        return parse_cursor_doc(json.loads(scenario.read_text(encoding="utf-8"))), None
    return None, None


def save_cursor(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def resolve_variant_from_cursor(
    slug: str,
    step: str,
    workspace: Path,
) -> tuple[str, dict | None, Path | None]:
    data, path = load_cursor(workspace, slug)
    if data is None:
        return "ok", None, None
    ticks = data["ticks"]
    tick = int(data.get("tick") or 0)
    if tick >= len(ticks):
        raise ValueError(f"{slug}: cursor exhausted (tick {tick} >= {len(ticks)})")
    current = ticks[tick]
    if not isinstance(current, dict):
        raise ValueError(f"{slug}: cursor tick {tick} is not an object")
    cur_step = str(current.get("step") or "")
    variant = str(current.get("variant") or "")
    if cur_step and cur_step != step:
        raise ValueError(
            f"{slug}: cursor tick {tick} step {cur_step!r} != requested {step!r}"
        )
    if variant not in VARIANTS:
        raise ValueError(f"{slug}: cursor tick {tick} has unknown variant {variant!r}")
    return variant, data, path


def advance_cursor(
    data: dict,
    path: Path | None,
    *,
    workspace: Path,
    slug: str,
) -> dict:
    updated = dict(data)
    updated["tick"] = int(data.get("tick") or 0) + 1
    dest = path or cursor_file(workspace, slug)
    save_cursor(dest, updated)
    return updated


def last_message_for(step: str, variant: str) -> str:
    if variant == "ok":
        return f"{step} completed. Quality gates PASS · fail 0 · warn 0.\n"
    if variant == "fail":
        return f"{step} failed: timeout\n"
    if variant == "retry":
        return f"ASK_PARENT — retry {step} after needs-answer in DECISIONS.\n"
    if variant == "empty":
        return ""
    if variant == "dirty":
        return f"{step} completed with gaps. Quality gates PASS · fail 0.\n"
    if variant == "pending-apply":
        return f"{step} completed. DECISIONS pending-apply is ready; apply before check-feature.\n"
    raise ValueError(f"unknown variant: {variant}")


def _routing_state(*, slug: str, variant: str, step: str) -> str:
    if variant == "empty":
        return ""
    gaps = ["GAP-LAB-01"] if variant == "dirty" else []
    pending = variant == "pending-apply"
    has_challenges = pending or (
        step in {"challenge-feature", "resolve-challenges"}
        and variant not in {"empty", "retry", "fail"}
    )
    needs_answer = 1 if variant == "retry" and step != "challenge-feature" else 0
    needs_check = False
    needs_reason = ""
    if pending:
        needs_check = True
        needs_reason = "нет check-feature после последней правки SPEC"
    elif variant in {"fail", "dirty"} and step != "check-feature":
        needs_check = True
        needs_reason = "open gaps" if gaps else ""
    elif variant == "ok" and step == "resolve-gaps":
        # After apply, SPEC changed — invariant should re-queue check-feature.
        needs_check = True
        needs_reason = "нет check-feature после последней правки SPEC"
    payload = {
        "schema_version": 1,
        "slug": slug,
        "generated_at": "2026-01-01T00:00:00Z",
        "step_completion": {},
        "fields": {
            "has_context": True,
            "has_spec": True,
            "has_decisions": pending
            or step in {"resolve-gaps", "resolve-challenges", "resolve-code-alignment"},
            "has_gaps_map": step == "resolve-gaps" and variant != "empty",
            "has_challenges": has_challenges,
            "has_challenges_map": step == "resolve-challenges" and variant == "ok",
            "has_alignment": step in {"check-feature-code", "resolve-code-alignment"}
            and variant not in {"empty", "fail"},
            "decisions_needs_answer": needs_answer,
            "decisions_pending_apply": 1 if pending else 0,
            "decisions_needs_answer_alignment": 0,
            "decisions_pending_apply_alignment": 0,
            "open_gaps": gaps,
            "open_questions": ["Q-01"] if variant == "dirty" and step == "find-context" else [],
            "challenges": {
                "open": 1 if variant == "dirty" and step in {"challenge-feature", "resolve-challenges"} else 0,
                "deferred": 0,
                "resolved": 1 if variant == "ok" and step == "resolve-challenges" else 0,
                "covered": 0,
                "open_critical": 1 if variant == "dirty" and step == "challenge-feature" else 0,
                "open_major": 0,
            },
            "verdict": "PASS" if variant == "ok" and step == "check-feature-code" else "",
            "alignment_iteration": 1 if step in {"check-feature-code", "resolve-code-alignment"} else 0,
            "critical_major_mismatch": 1 if variant == "dirty" and step == "check-feature-code" else 0,
            "alignment_stale": False,
            "stale": [],
            "needs_check_feature": needs_check,
            "needs_check_feature_reason": needs_reason,
        },
    }
    if step == "check-feature" and variant != "pending-apply":
        payload["fields"]["needs_check_feature"] = variant == "fail"
        payload["fields"]["needs_check_feature_reason"] = "timeout" if variant == "fail" else ""
        if variant == "ok":
            payload["step_completion"] = {"check-feature": {"result": "ok"}}
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def _spec(*, slug: str, variant: str) -> str:
    if variant == "empty":
        return ""
    if variant == "fail":
        return f"# {slug}\n\n(incomplete — step failed)\n"
    if variant == "dirty":
        return (
            f"# {slug}\n\n"
            f"Стендовый spec. Открытый факт: [GAP-LAB-01] не закрыт.\n"
        )
    if variant == "retry":
        return f"# {slug}\n\nSpec ждёт ответ в DECISIONS (needs-answer).\n"
    return f"# {slug}\n\nТребование стенда без открытых GAP.\n"


def _check_report(*, slug: str, variant: str) -> str:
    if variant == "empty":
        return ""
    if variant == "fail":
        return f"# {slug}-check\n\nFAIL: timeout\n"
    if variant == "dirty":
        return f"# {slug}-check\n\nOpen gaps: GAP-LAB-01\n"
    if variant == "retry":
        return f"# {slug}-check\n\nASK_PARENT — retry after needs-answer.\n"
    return f"# {slug}-check\n\nPASS · fail 0 · warn 0\n"


def _context(*, slug: str, variant: str) -> str:
    if variant == "empty":
        return ""
    if variant == "dirty":
        return f"# {slug}\n\nVerified lab context.\n\n## Открытые вопросы\n\n- Q-01: стендовый вопрос\n"
    if variant == "fail":
        return f"# {slug}\n\n(incomplete — find-context failed)\n"
    return f"# {slug}\n\nVerified lab context. Нет открытых Q-XX.\n"


def _decisions(*, slug: str, variant: str) -> str:
    if variant == "empty":
        return ""
    if variant == "pending-apply":
        status = "pending-apply"
        decision = "A: стенд"
    elif variant == "retry":
        status = "needs-answer"
        decision = ""
    else:
        status = "applied"
        decision = "A: стенд"
    relates = "CH-01" if variant == "pending-apply" else "GAP-LAB-01, Q-01"
    return (
        f"# {slug}-decisions\n\n"
        "| ID | Relates | Prompt | Options | Decision | Status | Date |\n"
        "|----|---------|--------|---------|----------|--------|------|\n"
        f"| D-01 | {relates} | Стенд? | A) да; B) нет | {decision} | {status} | 2026-01-01 |\n"
    )


def _gaps_map(*, slug: str, variant: str) -> str:
    if variant == "empty":
        return ""
    if variant == "dirty":
        return f"# {slug}-gaps-resolved\n\nОстался [GAP-LAB-01].\n"
    return f"# {slug}-gaps-resolved\n\nЗакрыто: GAP-LAB-01.\n"


def _challenges(*, slug: str, variant: str) -> str:
    if variant == "empty":
        return ""
    if variant == "dirty":
        return f"# {slug}-challenges\n\n| ID | Severity | Status |\n|----|----------|--------|\n| CH-01 | Critical | open |\n"
    return f"# {slug}-challenges\n\n| ID | Severity | Status |\n|----|----------|--------|\n| CH-01 | Minor | covered |\n"


def _challenges_map(*, slug: str, variant: str) -> str:
    if variant == "empty":
        return ""
    return f"# {slug}-challenges-resolved\n\nCH-01 → covered.\n"


def _alignment(*, slug: str, variant: str) -> str:
    if variant == "empty":
        return ""
    if variant == "dirty":
        return f"# {slug}-code-alignment\n\nVerdict: FAIL\n\nMISMATCH Critical: стенд.\n"
    if variant == "fail":
        return f"# {slug}-code-alignment\n\n(incomplete — timeout)\n"
    return f"# {slug}-code-alignment\n\nVerdict: PASS\n"


_BODIES = {
    "last_message.txt": lambda slug, variant, step: last_message_for(step, variant),
    "spec.md": lambda slug, variant, step: _spec(slug=slug, variant=variant),
    "check.md": lambda slug, variant, step: _check_report(slug=slug, variant=variant),
    "context.md": lambda slug, variant, step: _context(slug=slug, variant=variant),
    "decisions.md": lambda slug, variant, step: _decisions(slug=slug, variant=variant),
    "gaps-resolved.md": lambda slug, variant, step: _gaps_map(slug=slug, variant=variant),
    "challenges.md": lambda slug, variant, step: _challenges(slug=slug, variant=variant),
    "challenges-resolved.md": lambda slug, variant, step: _challenges_map(slug=slug, variant=variant),
    "code-alignment.md": lambda slug, variant, step: _alignment(slug=slug, variant=variant),
    "routing-state.json": lambda slug, variant, step: _routing_state(slug=slug, variant=variant, step=step),
}


def library_contents(step: str, variant: str, *, slug: str = "__SLUG__") -> dict[str, str]:
    if step not in STEP_FILES:
        raise ValueError(f"unknown step: {step}")
    if variant not in VARIANTS:
        raise ValueError(f"unknown variant: {variant}")
    files: dict[str, str] = {}
    for name in STEP_FILES[step]:
        files[name] = _BODIES[name](slug, variant, step)
    if step == "challenge-feature" and variant in {
        "ok",
        "dirty",
        "pending-apply",
        "retry",
        "fail",
    }:
        files.setdefault(
            "routing-state.json",
            _routing_state(slug=slug, variant=variant, step=step),
        )
    # Sixth variant is not in the session-2 matrix; assemble DECISIONS + routing-state
    # so overlay P60–70 can fire without changing ok/fail/retry/empty/dirty bodies.
    if variant == "pending-apply":
        files.setdefault("decisions.md", _decisions(slug=slug, variant=variant))
        files.setdefault(
            "routing-state.json",
            _routing_state(slug=slug, variant=variant, step=step),
        )
    return files


def write_library(root: Path | None = None) -> list[Path]:
    fixtures = (root or LAB_ROOT) / "fixtures"
    written: list[Path] = []
    if fixtures.exists():
        shutil.rmtree(fixtures)
    for step in STEP_FILES:
        for variant in VARIANTS:
            dest = fixtures / step / variant
            dest.mkdir(parents=True)
            for name, body in library_contents(step, variant).items():
                path = dest / name
                path.write_text(body, encoding="utf-8")
                written.append(path)
    return written


def rewrite_body(text: str, slug: str) -> str:
    return text.replace("__SLUG__", slug)


def dest_path(workspace: Path, slug: str, generic_name: str) -> Path:
    rel = GENERIC_DEST.get(generic_name)
    if rel is None:
        return workspace / "Feature-writing" / slug / generic_name
    return workspace / rel.format(slug=slug)


def apply_fixture(
    slug: str,
    step: str,
    variant: str | None = None,
    *,
    workspace: Path | None = None,
) -> dict:
    if not slug.startswith("lab-"):
        raise ValueError(f"lab slug must start with lab-, got {slug!r}")
    if step not in STEP_FILES:
        raise ValueError(f"unknown step: {step}")
    workspace = (workspace or LAB_ROOT).resolve()
    cursor_data: dict | None = None
    cursor_path: Path | None = None
    if variant is None:
        variant, cursor_data, cursor_path = resolve_variant_from_cursor(
            slug, step, workspace
        )
    if variant not in VARIANTS:
        raise ValueError(f"unknown variant: {variant}")
    src = fixture_dir(step, variant)
    if not src.is_dir():
        raise FileNotFoundError(f"fixture not found: {src}")
    copied: list[str] = []
    last_message = ""
    routing_dest: Path | None = None
    files = [
        path
        for path in src.iterdir()
        if path.is_file() and not path.name.startswith(".")
    ]
    files.sort(key=lambda path: (path.name == "routing-state.json", path.name))
    for path in files:
        body = rewrite_body(path.read_text(encoding="utf-8"), slug)
        dest = dest_path(workspace, slug, path.name)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(body, encoding="utf-8")
        copied.append(str(dest.relative_to(workspace)))
        if path.name == "last_message.txt":
            last_message = body
        if path.name == "routing-state.json":
            routing_dest = dest
    if routing_dest is not None and routing_dest.is_file():
        # Keep JSON from looking stale vs artifacts written in the same tick.
        now = routing_dest.stat().st_mtime
        os.utime(routing_dest, (now + 1, now + 1))
    if cursor_data is not None:
        advance_cursor(
            cursor_data, cursor_path, workspace=workspace, slug=slug
        )
    return {
        "slug": slug,
        "step": step,
        "variant": variant,
        "subagent": STEP_TO_SUBAGENT[step],
        "copied": copied,
        "last_message": last_message,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slug", help="lab-* slug")
    parser.add_argument("--step", choices=sorted(STEP_FILES))
    parser.add_argument(
        "--variant",
        choices=VARIANTS,
        help="Fixture variant. Omit to read Feature-writing/<slug>/.lab-cursor.json",
    )
    parser.add_argument("--workspace", type=Path, default=LAB_ROOT)
    parser.add_argument(
        "--write-library",
        action="store_true",
        help="Regenerate pipeline-lab/fixtures/ from templates",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Do not print last_message to stdout",
    )
    args = parser.parse_args(argv)

    if args.write_library:
        written = write_library(LAB_ROOT)
        print(f"wrote {len(written)} fixture files under {FIXTURES_DIR}", file=sys.stderr)
        return 0

    if not (args.slug and args.step):
        parser.error("--slug --step are required (unless --write-library)")

    result = apply_fixture(
        args.slug,
        args.step,
        args.variant,
        workspace=args.workspace,
    )
    if not args.quiet:
        sys.stdout.write(result["last_message"])
        if result["last_message"] and not result["last_message"].endswith("\n"):
            sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

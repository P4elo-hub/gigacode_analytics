#!/usr/bin/env python3
"""Merge settings.base.json + settings.hooks.json → settings.json (Qwen / GigaCode)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CLI_DIRS = {
    "qwen": ROOT / ".qwen",
    "gigacode": ROOT / ".gigacode",
}

REQUIRED_ALLOW = (
    "Bash(python3 scripts/*)",
    "Bash(python3 *)",
    "Agent(spec-writer)",
    "Agent(spec-reviewer)",
    "Agent(code-auditor)",
)

REQUIRED_HOOK_EVENTS = ("PreToolUse", "SubagentStop")


def load_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected JSON object")
    return data


def merge_settings(base: dict, hooks_doc: dict) -> dict:
    merged = dict(base)
    hooks = hooks_doc.get("hooks")
    if not isinstance(hooks, dict):
        raise ValueError("settings.hooks.json must contain a hooks object")
    merged["hooks"] = hooks
    return merged


def validate_settings(settings: dict, cli: str) -> list[str]:
    errors: list[str] = []
    permissions = settings.get("permissions")
    if not isinstance(permissions, dict):
        errors.append("missing permissions block")
        return errors

    allow = permissions.get("allow")
    if not isinstance(allow, list) or len(allow) < 10:
        errors.append(f"permissions.allow too short ({len(allow) if isinstance(allow, list) else 0})")
    else:
        for item in REQUIRED_ALLOW:
            if item not in allow:
                errors.append(f"missing allow: {item}")

    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        errors.append("missing hooks block")
    else:
        for event in REQUIRED_HOOK_EVENTS:
            if event not in hooks:
                errors.append(f"missing hooks.{event}")

    context = settings.get("context")
    if not isinstance(context, dict) or not context.get("fileName"):
        errors.append("missing context.fileName")

    if cli == "qwen" and "QWEN.md" not in (context or {}).get("fileName", []):
        errors.append("context.fileName must include QWEN.md")
    if cli == "gigacode" and "GIGACODE.md" not in (context or {}).get("fileName", []):
        errors.append("context.fileName must include GIGACODE.md")

    return errors


def build_cli_settings(cli: str, *, write: bool = True) -> dict:
    cli_dir = CLI_DIRS.get(cli)
    if cli_dir is None:
        raise ValueError(f"unknown cli: {cli}")

    base_path = cli_dir / "settings.base.json"
    hooks_path = cli_dir / "settings.hooks.json"
    out_path = cli_dir / "settings.json"

    merged = merge_settings(load_json(base_path), load_json(hooks_path))
    errors = validate_settings(merged, cli)
    if errors:
        raise SystemExit(f"{cli} settings invalid:\n- " + "\n- ".join(errors))

    if write:
        out_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return merged


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cli",
        choices=tuple(CLI_DIRS),
        action="append",
        dest="clis",
        help="CLI to build (default: all)",
    )
    parser.add_argument("--check", action="store_true", help="Validate settings.json without writing")
    args = parser.parse_args(argv)

    clis = args.clis or list(CLI_DIRS)
    for cli in clis:
        cli_dir = CLI_DIRS[cli]
        if args.check:
            path = cli_dir / "settings.json"
            if not path.is_file():
                print(f"[FAIL] {cli}: missing {path}", file=sys.stderr)
                return 1
            errors = validate_settings(load_json(path), cli)
            if errors:
                print(f"[FAIL] {cli}:", file=sys.stderr)
                for err in errors:
                    print(f"  - {err}", file=sys.stderr)
                return 1
            print(f"[OK] {cli}: settings.json")
        else:
            build_cli_settings(cli, write=True)
            print(f"[OK] {cli}: wrote {cli_dir / 'settings.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

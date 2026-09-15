#!/usr/bin/env python3
"""SubagentStop matcher must include every pack gated_subagent (else no run-log)."""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

from pipeline_common import load_pipeline_registry  # noqa: E402

CLI_HOOKS = (
    ROOT / ".qwen" / "settings.hooks.json",
    ROOT / ".gigacode" / "settings.hooks.json",
)


def _matcher_names(path: Path) -> set[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for block in (data.get("hooks") or {}).get("SubagentStop") or []:
        matcher = str(block.get("matcher") or "")
        match = re.fullmatch(r"\^\((.*)\)\$", matcher)
        body = match.group(1) if match else matcher
        names.update(part for part in body.split("|") if part)
    return names


class SubagentStopMatcherTest(unittest.TestCase):
    def test_matcher_covers_all_gated_subagents(self) -> None:
        gated: set[str] = set()
        for pipe in (load_pipeline_registry().get("pipelines") or {}).values():
            if isinstance(pipe, dict):
                gated.update(str(name) for name in (pipe.get("gated_subagents") or []) if name)
        self.assertIn("routing-analyzer", gated)
        for path in CLI_HOOKS:
            missing = sorted(gated - _matcher_names(path))
            self.assertFalse(missing, msg=f"{path.name} SubagentStop missing {missing}")


if __name__ == "__main__":
    unittest.main()

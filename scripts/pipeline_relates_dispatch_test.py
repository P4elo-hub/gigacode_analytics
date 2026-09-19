#!/usr/bin/env python3
"""CH pending-apply + leftover GAP must dispatch to resolve-challenges, not gaps."""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from feature_status import FeatureStatus  # noqa: E402
from pipeline_dispatch import build_dispatch  # noqa: E402
from pipeline_routing_state import example_payload, routing_state_path  # noqa: E402
from pipeline_status import populate_status  # noqa: E402

SLUG = "relates-steal"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _seed_ch_pending_leftover(root: Path, *, status_flag: str) -> None:
    fw = root / "Feature-writing" / SLUG
    _write(root / "Feature-context" / f"{SLUG}.md", "# Context\n\nVerified.\n")
    _write(
        fw / f"{SLUG}.md",
        "# spec\n\nLeftover marker [GAP-LEFTOVER] after resolve-gaps asked.\n",
    )
    _write(fw / f"{SLUG}-gaps-resolved.md", "# GAPS_MAP\n")
    _write(
        fw / f"{SLUG}-challenges.md",
        "# CH\n\n"
        "| ID | § | Q | type | severity | status |\n"
        "|----|---|----|-----|----------|--------|\n"
        "| CH-13 | §1 | q | t | Minor | open |\n",
    )
    _write(
        fw / f"{SLUG}-decisions.md",
        "# DECISIONS\n\n"
        "| ID | Relates | Prompt | Options | Decision | Status | Date |\n"
        "|----|---------|--------|---------|----------|--------|------|\n"
        f"| D-01 | CH-13 | leftover? | A) apply | A | {status_flag} | 2026-09-19 |\n",
    )
    payload = example_payload(SLUG, open_gaps=["GAP-LEFTOVER"])
    fields = payload["fields"]
    fields["has_context"] = True
    fields["has_spec"] = True
    fields["has_decisions"] = True
    fields["has_gaps_map"] = True
    fields["has_challenges"] = True
    fields["needs_check_feature"] = True
    fields["needs_check_feature_reason"] = "нет check-feature после последней правки SPEC"
    if status_flag == "pending-apply":
        fields["decisions_pending_apply"] = 1
        fields["decisions_pending_apply_gaps"] = 1
        fields["decisions_pending_apply_challenges"] = 0
    else:
        fields["decisions_needs_answer"] = 1
        fields["decisions_needs_answer_gaps"] = 1
        fields["decisions_needs_answer_challenges"] = 0
    path = routing_state_path(root, SLUG)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    newer = time.time() + 60
    os.utime(path, (newer, newer))


class RelatesDispatchStealTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="relates-dispatch-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_overlay_recomputes_ch_pending_despite_json_gaps_bucket(self) -> None:
        _seed_ch_pending_leftover(self.tmp, status_flag="pending-apply")
        status = FeatureStatus(slug=SLUG)
        populate_status(status, self.tmp, SLUG, "spec")
        self.assertEqual(status.decisions_pending_apply, 1)
        self.assertEqual(status.decisions_pending_apply_gaps, 0)
        self.assertEqual(status.decisions_pending_apply_challenges, 1)
        self.assertEqual(status.open_gaps, ["GAP-LEFTOVER"])

    def test_pending_ch_plus_leftover_gap_goes_to_resolve_challenges(self) -> None:
        _seed_ch_pending_leftover(self.tmp, status_flag="pending-apply")
        dispatch = build_dispatch(self.tmp, SLUG, "spec")
        self.assertEqual(dispatch["next_step"], "resolve-challenges")
        self.assertEqual(dispatch["next_subagent"], "challenge-resolver")
        self.assertEqual(dispatch["orchestrator_mode"], "delegate")
        self.assertNotEqual(dispatch["next_step"], "resolve-gaps")

    def test_needs_answer_ch_plus_leftover_gap_goes_to_resolve_challenges(self) -> None:
        _seed_ch_pending_leftover(self.tmp, status_flag="needs-answer")
        dispatch = build_dispatch(self.tmp, SLUG, "spec")
        self.assertEqual(dispatch["next_step"], "resolve-challenges")
        self.assertEqual(dispatch["orchestrator_mode"], "ask_user")
        self.assertNotEqual(dispatch["next_step"], "resolve-gaps")


if __name__ == "__main__":
    unittest.main()

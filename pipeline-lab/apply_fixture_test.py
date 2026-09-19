#!/usr/bin/env python3
"""Session 2 criterion: apply_fixture copies artifacts; hook no longer judges last_message quality."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

LAB = Path(__file__).resolve().parent
REPO = LAB.parent
sys.path.insert(0, str(LAB))
sys.path.insert(0, str(REPO / "scripts"))

from apply_fixture import apply_fixture  # noqa: E402
from pipeline_after_subagent import infer_result  # noqa: E402

EXPECTED_DIRTY = (
    "Feature-writing/lab-demo/lab-demo.md",
    "Feature-writing/lab-demo/lab-demo-check.md",
    "Feature-writing/lab-demo/lab-demo-routing-state.json",
    "Feature-writing/lab-demo/last_message.txt",
)

# Fixtures still differ in text; hook treats all as finished unless CLI abort.
VARIANT_RESULT = {
    "ok": "ok",
    "empty": "ok",
    "fail": "ok",
    "retry": "ok",
    "dirty": "ok",
}


class ApplyFixtureCriterionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="lab-demo-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_dirty_creates_canonical_files(self) -> None:
        result = apply_fixture("lab-demo", "check-feature", "dirty", workspace=self.tmp)
        for rel in EXPECTED_DIRTY:
            path = self.tmp / rel
            self.assertTrue(path.is_file(), msg=rel)
        spec = (self.tmp / "Feature-writing/lab-demo/lab-demo.md").read_text(encoding="utf-8")
        self.assertIn("[GAP-LAB-01]", spec)
        routing = (self.tmp / "Feature-writing/lab-demo/lab-demo-routing-state.json").read_text(
            encoding="utf-8"
        )
        self.assertIn("GAP-LAB-01", routing)
        self.assertIn("lab-demo", routing)
        self.assertEqual(infer_result(result["last_message"]), "ok")

    def test_variant_last_messages_infer_apart(self) -> None:
        seen: dict[str, str] = {}
        for variant, expected in VARIANT_RESULT.items():
            result = apply_fixture("lab-demo", "check-feature", variant, workspace=self.tmp)
            message = result["last_message"]
            inferred = infer_result(message)
            self.assertEqual(inferred, expected, msg=f"{variant!r}: {message!r} → {inferred}")
            seen[variant] = message
        self.assertNotEqual(seen["ok"], seen["fail"])
        self.assertNotEqual(seen["fail"], seen["retry"])
        self.assertEqual(seen["empty"], "")
        self.assertIn("ASK_PARENT", seen["retry"])
        self.assertIn("timeout", seen["fail"])

    def test_pending_apply_does_not_break_other_variants(self) -> None:
        result = apply_fixture(
            "lab-demo", "analyze-routing", "pending-apply", workspace=self.tmp
        )
        self.assertEqual(infer_result(result["last_message"]), "ok")
        self.assertNotIn("ASK_PARENT", result["last_message"])
        self.assertNotRegex(result["last_message"], r"(?i)\btimeout\b")
        routing = (
            self.tmp / "Feature-writing/lab-demo/lab-demo-routing-state.json"
        ).read_text(encoding="utf-8")
        self.assertIn('"decisions_pending_apply": 1', routing)
        self.assertIn('"needs_check_feature": true', routing)
        decisions = (
            self.tmp / "Feature-writing/lab-demo/lab-demo-decisions.md"
        ).read_text(encoding="utf-8")
        self.assertIn("pending-apply", decisions)
        self.assertTrue((self.tmp / "Feature-context/lab-demo.md").is_file())
        self.assertTrue((self.tmp / "Feature-writing/lab-demo/lab-demo.md").is_file())
        leftover = apply_fixture(
            "lab-demo", "analyze-routing", "ch-apply-leftover-gaps", workspace=self.tmp
        )
        self.assertEqual(infer_result(leftover["last_message"]), "ok")
        leftover_spec = (self.tmp / "Feature-writing/lab-demo/lab-demo.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("[GAP-LAB-01]", leftover_spec)
        leftover_decisions = (
            self.tmp / "Feature-writing/lab-demo/lab-demo-decisions.md"
        ).read_text(encoding="utf-8")
        self.assertIn("CH-01", leftover_decisions)
        leftover_json = json.loads(
            (self.tmp / "Feature-writing/lab-demo/lab-demo-routing-state.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(leftover_json["fields"]["open_gaps"], ["GAP-LAB-01"])
        self.assertEqual(leftover_json["fields"]["decisions_pending_apply_gaps"], 1)
        ok = apply_fixture("lab-demo", "check-feature", "ok", workspace=self.tmp)
        self.assertIn("fail 0", ok["last_message"])
        self.assertNotIn("pending-apply", ok["last_message"])

    def test_omitted_variant_reads_and_advances_cursor(self) -> None:
        feature = self.tmp / "Feature-writing" / "lab-demo"
        feature.mkdir(parents=True)
        cursor = feature / ".lab-cursor.json"
        cursor.write_text(
            json.dumps(
                {
                    "ticks": [
                        {"step": "check-feature", "variant": "retry"},
                        {"step": "check-feature", "variant": "ok"},
                    ],
                    "tick": 0,
                }
            ),
            encoding="utf-8",
        )
        first = apply_fixture("lab-demo", "check-feature", workspace=self.tmp)
        self.assertEqual(first["variant"], "retry")
        self.assertIn("ASK_PARENT", first["last_message"])
        data = json.loads(cursor.read_text(encoding="utf-8"))
        self.assertEqual(data["tick"], 1)
        second = apply_fixture("lab-demo", "check-feature", workspace=self.tmp)
        self.assertEqual(second["variant"], "ok")
        data = json.loads(cursor.read_text(encoding="utf-8"))
        self.assertEqual(data["tick"], 2)
        with self.assertRaises(ValueError):
            apply_fixture("lab-demo", "check-feature", workspace=self.tmp)


if __name__ == "__main__":
    unittest.main()

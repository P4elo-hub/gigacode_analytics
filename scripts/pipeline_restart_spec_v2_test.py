import json
import tempfile
import unittest
from pathlib import Path
from pipeline_restart import build_restart_plan, apply_restart_plan, load_restart_marker
from pipeline_dispatch import build_dispatch


class RestartSpecV2Test(unittest.TestCase):
    def test_restart_preserves_resolver_input_and_forces_selected_step(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            slug = "restart-test"
            fd = root / "Feature-writing" / slug
            journal = fd / ".pipeline/routing-reports"
            journal.mkdir(parents=True)
            for suffix in (".md", "-code-alignment.md", "-decisions.md", "-routing-state.json"):
                (fd / (slug + suffix)).write_text("{}")
            events = [
                {"seq": 1, "step": "code-auditor", "file": "first.json", "ts": "2000-01-01T00:00:00Z"},
                {"seq": 2, "step": "alignment-resolver", "file": "second.json", "ts": "2000-01-01T00:01:00Z"},
                {"seq": 3, "step": "code-auditor", "file": "third.json", "ts": "2000-01-01T00:02:00Z"},
            ]
            for event in events:
                (journal / event["file"]).write_text(json.dumps(event))
            (journal / "index.json").write_text(json.dumps({"schema_version": 1, "last_seq": 3, "events": events}))
            plan = build_restart_plan(root, slug, "alignment-resolver", from_seq=2, pipeline_id="spec-v2")
            self.assertNotIn(str((fd / (slug + "-code-alignment.md")).relative_to(root)), plan.remove_paths)
            result = apply_restart_plan(root, plan)
            self.assertTrue(result["ok"])
            self.assertTrue((journal / "first.json").exists())
            self.assertFalse((journal / "second.json").exists())
            self.assertFalse((journal / "third.json").exists())
            self.assertFalse((fd / (slug + "-routing-state.json")).exists())
            self.assertTrue(load_restart_marker(root, slug, "spec-v2"))
            dispatch = build_dispatch(root, slug, "spec-v2")
            self.assertEqual(dispatch["next_step"], "alignment-resolver")
            self.assertEqual(dispatch["task"]["subagent_type"], "alignment-resolver")
            self.assertEqual(json.loads((journal / "index.json").read_text())["last_seq"], 3)

    def test_auditor_restart_removes_old_alignment(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fd = root / "Feature-writing/test"
            fd.mkdir(parents=True)
            (fd / "test-code-alignment.md").write_text("FAIL")
            plan = build_restart_plan(root, "test", "code-auditor", pipeline_id="spec-v2")
            self.assertIn("Feature-writing/test/test-code-alignment.md", plan.remove_paths)

    def test_alignment_restart_keeps_incremental_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fd = root / "Feature-writing/test"
            fd.mkdir(parents=True)
            state = fd / "test-routing-state.json"
            state.write_text(json.dumps({
                "schema_version": 1, "slug": "test",
                "fields": {"find_context": False, "untouched_fact": True,
                           "has_alignment_svezhii_verdict_pass_ili_pass_with_gaps_sp": True},
            }))
            (fd / "test-code-alignment.md").write_text("FAIL")
            plan = build_restart_plan(root, "test", "code-auditor", pipeline_id="spec-v2")
            self.assertNotIn("Feature-writing/test/test-routing-state.json", plan.remove_paths)
            self.assertTrue(apply_restart_plan(root, plan)["ok"])
            fields = json.loads(state.read_text())["fields"]
            self.assertTrue(fields["untouched_fact"])
            self.assertFalse(fields["has_alignment_svezhii_verdict_pass_ili_pass_with_gaps_sp"])
            self.assertTrue(fields["has_net_otcheta_ili_on_ustarel_korotko_alignment_net_ili"])
            self.assertFalse((fd / "test-code-alignment.md").exists())

    def test_rejects_invalid_pass_and_slug(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                build_restart_plan(Path(tmp), "test", "code-auditor", from_seq=999, pipeline_id="spec-v2")
            with self.assertRaises(ValueError):
                build_restart_plan(Path(tmp), "../other", "code-auditor", pipeline_id="spec-v2")


if __name__ == "__main__":
    unittest.main()

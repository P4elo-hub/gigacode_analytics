#!/usr/bin/env python3
"""Phase 7 runtime contract: pack-first validate, shared orchestrator loop."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

from pipeline_pack import load_pack_module  # noqa: E402
from pipeline_runtime import runtime_contract  # noqa: E402
from pipeline_validate import ValidationReport, _add, validate_slug  # noqa: E402

SPEC_PACK_ADVICE_IDS = (
    "pending-apply-paused",
    "needs-answer-not-asked",
    "check-feature-redundant-loop",
    "challenge-repeat-blocked",
    "routing-state-missing",
    "routing-state-stale",
)
ENGINE_ADVICE_IDS = (
    "dispatch-not-configured",
    "pipeline-ready",
    "write-feature-cycle-idle",
    "stopped-while-must-continue",
    "last-step-fail",
    "workflow-ok",
)
SMOKE_SLUG = "pipeline-viewer-smoke"


def _empty_report(next_step: str = "") -> ValidationReport:
    return ValidationReport(
        slug="matrix",
        ok=True,
        ready=False,
        must_continue=False,
        next_step=next_step,
        next_subagent="",
    )


def _advice_by_id(report: ValidationReport) -> dict[str, object]:
    return {item.id: item for item in report.advice}


class RuntimeContractTest(unittest.TestCase):
    def test_spec_and_calibration_loop_share_scripts(self) -> None:
        spec = runtime_contract("spec")
        cal = runtime_contract("calibration")
        self.assertTrue(spec["dispatch_supported"])
        self.assertFalse(cal["dispatch_supported"])
        self.assertTrue(spec["validate"]["extra_advice"])
        self.assertTrue(cal["validate"]["extra_advice"])
        self.assertIn("--pipeline spec", spec["loop"][0])
        self.assertIn("--pipeline calibration", cal["loop"][0])
        self.assertTrue(spec["loop"][0].startswith("python3 scripts/pipeline_delegate.py"))
        for contract in (spec, cal):
            joined = " ".join(contract["loop"])
            self.assertIn("pipeline_delegate.py", joined)
            self.assertIn("append_run_log.py", joined)
            self.assertIn("pipeline_validate.py", joined)


class SpecValidateIdsTest(unittest.TestCase):
    def test_engine_has_no_spec_only_copy(self) -> None:
        text = (SCRIPTS / "pipeline_validate.py").read_text(encoding="utf-8")
        self.assertNotIn("Spec готов", text)
        self.assertNotIn("spec-writer", text)
        self.assertNotIn("калибровка — только по запросу", text)
        self.assertNotIn("pipeline_dispatch.py --json", text)
        for advice_id in ENGINE_ADVICE_IDS:
            self.assertIn(f'id="{advice_id}"', text)

    def test_spec_pack_advice_ids_unchanged(self) -> None:
        text = (ROOT / "pipelines" / "spec" / "validate.py").read_text(encoding="utf-8")
        helper = (SCRIPTS / "pipeline_routing_state.py").read_text(encoding="utf-8")
        combined = text + "\n" + helper
        for advice_id in SPEC_PACK_ADVICE_IDS:
            self.assertIn(f'id="{advice_id}"', combined)

    def test_pipeline_ready_copy_from_status_messages(self) -> None:
        fake_dispatch = {
            "ready": True,
            "must_continue": False,
            "next_step": "",
            "next_subagent": "",
            "next_reason": "PASS",
            "orchestrator_mode": "ready",
        }
        with (
            patch("pipeline_validate.build_dispatch", return_value=fake_dispatch),
            patch("pipeline_validate.dispatch_supported", return_value=True),
            patch("pipeline_validate.build_status", return_value=SimpleNamespace()),
        ):
            result = validate_slug(ROOT, SMOKE_SLUG, pipeline="spec")
        self.assertEqual(len(result.advice), 1)
        item = result.advice[0]
        self.assertEqual(item.id, "pipeline-ready")
        self.assertEqual(item.severity, "ok")
        self.assertEqual(item.title, "Spec готов")
        self.assertEqual(item.detail, "PASS")
        self.assertEqual(
            item.workflow_fix,
            "Финальный ответ пользователю; калибровка — только по запросу.",
        )

    def test_spec_validate_item_ids_on_real_slug(self) -> None:
        result = validate_slug(ROOT, SMOKE_SLUG, pipeline="spec")
        ids = [item.id for item in result.advice]
        allowed_prefixes = ("div-",)
        allowed = set(ENGINE_ADVICE_IDS) | set(SPEC_PACK_ADVICE_IDS)
        for advice_id in ids:
            if advice_id.startswith(allowed_prefixes):
                continue
            self.assertIn(advice_id, allowed, ids)

    def test_stopped_while_must_continue_fix_uses_delegate(self) -> None:
        text = (SCRIPTS / "pipeline_validate.py").read_text(encoding="utf-8")
        self.assertIn("pipeline_delegate.py --pipeline", text)
        self.assertIn("task", text)


class SpecPackAdviceMatrixTest(unittest.TestCase):
    """Severity matrix for pipelines/spec/validate.py extra_advice (bit-for-bit ids)."""

    def setUp(self) -> None:
        extra = load_pack_module("spec", "validate")
        assert extra is not None
        self.extra = extra

    def _run(self, status, dispatch: dict, next_step: str = "") -> dict[str, object]:
        report = _empty_report(next_step=next_step)
        self.extra.extra_advice(ROOT, "matrix", status, dispatch, report, _add)
        return _advice_by_id(report)

    def test_pending_apply_paused_is_block(self) -> None:
        status = SimpleNamespace(
            decisions_pending_apply=2,
            decisions_needs_answer=0,
            has_challenges=False,
            pipeline_id="spec",
        )
        found = self._run(status, {"orchestrator_mode": "ask_user"})
        self.assertIn("pending-apply-paused", found)
        self.assertEqual(found["pending-apply-paused"].severity, "block")  # type: ignore[union-attr]

    def test_pending_apply_with_delegate_is_silent(self) -> None:
        status = SimpleNamespace(
            decisions_pending_apply=2,
            decisions_needs_answer=0,
            has_challenges=False,
            pipeline_id="spec",
        )
        found = self._run(status, {"orchestrator_mode": "delegate"})
        self.assertNotIn("pending-apply-paused", found)

    def test_needs_answer_not_asked_is_block(self) -> None:
        status = SimpleNamespace(
            decisions_pending_apply=0,
            decisions_needs_answer=3,
            has_challenges=False,
            pipeline_id="spec",
        )
        found = self._run(status, {"orchestrator_mode": "delegate"})
        self.assertIn("needs-answer-not-asked", found)
        self.assertEqual(found["needs-answer-not-asked"].severity, "block")  # type: ignore[union-attr]

    def test_needs_answer_with_ask_user_is_silent(self) -> None:
        status = SimpleNamespace(
            decisions_pending_apply=0,
            decisions_needs_answer=3,
            has_challenges=False,
            pipeline_id="spec",
        )
        found = self._run(status, {"orchestrator_mode": "ask_user"})
        self.assertNotIn("needs-answer-not-asked", found)

    def test_challenge_repeat_blocked_is_block(self) -> None:
        status = SimpleNamespace(
            decisions_pending_apply=0,
            decisions_needs_answer=0,
            has_challenges=True,
            pipeline_id="spec",
        )
        found = self._run(status, {"orchestrator_mode": "delegate"}, next_step="challenge-feature")
        self.assertIn("challenge-repeat-blocked", found)
        self.assertEqual(found["challenge-repeat-blocked"].severity, "block")  # type: ignore[union-attr]

    def test_challenge_file_with_code_step_is_silent(self) -> None:
        status = SimpleNamespace(
            decisions_pending_apply=0,
            decisions_needs_answer=0,
            has_challenges=True,
            pipeline_id="spec",
        )
        found = self._run(status, {"orchestrator_mode": "delegate"}, next_step="check-feature-code")
        self.assertNotIn("challenge-repeat-blocked", found)


class CalibrationValidateTest(unittest.TestCase):
    def test_real_pack_extra_advice_runs_without_engine_duplicate(self) -> None:
        result = validate_slug(ROOT, SMOKE_SLUG, pipeline="calibration")
        ids = [item.id for item in result.advice]
        self.assertIn("cal-orchestrator-only", ids)
        self.assertNotIn("dispatch-not-configured", ids)
        self.assertTrue(result.ok)

    def test_extra_advice_called_when_dispatch_unsupported(self) -> None:
        seen: list[str] = []

        def fake_extra(root, slug, status, dispatch, report, add) -> None:
            del root, slug, status, dispatch
            seen.append("called")
            add(
                report,
                id="cal-test-sentinel",
                severity="ok",
                title="sentinel",
                detail="stub",
                fix="n/a",
            )

        stub = SimpleNamespace(extra_advice=fake_extra)
        with patch("pipeline_validate._pack_validate_module", return_value=stub):
            result = validate_slug(ROOT, SMOKE_SLUG, pipeline="calibration")
        ids = [item.id for item in result.advice]
        self.assertEqual(seen, ["called"])
        self.assertIn("cal-test-sentinel", ids)
        self.assertNotIn("dispatch-not-configured", ids)
        self.assertTrue(result.ok)

    def test_engine_fallback_when_pack_validate_missing(self) -> None:
        with patch("pipeline_validate._pack_validate_module", return_value=None):
            result = validate_slug(ROOT, SMOKE_SLUG, pipeline="calibration")
        ids = [item.id for item in result.advice]
        self.assertIn("dispatch-not-configured", ids)
        self.assertNotIn("cal-orchestrator-only", ids)
        self.assertTrue(result.ok)

    def test_graph_orchestrator_missing_is_block(self) -> None:
        extra = load_pack_module("calibration", "validate")
        assert extra is not None
        report = _empty_report()
        dispatch = {"orchestrator_mode": "orchestrator_only", "dispatch_supported": False}
        broken = {"orchestrator": "missing-orch", "nodes": [{"id": "snapshot-baseline"}]}
        with patch.object(extra, "load_pipeline_schema", return_value=broken):
            extra.extra_advice(ROOT, SMOKE_SLUG, SimpleNamespace(), dispatch, report, _add)
        found = _advice_by_id(report)
        self.assertIn("cal-graph-orchestrator-missing", found)
        self.assertEqual(found["cal-graph-orchestrator-missing"].severity, "block")  # type: ignore[union-attr]
        self.assertFalse(report.ok)


class OrchestratorRuntimeBlockTest(unittest.TestCase):
    def test_agents_share_runtime_loop_heading(self) -> None:
        for rel in (
            ".qwen/agents/spec-orchestrator.md",
            ".gigacode/agents/spec-orchestrator.md",
            ".opencode/agents/spec-orchestrator.md",
            ".qwen/agents/calibration-orchestrator.md",
            ".gigacode/agents/calibration-orchestrator.md",
            ".opencode/agents/calibration-orchestrator.md",
            ".qwen/rules/pipeline-enforcement.md",
            ".gigacode/rules/pipeline-enforcement.md",
            ".opencode/rules/pipeline-enforcement.md",
        ):
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("Runtime loop (mandatory)", text, rel)
            self.assertIn("pipeline_delegate.py", text)
            self.assertIn("pipeline_validate.py", text)
            self.assertIn("--pipeline", text)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Machine-checkable contracts for music-production agents."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
AGENTS = ROOT / ".gigacode" / "agents"
SKILLS = ROOT / ".gigacode" / "skills"
CONTRACTS = ROOT / "music_production" / "contracts"
FIXTURES = ROOT / "music_production" / "fixtures"
GRAPH = ROOT / "pipelines" / "music-production" / "graph.yaml"
REGISTRY = ROOT / "pipelines" / "music-production" / "registry.yaml"

AGENT_CONTRACTS = {
    "music-brief-analyst": (
        "brief", "brief.schema.json", "sample-brief.json", "brief"
    ),
    "music-lyrics-writer": (
        "lyrics", "lyrics.schema.json", "sample-lyrics.json", "lyrics-write"
    ),
    "music-lyrics-editor": (
        "lyrics-review",
        "lyrics-review.schema.json",
        "sample-lyrics-review-pass.json",
        "lyrics-review",
    ),
    "music-sound-director": (
        "sound-direction",
        "sound-direction.schema.json",
        "sample-sound-direction.json",
        "sound-design",
    ),
    "music-package-reviewer": (
        "package-review",
        "package-review.schema.json",
        "sample-package-review-pass.json",
        "package-review",
    ),
    "music-suno-prompt-compiler": (
        "generation-request",
        "generation-request.schema.json",
        "sample-generation-request.json",
        "prompt-compile",
    ),
    "music-candidate-critic": (
        "candidate-review",
        "candidate-review.schema.json",
        "sample-candidate-review.json",
        "candidate-review",
    ),
    "music-defect-diagnostician": (
        "defect", "defect.schema.json", "sample-defect.json", "diagnose-defects"
    ),
    "music-revision-planner": (
        "revision-plan",
        "revision-plan.schema.json",
        "sample-revision-plan.json",
        "plan-revision",
    ),
    "music-version-comparator": (
        "version-comparison",
        "version-comparison.schema.json",
        "sample-version-comparison.json",
        "compare-versions",
    ),
    "music-knowledge-capturer": (
        "knowledge-case",
        "knowledge-case.schema.json",
        "sample-knowledge-case.json",
        "capture-knowledge",
    ),
}

NEW_SCHEMAS = (
    "agent-result.schema.json",
    "lyrics.schema.json",
    "lyrics-review.schema.json",
    "sound-direction.schema.json",
    "package-review.schema.json",
    "candidate-review.schema.json",
    "revision-plan.schema.json",
    "version-comparison.schema.json",
    "knowledge-case.schema.json",
)

VALID_ENVELOPES = (
    "sample-agent-result-pass.json",
    "sample-agent-result-revise.json",
    "sample-agent-result-blocked.json",
)

INVALID_ENVELOPES = (
    "invalid-agent-result-extra-field.json",
    "invalid-agent-result-pass-without-artifact.json",
    "invalid-agent-result-revise-without-issues.json",
    "invalid-agent-result-blocked-without-reason.json",
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validator_for(schema_name: str) -> Draft202012Validator:
    schema = load_json(CONTRACTS / schema_name)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def envelope_for(
    agent_id: str,
    artifact_type: str,
    step: str,
    artifact: dict,
) -> dict:
    return {
        "schema_version": "1.0",
        "track_id": artifact["track_id"],
        "created_at": artifact["created_at"],
        "agent_id": agent_id,
        "step": step,
        "outcome": "PASS",
        "artifact_type": artifact_type,
        "artifact": artifact,
        "issues": [],
        "blocked_reason": None,
    }


def assert_fixed_objects_closed(test: unittest.TestCase, node: object, path: str) -> None:
    if isinstance(node, dict):
        if node.get("type") == "object" and "properties" in node:
            test.assertIs(node.get("additionalProperties"), False, path)
        for key, child in node.items():
            assert_fixed_objects_closed(test, child, f"{path}.{key}")
    elif isinstance(node, list):
        for index, child in enumerate(node):
            assert_fixed_objects_closed(test, child, f"{path}[{index}]")


class PackageAgentContractTest(unittest.TestCase):
    def test_all_new_schemas_are_valid_draft_2020_12(self) -> None:
        for schema_name in NEW_SCHEMAS:
            with self.subTest(schema=schema_name):
                schema = load_json(CONTRACTS / schema_name)
                self.assertEqual(
                    schema["$schema"],
                    "https://json-schema.org/draft/2020-12/schema",
                )
                self.assertIs(schema["additionalProperties"], False)
                Draft202012Validator.check_schema(schema)
                assert_fixed_objects_closed(self, schema, schema_name)

    def test_all_artifact_fixtures_are_schema_valid(self) -> None:
        for _, schema_name, fixture_name, _ in AGENT_CONTRACTS.values():
            with self.subTest(fixture=fixture_name):
                validator_for(schema_name).validate(load_json(FIXTURES / fixture_name))

    def test_valid_envelopes_then_their_artifacts(self) -> None:
        artifact_schemas = {
            artifact_type: schema_name
            for artifact_type, schema_name, _, _ in AGENT_CONTRACTS.values()
        }
        envelope_validator = validator_for("agent-result.schema.json")
        for fixture_name in VALID_ENVELOPES:
            with self.subTest(fixture=fixture_name):
                envelope = load_json(FIXTURES / fixture_name)
                envelope_validator.validate(envelope)
                schema_name = artifact_schemas[envelope["artifact_type"]]
                validator_for(schema_name).validate(envelope["artifact"])

    def test_envelope_accepts_exactly_all_eleven_agent_ids(self) -> None:
        envelope_validator = validator_for("agent-result.schema.json")
        declared = set(
            load_json(CONTRACTS / "agent-result.schema.json")["properties"][
                "agent_id"
            ]["enum"]
        )
        self.assertEqual(declared, set(AGENT_CONTRACTS))
        self.assertNotIn("music-orchestrator", declared)
        for agent_id, (
            artifact_type,
            schema_name,
            fixture_name,
            step,
        ) in AGENT_CONTRACTS.items():
            with self.subTest(agent=agent_id):
                artifact = load_json(FIXTURES / fixture_name)
                validator_for(schema_name).validate(artifact)
                envelope_validator.validate(
                    envelope_for(agent_id, artifact_type, step, artifact)
                )

    def test_invalid_envelopes_are_rejected(self) -> None:
        validator = validator_for("agent-result.schema.json")
        for fixture_name in INVALID_ENVELOPES:
            with self.subTest(fixture=fixture_name):
                errors = list(validator.iter_errors(load_json(FIXTURES / fixture_name)))
                self.assertTrue(errors, fixture_name)

    def test_envelope_date_time_uses_format_checker(self) -> None:
        envelope = load_json(FIXTURES / "sample-agent-result-pass.json")
        envelope["created_at"] = "2026-13-40T25:61:61Z"
        errors = list(
            validator_for("agent-result.schema.json").iter_errors(envelope)
        )
        self.assertTrue(
            [error for error in errors if error.validator == "format"],
            [error.message for error in errors],
        )

    def test_invalid_revision_plan_and_knowledge_case_are_rejected(self) -> None:
        cases = (
            ("revision-plan.schema.json", "invalid-revision-plan.json"),
            ("knowledge-case.schema.json", "invalid-knowledge-case.json"),
        )
        for schema_name, fixture_name in cases:
            with self.subTest(fixture=fixture_name):
                errors = list(
                    validator_for(schema_name).iter_errors(
                        load_json(FIXTURES / fixture_name)
                    )
                )
                self.assertTrue(errors, fixture_name)

    def test_agents_link_existing_envelope_and_artifact_schemas(self) -> None:
        envelope_path = "music_production/contracts/agent-result.schema.json"
        self.assertTrue((CONTRACTS / "agent-result.schema.json").is_file())
        for agent_id, (
            artifact_type,
            schema_name,
            _,
            _,
        ) in AGENT_CONTRACTS.items():
            with self.subTest(agent=agent_id):
                text = (AGENTS / f"{agent_id}.md").read_text(encoding="utf-8")
                self.assertIn(envelope_path, text)
                self.assertIn(
                    f"music_production/contracts/{schema_name}",
                    text,
                )
                self.assertIn(f"`artifact_type`: `{artifact_type}`", text)
                self.assertIn("PASS", text)
                self.assertIn("REVISE", text)
                self.assertIn("BLOCKED", text)
                self.assertIn("обе проверки", text)
                self.assertIn("Markdown-инструкция не заменяет JSON Schema", text)

    def test_agents_require_bare_json_not_markdown_wrapping(self) -> None:
        for agent_id in AGENT_CONTRACTS:
            with self.subTest(agent=agent_id):
                text = (AGENTS / f"{agent_id}.md").read_text(encoding="utf-8")
                self.assertIn("только JSON envelope без Markdown", text)
                self.assertNotIn("```json", text.lower())

    def test_candidate_review_cannot_store_human_selection(self) -> None:
        schema = load_json(CONTRACTS / "candidate-review.schema.json")
        serialized = json.dumps(schema, ensure_ascii=False)
        self.assertNotIn("selected_candidate_id", serialized)
        self.assertNotIn("SELECT_AS_BASE", serialized)
        candidate = load_json(FIXTURES / "sample-candidate-review.json")
        self.assertNotIn("selected_candidate_id", candidate)
        self.assertNotIn("verdict", candidate)
        validator_for("candidate-review.schema.json").validate(candidate)

    def test_knowledge_rule_remains_candidate_only(self) -> None:
        schema = load_json(CONTRACTS / "knowledge-case.schema.json")
        self.assertEqual(
            schema["properties"]["rule_status"]["const"],
            "candidate_rule",
        )
        case = load_json(FIXTURES / "sample-knowledge-case.json")
        self.assertEqual(case["rule_status"], "candidate_rule")
        validator_for("knowledge-case.schema.json").validate(case)

    def test_revision_operation_enum_matches_generation_request(self) -> None:
        generation_enum = load_json(
            CONTRACTS / "generation-request.schema.json"
        )["properties"]["operation"]["enum"]
        revision_enum = load_json(
            CONTRACTS / "revision-plan.schema.json"
        )["properties"]["operation"]["enum"]
        self.assertEqual(revision_enum, generation_enum)

    def test_revise_returns_lyrics_review_to_lyrics_write(self) -> None:
        review = load_json(FIXTURES / "sample-lyrics-review-revise.json")
        validator_for("lyrics-review.schema.json").validate(review)
        self.assertEqual(review["verdict"], "REVISE")
        graph = GRAPH.read_text(encoding="utf-8")
        self.assertIn("from: lyrics-review\n    to: lyrics-write", graph)
        self.assertIn("condition: lyrics_revise", graph)

    def test_version_comparator_requires_edit_attempt_contract(self) -> None:
        agent = (AGENTS / "music-version-comparator.md").read_text(encoding="utf-8")
        skill = (
            SKILLS / "music-version-comparison" / "SKILL.md"
        ).read_text(encoding="utf-8")
        for text in (agent, skill):
            self.assertIn("edit-attempt", text)
            self.assertIn("revision-plan", text)
            self.assertIn("parent version", text)
            self.assertIn("child version", text)
            self.assertIn("target defect", text)
            self.assertIn("измеренные или переданные факты сравнения", text)
            self.assertIn("edit_attempt_id", text)
            self.assertIn("parent_version_id", text)
            self.assertIn("child_version_id", text)
            self.assertIn("revision_plan_id", text)
            self.assertIn("defect_id", text)
            self.assertIn("Не исправляй lineage самостоятельно", text)
            self.assertIn("не подменяй parent/child IDs", text)
        self.assertIn("Outcome artifact тогда `BLOCKED`", agent)
        self.assertIn("outcome artifact = `BLOCKED`", skill)

        sample = load_json(FIXTURES / "sample-version-comparison.json")
        validator_for("version-comparison.schema.json").validate(sample)
        self.assertIn("edit_attempt_id", sample)

        missing = dict(sample)
        del missing["edit_attempt_id"]
        errors = list(
            validator_for("version-comparison.schema.json").iter_errors(missing)
        )
        self.assertTrue(
            any(
                error.validator == "required" and "edit_attempt_id" in error.message
                for error in errors
            )
        )
        self.assertIn("Не менять `parent_version_id`", agent)

    def test_agents_skills_command_and_registry_exist(self) -> None:
        registry = REGISTRY.read_text(encoding="utf-8")
        for agent_id in AGENT_CONTRACTS:
            self.assertTrue((AGENTS / f"{agent_id}.md").is_file(), agent_id)
            self.assertIn(f": {agent_id}", registry)
        self.assertTrue((AGENTS / "music-orchestrator.md").is_file())
        self.assertTrue(
            (ROOT / ".gigacode" / "commands" / "music-production.md").is_file()
        )
        self.assertFalse(list((ROOT / ".qwen" / "agents").glob("music-*.md")))
        self.assertFalse(list((ROOT / ".opencode" / "agents").glob("music-*.md")))


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Validate music_production fixtures with Draft 2020-12 and FormatChecker."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError

ROOT = Path(__file__).resolve().parents[2] / "music_production"
CONTRACTS = ROOT / "contracts"
FIXTURES = ROOT / "fixtures"

SCHEMA_FILES = (
    "brief.schema.json",
    "song-package.schema.json",
    "track-state.schema.json",
    "generation-request.schema.json",
    "defect.schema.json",
    "expert-decision.schema.json",
)

VALID_FIXTURES = (
    ("brief.schema.json", "sample-brief.json"),
    ("song-package.schema.json", "sample-song-package.json"),
    ("track-state.schema.json", "sample-track-state.json"),
    ("generation-request.schema.json", "sample-generation-request.json"),
    ("defect.schema.json", "sample-defect.json"),
    ("expert-decision.schema.json", "sample-expert-decision.json"),
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validator_for(schema_name: str) -> Draft202012Validator:
    schema = load_json(CONTRACTS / schema_name)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def walk_errors(errors: list[ValidationError]):
    for error in errors:
        yield error
        yield from walk_errors(list(error.context))


class MusicContractTest(unittest.TestCase):
    def test_schemas_are_draft_2020_12(self) -> None:
        for name in SCHEMA_FILES:
            with self.subTest(schema=name):
                schema = load_json(CONTRACTS / name)
                Draft202012Validator.check_schema(schema)
                self.assertEqual(
                    schema["$schema"],
                    "https://json-schema.org/draft/2020-12/schema",
                )
                self.assertIs(schema["additionalProperties"], False)
                self.assertEqual(schema["type"], "object")
                self.assertIn("schema_version", schema["required"])
                self.assertIn("track_id", schema["required"])
                self.assert_closed_objects(schema, name)

    def assert_closed_objects(self, node: object, path: str) -> None:
        if isinstance(node, dict):
            if node.get("type") == "object" and "properties" in node:
                self.assertIs(node.get("additionalProperties"), False, path)
            for key, child in node.items():
                if key == "properties" and isinstance(child, dict):
                    for name, subschema in child.items():
                        self.assert_closed_objects(subschema, f"{path}.{name}")
                elif key == "$defs" and isinstance(child, dict):
                    for name, subschema in child.items():
                        self.assert_closed_objects(subschema, f"{path}.{name}")
                elif isinstance(child, dict):
                    self.assert_closed_objects(child, f"{path}.{key}")
                elif isinstance(child, list):
                    for index, item in enumerate(child):
                        self.assert_closed_objects(item, f"{path}.{key}[{index}]")

    def test_unknown_top_level_field_rejected(self) -> None:
        for schema_name, fixture_name in VALID_FIXTURES:
            with self.subTest(schema=schema_name):
                document = load_json(FIXTURES / fixture_name)
                document["unknown_field"] = "rejected"
                errors = list(validator_for(schema_name).iter_errors(document))
                rejected = [
                    error
                    for error in errors
                    if error.validator == "additionalProperties"
                ]
                self.assertTrue(rejected, [error.message for error in errors])

    def test_format_checker_registers_date_time(self) -> None:
        self.assertIn("date-time", FormatChecker().checkers)

    def test_valid_track_fixtures(self) -> None:
        for schema_name, fixture_name in VALID_FIXTURES:
            with self.subTest(fixture=fixture_name):
                validator_for(schema_name).validate(load_json(FIXTURES / fixture_name))

    def test_missing_ids_rejected(self) -> None:
        cases = (
            ("brief.schema.json", "invalid-missing-track-id.json", "track_id"),
            ("defect.schema.json", "invalid-missing-defect-ids.json", "id"),
            ("defect.schema.json", "invalid-missing-defect-ids.json", "version_id"),
            ("expert-decision.schema.json", "invalid-missing-decision-ref.json", "version_id"),
        )
        for schema_name, fixture_name, field_name in cases:
            with self.subTest(fixture=fixture_name, field=field_name):
                errors = list(
                    walk_errors(
                        list(
                            validator_for(schema_name).iter_errors(
                                load_json(FIXTURES / fixture_name)
                            )
                        )
                    )
                )
                required = [
                    error
                    for error in errors
                    if error.validator == "required" and field_name in error.message
                ]
                self.assertTrue(required, [error.message for error in errors])

    def test_audio_offset_125_75_is_valid(self) -> None:
        document = load_json(FIXTURES / "sample-defect.json")
        self.assertEqual(document["start_seconds"], 125.75)
        validator_for("defect.schema.json").validate(document)

    def test_negative_audio_offset_rejected(self) -> None:
        errors = list(
            validator_for("defect.schema.json").iter_errors(
                load_json(FIXTURES / "invalid-time.json")
            )
        )
        minimum_errors = [
            error
            for error in errors
            if error.validator == "minimum" and error.instance == -1
        ]
        self.assertTrue(minimum_errors, [error.message for error in errors])

    def test_impossible_date_rejected(self) -> None:
        document = load_json(FIXTURES / "sample-brief.json")
        document["created_at"] = "2026-13-40T25:61:61Z"
        errors = list(
            walk_errors(
                list(validator_for("brief.schema.json").iter_errors(document))
            )
        )
        format_errors = [
            error
            for error in errors
            if error.validator == "format" and error.validator_value == "date-time"
        ]
        self.assertTrue(format_errors, [error.message for error in errors])
        self.assertEqual(format_errors[0].instance, "2026-13-40T25:61:61Z")

    def test_incompatible_gate_verdict_rejected(self) -> None:
        errors = list(
            walk_errors(
                list(
                    validator_for("expert-decision.schema.json").iter_errors(
                        load_json(FIXTURES / "invalid-verdict.json")
                    )
                )
            )
        )
        enum_errors = [
            error
            for error in errors
            if error.validator == "enum" and error.instance == "SELECT_AS_BASE"
        ]
        self.assertTrue(enum_errors, [error.message for error in errors])

    def test_invalid_state_rejected(self) -> None:
        errors = list(
            validator_for("track-state.schema.json").iter_errors(
                load_json(FIXTURES / "invalid-state.json")
            )
        )
        enum_errors = [error for error in errors if error.validator == "enum"]
        self.assertTrue(enum_errors, [error.message for error in errors])
        self.assertEqual(enum_errors[0].instance, "DONE")

    def test_replace_section_is_schema_valid(self) -> None:
        document = load_json(FIXTURES / "sample-generation-request.json")
        document["operation"] = "replace-section"
        validator_for("generation-request.schema.json").validate(document)

    def test_unknown_operation_rejected(self) -> None:
        errors = list(
            validator_for("generation-request.schema.json").iter_errors(
                load_json(FIXTURES / "invalid-suno-operation.json")
            )
        )
        enum_errors = [
            error for error in errors if error.validator == "enum" and error.instance == "unknown-operation"
        ]
        self.assertTrue(enum_errors, [error.message for error in errors])


if __name__ == "__main__":
    unittest.main()

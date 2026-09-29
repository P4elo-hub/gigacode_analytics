"""Service-level invariants that JSON Schema cannot express."""

from __future__ import annotations

from typing import Mapping


class InvalidDefectRangeError(ValueError):
    pass


def validate_defect_range(start_seconds: object, end_seconds: object) -> None:
    if isinstance(start_seconds, bool) or not isinstance(start_seconds, (int, float)):
        raise InvalidDefectRangeError("start_seconds must be a number")
    if isinstance(end_seconds, bool) or not isinstance(end_seconds, (int, float)):
        raise InvalidDefectRangeError("end_seconds must be a number")
    if start_seconds < 0:
        raise InvalidDefectRangeError("start_seconds must be non-negative")
    if end_seconds <= start_seconds:
        raise InvalidDefectRangeError("end_seconds must be greater than start_seconds")


def validate_defect(defect: Mapping[str, object]) -> None:
    try:
        start_seconds = defect["start_seconds"]
        end_seconds = defect["end_seconds"]
    except KeyError as exc:
        raise InvalidDefectRangeError(f"missing {exc.args[0]}") from exc
    validate_defect_range(start_seconds, end_seconds)

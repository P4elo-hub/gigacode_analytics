"""Gate-step stamp for routing-poc. No gate steps — mutate leaves JSON stale."""

from __future__ import annotations

from pathlib import Path


def refresh_fields(
    root: Path,
    slug: str,
    paths: dict[str, Path],
    step_completion: dict[str, str],
    current_fields: dict,
) -> dict:
    del root, slug, paths, step_completion
    return dict(current_fields)

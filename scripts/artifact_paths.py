"""Канонические пути артефактов фичи. Совпадает с правилом artifact-paths."""

from __future__ import annotations

from pathlib import Path

FEATURE_WRITING_DIR = "Feature-writing"
FEATURE_CONTEXT_DIR = "Feature-context"

SPEC_SUFFIX = ".md"
DECISIONS_SUFFIX = "-decisions.md"
ALIGNMENT_SUFFIX = "-code-alignment.md"
GAPS_MAP_SUFFIX = "-gaps-resolved.md"
CHALLENGES_SUFFIX = "-challenges.md"
CHALLENGES_MAP_SUFFIX = "-challenges-resolved.md"

ALIGNMENT_MAX_ITERATIONS = 3
VERDICT_PASS = "PASS"
VERDICT_PASS_WITH_GAPS = "PASS WITH GAPS"
VERDICT_FAIL = "FAIL"


def workspace_root(start: Path | None = None) -> Path:
    here = (start or Path.cwd()).resolve()
    if (here / FEATURE_WRITING_DIR).is_dir():
        return here
    for parent in here.parents:
        if (parent / FEATURE_WRITING_DIR).is_dir():
            return parent
    return here


def feature_dir(root: Path, slug: str) -> Path:
    return root / FEATURE_WRITING_DIR / slug


def spec_path(root: Path, slug: str) -> Path:
    return feature_dir(root, slug) / f"{slug}{SPEC_SUFFIX}"


def decisions_path(root: Path, slug: str) -> Path:
    return feature_dir(root, slug) / f"{slug}{DECISIONS_SUFFIX}"


def context_doc_path(root: Path, slug: str) -> Path:
    return root / FEATURE_CONTEXT_DIR / f"{slug}.md"


def alignment_path(root: Path, slug: str) -> Path:
    return feature_dir(root, slug) / f"{slug}{ALIGNMENT_SUFFIX}"


def gaps_map_path(root: Path, slug: str) -> Path:
    return feature_dir(root, slug) / f"{slug}{GAPS_MAP_SUFFIX}"


def challenges_path(root: Path, slug: str) -> Path:
    return feature_dir(root, slug) / f"{slug}{CHALLENGES_SUFFIX}"


def challenges_map_path(root: Path, slug: str) -> Path:
    return feature_dir(root, slug) / f"{slug}{CHALLENGES_MAP_SUFFIX}"


def list_feature_slugs(root: Path) -> list[str]:
    writing = root / FEATURE_WRITING_DIR
    if not writing.is_dir():
        return []
    return sorted(
        path.name
        for path in writing.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    )


def resolve_slug(raw: str, root: Path) -> str | None:
    candidate = raw.strip().rstrip("/")
    if not candidate:
        return None
    path = Path(candidate)
    if path.suffix == ".md":
        parent_name = path.parent.name
        if parent_name and (root / FEATURE_WRITING_DIR / parent_name).is_dir():
            return parent_name
        stem = path.stem
        for suffix in (
            ALIGNMENT_SUFFIX.replace(".md", ""),
            GAPS_MAP_SUFFIX.replace(".md", ""),
            CHALLENGES_MAP_SUFFIX.replace(".md", ""),
            CHALLENGES_SUFFIX.replace(".md", ""),
            DECISIONS_SUFFIX.replace(".md", ""),
        ):
            if stem.endswith(suffix):
                return stem[: -len(suffix)]
        return stem
    if (root / FEATURE_WRITING_DIR / candidate).is_dir():
        return candidate
    return candidate

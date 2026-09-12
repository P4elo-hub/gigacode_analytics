"""Профили разделов spec. Списки — kb-writing-kits/spec-catalog.yaml."""

from __future__ import annotations

from spec_catalog import (
    default_profile_name,
    extra_keywords,
    profile_sections,
)

PROFILE_CORE = "core"
PROFILE_SIHIST = "sihist"
PROFILE_FULL = "full"
DEFAULT_PROFILE = default_profile_name()


def normalize_profile(name: str | None) -> str:
    profiles = profile_sections()
    if not name:
        return DEFAULT_PROFILE
    key = name.strip().lower()
    if key not in profiles:
        known = ", ".join(profiles)
        raise ValueError(f"неизвестный профиль `{name}`; доступны: {known}")
    return key


def _section_sort_key(section_id: str) -> tuple:
    base = section_id.split("-")[0]
    numbers = [int(part) for part in base.split(".") if part.isdigit()]
    while len(numbers) < 4:
        numbers.append(0)
    return (*numbers[:4], section_id)


def extra_keyword_sections(brief: str) -> set[str]:
    lower = brief.lower()
    chosen: set[str] = set()
    for section_id, keywords in extra_keywords().items():
        if any(keyword in lower for keyword in keywords):
            chosen.add(section_id)
    return chosen


def infer_sections(
    feature_brief: str,
    explicit: str | None = None,
    profile: str | None = None,
) -> list[str]:
    profiles = profile_sections()
    if explicit and explicit.lower() != "full":
        return sorted(
            [part.strip() for part in explicit.split(",") if part.strip()],
            key=_section_sort_key,
        )
    if explicit and explicit.lower() == "full":
        chosen = set(profiles[PROFILE_FULL])
    else:
        chosen = set(profiles[normalize_profile(profile)])
        chosen |= extra_keyword_sections(feature_brief)
    return sorted(chosen, key=_section_sort_key)

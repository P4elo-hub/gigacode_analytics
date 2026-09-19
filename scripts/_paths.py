"""Scripts layout bootstrap: subpackages on sys.path for cross-folder imports."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parent

SUBDIRS = (
    "shared",
    "hooks",
    "telemetry",
    "pipeline",
    "routing",
    "authoring",
    "analytics",
    "calibration",
    "viewer",
    "tooling",
    "testing",
)

_installed = False


def install() -> Path:
    global _installed
    root = str(SCRIPTS_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
    for name in SUBDIRS:
        sub = str(SCRIPTS_ROOT / name)
        if sub not in sys.path:
            sys.path.insert(0, sub)
    _installed = True
    return SCRIPTS_ROOT


def scripts_root() -> Path:
    return SCRIPTS_ROOT


def repo_root() -> Path:
    return SCRIPTS_ROOT.parent


def fixtures_dir(*parts: str) -> Path:
    path = SCRIPTS_ROOT / "fixtures"
    for part in parts:
        path = path / part
    return path


def generated_dir(*parts: str) -> Path:
    path = SCRIPTS_ROOT / "generated"
    for part in parts:
        path = path / part
    return path

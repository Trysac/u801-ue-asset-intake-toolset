"""Nanite decision."""

from __future__ import annotations

from .errors import IntakeError


def decide_nanite(triangles: int, is_static: bool, threshold: int = 20000) -> bool:
    """Return True when a static mesh has at least ``threshold`` triangles."""
    if triangles < 0 or threshold < 0:
        raise IntakeError("invalid_manifest", "triangles and threshold must not be negative")
    return bool(is_static and triangles >= threshold)

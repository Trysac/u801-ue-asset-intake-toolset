"""Typed errors of the library."""

from __future__ import annotations


class IntakeError(Exception):
    """Base error; ``code`` is invalid_manifest, path_not_allowed, name_conflict or unknown_fix."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message[:200])
        self.code = code
        self.message = message[:200]

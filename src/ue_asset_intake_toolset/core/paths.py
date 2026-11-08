"""Path normalization: Windows separators and the /Game confinement."""

from __future__ import annotations

from .errors import IntakeError

MAX_PATH_LENGTH = 512


def _clean(path: object) -> str:
    if not isinstance(path, str) or len(path) > MAX_PATH_LENGTH:
        raise IntakeError("path_not_allowed", "path must be a string of at most 512 characters")
    text = path.strip().replace("\\", "/")
    if any(ord(ch) < 32 for ch in text):
        raise IntakeError("path_not_allowed", "path contains control characters")
    return text


def normalize_game_path(path: object) -> str:
    """Return ``path`` with forward slashes, confined to ``/Game``.

    Raises:
        IntakeError: code ``path_not_allowed`` for anything outside /Game.
    """
    text = _clean(path)
    while "//" in text:
        text = text.replace("//", "/")
    if len(text) > 1:
        text = text.rstrip("/")
    parts = text.split("/")
    if ".." in parts or "." in parts:
        raise IntakeError("path_not_allowed", "path must not contain relative segments")
    if text != "/Game" and not text.startswith("/Game/"):
        raise IntakeError("path_not_allowed", "path must be under /Game")
    return text


def normalize_source_path(path: object) -> str:
    """Return a disk source path with forward slashes.

    Raises:
        IntakeError: code ``invalid_manifest`` when empty or malformed.
    """
    try:
        text = _clean(path)
    except IntakeError as exc:
        raise IntakeError("invalid_manifest", exc.message) from exc
    if not text:
        raise IntakeError("invalid_manifest", "source path must not be empty")
    return text

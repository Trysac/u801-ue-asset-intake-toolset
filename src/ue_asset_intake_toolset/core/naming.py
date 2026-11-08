"""Safe, collision-free asset names with the Epic prefix table."""

from __future__ import annotations

import re
from collections.abc import Iterable

from .errors import IntakeError

PREFIXES: dict[str, str] = {
    "StaticMesh": "SM_",
    "SkeletalMesh": "SK_",
    "Texture": "T_",
    "Material": "M_",
    "MaterialInstance": "MI_",
}
MAX_INPUT_LENGTH = 1024
_EXT = re.compile(r"\.[A-Za-z0-9]{1,5}$")
_WORD = re.compile(r"[A-Za-z0-9]+")


def safe_asset_name(
    name: str, asset_type: str, existing: Iterable[str], max_length: int = 64
) -> str:
    """Return a valid PascalCase asset name with its type prefix, never in ``existing``.

    On a collision the smallest free numeric suffix ``_01``, ``_02``... is used.
    Comparison with ``existing`` is case-insensitive, like Unreal.

    Raises:
        IntakeError: ``invalid_manifest`` for an unknown type, oversized input or tiny limit.
    """
    prefix = PREFIXES.get(asset_type)
    if prefix is None:
        raise IntakeError("invalid_manifest", f"unknown asset type {asset_type[:50]!r}")
    if not isinstance(name, str) or len(name) > MAX_INPUT_LENGTH:
        raise IntakeError("invalid_manifest", "name must be a string of at most 1024 characters")
    if max_length < 8:
        raise IntakeError("invalid_manifest", "max_length must be at least 8")
    stem = name.replace("\\", "/").split("/")[-1]
    stem = _EXT.sub("", stem)
    if stem.startswith(prefix):
        stem = stem[len(prefix) :]
    body = "".join(w[0].upper() + w[1:] for w in _WORD.findall(stem)) or "Asset"
    base = (prefix + body)[:max_length]
    taken = {e.lower() for e in existing}
    if base.lower() not in taken:
        return base
    n = 1
    while True:
        suffix = f"_{n:02d}"
        candidate = base[: max_length - len(suffix)] + suffix
        if candidate.lower() not in taken:
            return candidate
        n += 1

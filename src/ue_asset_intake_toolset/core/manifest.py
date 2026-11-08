"""Import manifest validation (stdlib, JSON-Schema-like)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .errors import IntakeError
from .naming import PREFIXES
from .provenance import Provenance

MAX_ENTRIES = 1000
_ALLOWED = frozenset({"source_path", "asset_type", "name", "dest_path", "provenance"})


@dataclass(frozen=True)
class ManifestEntry:
    """One validated import entry."""

    source_path: str
    asset_type: str = "StaticMesh"
    name: str | None = None
    dest_path: str = "/Game/Imported"
    provenance: Provenance | None = None


def _fail(index: int, message: str) -> IntakeError:
    return IntakeError("invalid_manifest", f"entry {index}: {message}")


def _entry(index: int, raw: Any) -> ManifestEntry:
    if not isinstance(raw, dict):
        raise _fail(index, "must be an object")
    unknown = sorted(str(k)[:30] for k in raw if k not in _ALLOWED)
    if unknown:
        raise _fail(index, f"unknown keys {unknown[:5]}")
    source = raw.get("source_path")
    if not isinstance(source, str) or not source.strip():
        raise _fail(index, "source_path is required")
    asset_type = raw.get("asset_type", "StaticMesh")
    if asset_type not in PREFIXES:
        raise _fail(index, "asset_type is not supported")
    name = raw.get("name")
    if name is not None and not isinstance(name, str):
        raise _fail(index, "name must be a string")
    dest = raw.get("dest_path", "/Game/Imported")
    if not isinstance(dest, str):
        raise _fail(index, "dest_path must be a string")
    provenance = None
    if raw.get("provenance") is not None:
        try:
            provenance = Provenance.from_dict(raw["provenance"])
        except IntakeError as exc:
            raise _fail(index, exc.message) from exc
    return ManifestEntry(source, asset_type, name, dest, provenance)


def validate_manifest(data: Any) -> tuple[ManifestEntry, ...]:
    """Validate a list of entries, or an object with an ``entries`` list.

    Raises:
        IntakeError: ``invalid_manifest``, naming the entry index when an entry is wrong.
    """
    entries = data.get("entries") if isinstance(data, dict) else data
    if not isinstance(entries, list):
        raise IntakeError("invalid_manifest", "manifest must be a list or an object with entries")
    if len(entries) > MAX_ENTRIES:
        raise IntakeError("invalid_manifest", "manifest has more than 1000 entries")
    return tuple(_entry(i, raw) for i, raw in enumerate(entries))

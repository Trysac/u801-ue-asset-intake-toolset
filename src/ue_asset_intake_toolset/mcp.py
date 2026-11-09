"""MCP-facing functions: flat, JSON-friendly parameters in, one JSON string out.

The Unreal plugin's toolset class (``plugin/AssetIntakeToolset/Content/Python``) only forwards to
these functions with the real ``unreal`` module, so everything an agent sees is tested here with a
fake. Inputs are primitives (complex inputs travel as JSON strings) and every result is a JSON
object whose first key is ``summary``. Errors never raise to the agent: they come back as
``{"summary": "error: ...", "error": {"code": ..., "message": ...}}``.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict, is_dataclass
from typing import Any

from . import adapter
from .adapter import ImportOptions
from .core.errors import IntakeError
from .core.provenance import Provenance

MAX_JSON_CHARS = 1_000_000


def _plain(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {k: _plain(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def to_json(result: Any) -> str:
    """Serialize a result with ``summary`` first."""
    data = _plain(result)
    if isinstance(data, dict) and "summary" in data:
        data = {"summary": data["summary"], **{k: v for k, v in data.items() if k != "summary"}}
    return json.dumps(data, ensure_ascii=False)


def _error(code: str, message: str) -> str:
    return json.dumps(
        {"summary": f"error: {message[:200]}", "error": {"code": code, "message": message[:200]}}
    )


def _run(call: Callable[[], Any]) -> str:
    try:
        return to_json(call())
    except IntakeError as exc:
        return _error(exc.code, exc.message)
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        return _error("unreal_error", f"{type(exc).__name__}: {exc}")


def _parse_json(raw: str, what: str) -> Any:
    if not isinstance(raw, str) or len(raw) > MAX_JSON_CHARS:
        raise IntakeError("invalid_manifest", f"{what} must be a JSON string under 1 MB")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise IntakeError("invalid_manifest", f"{what} is not valid JSON: {exc.msg}") from exc


def _options(
    nanite: str, nanite_threshold: int, collision: bool, material_instance: str, max_texture: int
) -> ImportOptions:
    flags = {"auto": None, "on": True, "off": False}
    if nanite not in flags:
        raise IntakeError("invalid_manifest", "nanite must be auto, on or off")
    return ImportOptions(
        nanite=flags[nanite],
        nanite_threshold=nanite_threshold,
        collision=collision,
        material_instance=material_instance or None,
        max_texture_size=max_texture,
    )


def _provenance(provenance_json: str) -> Provenance | None:
    if not provenance_json:
        return None
    return Provenance.from_dict(_parse_json(provenance_json, "provenance_json"))


def import_static_mesh(
    ue: Any,
    source_path: str,
    dest_folder: str = "/Game/Imported",
    asset_name: str = "",
    nanite: str = "auto",
    nanite_threshold: int = 20000,
    collision: bool = True,
    material_instance: str = "",
    max_texture_size: int = 2048,
    provenance_json: str = "",
    dry_run: bool = True,
) -> str:
    """Import one mesh file and normalize it (see the toolset docstring for details)."""

    def call() -> Any:
        options = _options(nanite, nanite_threshold, collision, material_instance, max_texture_size)
        return adapter.import_static_mesh(
            ue,
            source_path,
            dest_folder,
            asset_name or None,
            _provenance(provenance_json),
            dry_run,
            options,
        )

    return _run(call)


def import_batch(
    ue: Any,
    manifest_json: str,
    batch_limit: int = 5,
    cursor: int = 0,
    nanite: str = "auto",
    collision: bool = True,
    material_instance: str = "",
    max_texture_size: int = 2048,
    dry_run: bool = True,
) -> str:
    """Import a slice of a JSON manifest; returns ``cursor`` to continue (null when done)."""

    def call() -> Any:
        options = _options(nanite, 20000, collision, material_instance, max_texture_size)
        entries = _parse_json(manifest_json, "manifest_json")
        return adapter.import_batch(ue, entries, batch_limit, cursor, dry_run, options)

    return _run(call)


def validate_assets(
    ue: Any,
    folder: str,
    reference_height_cm: float = 180.0,
    tolerance: float = 10.0,
    nanite_threshold: int = 20000,
    max_texture_size: int = 4096,
) -> str:
    """Read-only validation of meshes and textures under ``folder``."""
    return _run(
        lambda: adapter.validate_assets(
            ue,
            folder,
            reference_height_cm=reference_height_cm,
            tolerance=tolerance,
            nanite_threshold=nanite_threshold,
            max_texture_size=max_texture_size,
        )
    )


def fix_assets(ue: Any, fixes_json: str, dry_run: bool = True) -> str:
    """Apply non-destructive fixes given as a JSON list."""
    return _run(lambda: adapter.fix_assets(ue, _parse_json(fixes_json, "fixes_json"), dry_run))


def write_provenance(ue: Any, asset_path: str, provenance_json: str, dry_run: bool = True) -> str:
    """Store provenance (JSON object) as metadata tags on one asset."""

    def call() -> Any:
        provenance = _provenance(provenance_json)
        if provenance is None:
            raise IntakeError("invalid_manifest", "provenance_json is required")
        return adapter.write_provenance(ue, asset_path, provenance, dry_run)

    return _run(call)


def export_provenance_log(ue: Any, folder: str, fmt: str = "md") -> str:
    """Render the provenance log of ``folder`` as md, csv or json."""
    return _run(lambda: adapter.export_provenance_log(ue, folder, fmt))

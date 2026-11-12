"""Thin adapter over the ``unreal`` module (passed in as ``ue``; never imported here).

The Unreal API surface used here is an assumption checked only against a fake.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .compat import box_collision_shape, static_mesh_api
from .core.errors import IntakeError
from .core.manifest import validate_manifest
from .core.naming import safe_asset_name
from .core.nanite import decide_nanite
from .core.paths import normalize_game_path, normalize_source_path
from .core.provenance import FIELDS, Provenance, render_provenance
from .core.validation import AssetInfo, ValidationReport
from .core.validation import validate_assets as _validate_core

TAG_PREFIX = "provenance."
MAX_BATCH_LIMIT = 1000
MAX_FIXES = 1000
FIXES = frozenset(
    {
        "rename_with_redirector",
        "set_texture_max_size",
        "set_lod_group",
        "add_simple_collision",
        "toggle_nanite",
    }
)
_NAME_RE = re.compile(r"[A-Za-z0-9_]{1,64}")


@dataclass(frozen=True)
class ImportResult:
    """Result of one import."""

    summary: str
    asset_path: str
    dry_run: bool


@dataclass(frozen=True)
class BatchResult:
    """Result of a batch import; ``cursor`` is None when finished."""

    summary: str
    results: tuple[ImportResult, ...]
    cursor: int | None


@dataclass(frozen=True)
class FixResult:
    """Result of fix_assets."""

    summary: str
    applied: tuple[str, ...]
    dry_run: bool


@dataclass(frozen=True)
class WriteResult:
    """Result of write_provenance."""

    summary: str
    asset_path: str
    dry_run: bool


@dataclass(frozen=True)
class ExportResult:
    """Result of export_provenance_log."""

    summary: str
    content: str
    count: int
    fmt: str



def _triangle_count(obj, lib) -> int:
    """UE 5.8: StaticMesh.get_num_triangles(lod) (the subsystem has no get_number_triangles)."""
    getter = getattr(obj, "get_num_triangles", None)
    if getter is not None:
        return int(getter(0))
    return int(lib.get_number_triangles(obj, 0))

def _short(path: str) -> str:
    return path.split(".")[0]


def _existing(ue: Any, folder: str) -> set[str]:
    paths = ue.EditorAssetLibrary.list_assets(folder, recursive=False, include_folder=False)
    return {_short(p).rsplit("/", 1)[-1] for p in paths}


def _require(ue: Any, path: str) -> Any:
    obj = ue.EditorAssetLibrary.load_asset(path)
    if obj is None:
        raise IntakeError("invalid_manifest", f"asset not found: {path[:100]}")
    return obj


def _write_tags(ue: Any, asset_path: str, prov: Provenance) -> None:
    obj = _require(ue, asset_path)
    for key, value in prov.to_dict().items():
        ue.EditorAssetLibrary.set_metadata_tag(obj, TAG_PREFIX + key, value)


@dataclass(frozen=True)
class ImportOptions:
    """Normalization applied right after an import (static meshes and their textures).

    ``nanite`` None means "decide by triangle count" (static meshes at or above
    ``nanite_threshold`` triangles get Nanite). ``max_texture_size`` 0 leaves textures untouched.
    """

    nanite: bool | None = None
    nanite_threshold: int = 20000
    collision: bool = True
    material_instance: str | None = None
    max_texture_size: int = 2048

    def __post_init__(self) -> None:
        size = self.max_texture_size
        if type(size) is not int or size < 0 or size > 16384 or (size and size & (size - 1)):
            raise IntakeError("invalid_manifest", "max_texture_size must be 0 or a power of two")
        if type(self.nanite_threshold) is not int or self.nanite_threshold < 0:
            raise IntakeError("invalid_manifest", "nanite_threshold must not be negative")


DEFAULT_OPTIONS = ImportOptions()


def _set_nanite(ue: Any, obj: Any, enabled: bool) -> None:
    lib = static_mesh_api(ue)
    settings = lib.get_nanite_settings(obj)
    settings.enabled = enabled
    lib.set_nanite_settings(obj, settings)


def _normalize(ue: Any, new_paths: Sequence[str], options: ImportOptions) -> list[str]:
    """Apply ``options`` to freshly imported assets; return a short note per change."""
    notes: list[str] = []
    material = None
    if options.material_instance:
        material = _require(ue, normalize_game_path(options.material_instance))
    for path in new_paths:
        obj = ue.EditorAssetLibrary.load_asset(path)
        if obj is None:
            continue
        cls = obj.get_class().get_name()
        if cls == "StaticMesh":
            lib = static_mesh_api(ue)
            triangles = _triangle_count(obj, lib)
            nanite = options.nanite
            if nanite is None:
                nanite = decide_nanite(triangles, True, options.nanite_threshold)
            _set_nanite(ue, obj, nanite)
            notes.append(f"{_short(path)}: nanite={'on' if nanite else 'off'}")
            if options.collision and lib.get_simple_collision_count(obj) == 0:
                lib.add_simple_collisions(obj, box_collision_shape(ue))
                notes.append(f"{_short(path)}: box collision")
            if material is not None:
                obj.set_material(0, material)
                notes.append(f"{_short(path)}: material")
        elif cls == "Texture2D" and options.max_texture_size:
            obj.set_editor_property("max_texture_size", options.max_texture_size)
            notes.append(f"{_short(path)}: max texture {options.max_texture_size}")
        ue.EditorAssetLibrary.save_loaded_asset(obj)
    return notes


def _import_one(
    ue: Any,
    source: str,
    dest: str,
    name_hint: str | None,
    asset_type: str,
    provenance: Provenance | None,
    dry_run: bool,
    taken: dict[str, set[str]],
    options: ImportOptions = DEFAULT_OPTIONS,
) -> ImportResult:
    if dest not in taken:
        taken[dest] = _existing(ue, dest)
    name = safe_asset_name(name_hint or source, asset_type, taken[dest])
    taken[dest].add(name)
    asset_path = f"{dest}/{name}"
    if dry_run:
        return ImportResult(
            f"dry run: would import {source[:80]} as {asset_path}", asset_path, True
        )
    before = set(_list(ue, dest))
    with ue.ScopedEditorTransaction(f"Import {name}"):
        task = ue.AssetImportTask()
        task.set_editor_property("filename", source)
        task.set_editor_property("destination_path", dest)
        task.set_editor_property("destination_name", name)
        task.set_editor_property("automated", True)
        task.set_editor_property("save", True)
        ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        new_paths = [p for p in _list(ue, dest) if p not in before]
        notes = _normalize(ue, new_paths, options) if asset_type == "StaticMesh" else []
        if provenance is not None:
            _write_tags(ue, asset_path, provenance)
    detail = f" ({'; '.join(notes)[:300]})" if notes else ""
    return ImportResult(f"imported {source[:80]} as {asset_path}{detail}", asset_path, False)


def import_static_mesh(
    ue: Any,
    source_path: str,
    dest_path: str,
    name: str | None = None,
    provenance: Provenance | None = None,
    dry_run: bool = True,
    options: ImportOptions = DEFAULT_OPTIONS,
) -> ImportResult:
    """Import one static mesh under ``dest_path`` with a safe name (dry run by default).

    After a real import the new mesh and its textures are normalized with ``options``.
    """
    dest = normalize_game_path(dest_path)
    source = normalize_source_path(source_path)
    return _import_one(ue, source, dest, name, "StaticMesh", provenance, dry_run, {}, options)


def import_batch(
    ue: Any,
    entries: Any,
    batch_limit: int = 5,
    cursor: int = 0,
    dry_run: bool = True,
    options: ImportOptions = DEFAULT_OPTIONS,
) -> BatchResult:
    """Import up to ``batch_limit`` manifest entries starting at ``cursor``."""
    parsed = validate_manifest(entries)
    if type(batch_limit) is not int or not 1 <= batch_limit <= MAX_BATCH_LIMIT:
        raise IntakeError("invalid_manifest", "batch_limit must be between 1 and 1000")
    if type(cursor) is not int or not 0 <= cursor <= len(parsed):
        raise IntakeError("invalid_manifest", "cursor is out of range")
    plan = [
        (e, normalize_game_path(e.dest_path), normalize_source_path(e.source_path)) for e in parsed
    ]
    chunk = plan[cursor : cursor + batch_limit]
    taken: dict[str, set[str]] = {}
    results = tuple(
        _import_one(ue, src, dest, e.name, e.asset_type, e.provenance, dry_run, taken, options)
        for e, dest, src in chunk
    )
    end = cursor + len(chunk)
    next_cursor = end if end < len(plan) else None
    verb = "dry run: would import" if dry_run else "imported"
    return BatchResult(f"{verb} {len(results)} of {len(plan)} entries", results, next_cursor)


def write_provenance(
    ue: Any, asset_path: str, provenance: Provenance, dry_run: bool = True
) -> WriteResult:
    """Store provenance as metadata tags on an asset."""
    path = normalize_game_path(asset_path)
    if dry_run:
        return WriteResult(f"dry run: would write provenance to {path}", path, True)
    with ue.ScopedEditorTransaction("Write provenance"):
        _write_tags(ue, path, provenance)
    return WriteResult(f"wrote provenance to {path}", path, False)


def _describe(ue: Any, path: str) -> AssetInfo | None:
    obj = ue.EditorAssetLibrary.load_asset(path)
    if obj is None:
        return None
    cls = obj.get_class().get_name()
    if cls == "StaticMesh":
        lib = static_mesh_api(ue)
        return AssetInfo(
            path,
            "StaticMesh",
            triangles=_triangle_count(obj, lib),
            bounds_height_cm=float(obj.get_bounds().box_extent.z) * 2.0,
            has_collision=lib.get_simple_collision_count(obj) > 0,
            nanite_enabled=bool(lib.get_nanite_settings(obj).enabled),
        )
    if cls == "Texture2D":
        size = (int(obj.blueprint_get_size_x()), int(obj.blueprint_get_size_y()))
        return AssetInfo(path, "Texture", texture_size=size)
    return None


def _list(ue: Any, folder: str) -> list[str]:
    paths = ue.EditorAssetLibrary.list_assets(folder, recursive=True, include_folder=False)
    return sorted({_short(p) for p in paths})


def validate_assets(
    ue: Any,
    folder: str,
    *,
    reference_height_cm: float = 180.0,
    tolerance: float = 10.0,
    nanite_threshold: int = 20000,
    max_texture_size: int = 4096,
) -> ValidationReport:
    """Validate static meshes and textures below ``folder`` (read-only)."""
    root = normalize_game_path(folder)
    infos = [i for i in (_describe(ue, p) for p in _list(ue, root)) if i is not None]
    return _validate_core(
        infos,
        reference_height_cm=reference_height_cm,
        tolerance=tolerance,
        nanite_threshold=nanite_threshold,
        max_texture_size=max_texture_size,
    )


@dataclass(frozen=True)
class _Fix:
    name: str
    asset: str
    param: Any


def _plan_fix(index: int, raw: Any) -> _Fix:
    if not isinstance(raw, Mapping):
        raise IntakeError("invalid_manifest", f"fix {index}: must be an object")
    fix = raw.get("fix")
    if not isinstance(fix, str) or fix not in FIXES:
        raise IntakeError("unknown_fix", f"fix {index}: unknown fix {str(fix)[:50]!r}")
    asset = normalize_game_path(raw.get("asset", ""))
    param: Any = None
    ok = True
    if fix == "rename_with_redirector":
        param = raw.get("new_name")
        ok = isinstance(param, str) and bool(_NAME_RE.fullmatch(param))
    elif fix == "set_texture_max_size":
        param = raw.get("size")
        ok = type(param) is int and 1 <= param <= 16384 and param & (param - 1) == 0
    elif fix == "set_lod_group":
        param = raw.get("group")
        ok = isinstance(param, str) and bool(_NAME_RE.fullmatch(param))
    elif fix == "toggle_nanite":
        param = raw.get("enabled")
        ok = isinstance(param, bool)
    if not ok:
        raise IntakeError("invalid_manifest", f"fix {index}: invalid parameter for {fix}")
    return _Fix(fix, asset, param)


def _rename_target(fix: _Fix) -> str:
    return fix.asset.rsplit("/", 1)[0] + "/" + str(fix.param)


def _apply(ue: Any, fix: _Fix) -> None:
    if fix.name == "rename_with_redirector":
        ue.EditorAssetLibrary.rename_asset(fix.asset, _rename_target(fix))
        return
    obj = _require(ue, fix.asset)
    if fix.name == "set_texture_max_size":
        obj.set_editor_property("max_texture_size", fix.param)
    elif fix.name == "set_lod_group":
        obj.set_editor_property("lod_group", fix.param)
    elif fix.name == "add_simple_collision":
        static_mesh_api(ue).add_simple_collisions(obj, box_collision_shape(ue))
    else:
        _set_nanite(ue, obj, bool(fix.param))


def fix_assets(ue: Any, fixes: Sequence[Any], dry_run: bool = True) -> FixResult:
    """Apply non-destructive fixes; every fix is validated before anything is touched."""
    if not isinstance(fixes, list) or len(fixes) > MAX_FIXES:
        raise IntakeError("invalid_manifest", "fixes must be a list of at most 1000 items")
    plan = [_plan_fix(i, raw) for i, raw in enumerate(fixes)]
    for fix in plan:
        if fix.name == "rename_with_redirector" and ue.EditorAssetLibrary.does_asset_exist(
            _rename_target(fix)
        ):
            raise IntakeError("name_conflict", f"target exists: {_rename_target(fix)[:100]}")
    applied = tuple(f"{f.name}:{f.asset}" for f in plan)
    if dry_run:
        return FixResult(f"dry run: would apply {len(plan)} fixes", applied, True)
    with ue.ScopedEditorTransaction("Apply asset fixes"):
        for fix in plan:
            _apply(ue, fix)
    return FixResult(f"applied {len(plan)} fixes", applied, False)


def export_provenance_log(ue: Any, folder: str, fmt: str = "md") -> ExportResult:
    """Render the provenance of every tagged asset below ``folder`` (read-only)."""
    root = normalize_game_path(folder)
    if fmt not in ("md", "csv", "json"):
        raise IntakeError("invalid_manifest", "format must be md, csv or json")
    records: list[tuple[str, Provenance]] = []
    for path in _list(ue, root):
        obj = ue.EditorAssetLibrary.load_asset(path)
        if obj is None:
            continue
        tags = {f: ue.EditorAssetLibrary.get_metadata_tag(obj, TAG_PREFIX + f) for f in FIELDS}
        if tags["origin"]:
            records.append((path, Provenance.from_dict(tags)))
    content = render_provenance(records, fmt)
    return ExportResult(f"exported {len(records)} records as {fmt}", content, len(records), fmt)

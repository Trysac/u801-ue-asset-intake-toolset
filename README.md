# ue-asset-intake-toolset

[![PyPI version](https://img.shields.io/pypi/v/trysac-ue-asset-intake-toolset)](https://pypi.org/project/trysac-ue-asset-intake-toolset/)
[![License: MIT](https://img.shields.io/pypi/l/trysac-ue-asset-intake-toolset)](LICENSE)
[![CI](https://github.com/Trysac/u801-ue-asset-intake-toolset/actions/workflows/ci.yml/badge.svg)](https://github.com/Trysac/u801-ue-asset-intake-toolset/actions/workflows/ci.yml)

Pure core and Unreal adapter of an Unreal MCP toolset that imports, validates and normalizes 3D assets and textures with a provenance log.

## Problem

Agents driving Unreal Engine 5.8 through its experimental Unreal MCP server import AI-generated meshes and textures with wrong names, scale, Nanite, collision and texture sizes, and leave no license provenance. Each fix is manual editor work. This package provides a pure core (naming, Nanite decision, manifest validation, asset validation, provenance rendering, path confinement) and a thin adapter that takes the `unreal` module as its first argument to import, validate, fix and log assets.

## Install in Unreal Engine (the MCP toolset)

1. Build the plugin: `uv run python tools/build_plugin.py` (or download the zip from a release). It
   creates `dist/AssetIntakeToolset-<version>.zip`.
2. Unzip it into `<YourProject>/Plugins/` (you get `Plugins/AssetIntakeToolset/`).
3. In the editor enable **Unreal MCP**, **All Toolsets** and **Asset Intake Toolset**, restart, and
   turn on *Editor Preferences > General > Model Context Protocol > Auto Start Server*.
4. Run `ModelContextProtocol.GenerateClientConfig ClaudeCode` in the console (writes `.mcp.json`),
   then start your agent from the project root. If the editor was already running, run
   `ModelContextProtocol.RefreshTools`.
5. The agent finds the toolset `AssetIntakeTools` through `list_toolsets` and calls it with
   `call_tool`. See [docs/AGENT_USAGE.md](docs/AGENT_USAGE.md) and the optional Claude Code skill in
   [skill/SKILL.md](skill/SKILL.md).

Requirements: Unreal Engine 5.8 with the experimental Unreal MCP and Toolset Registry plugins.
Python only, nothing to compile. Status: the logic and the MCP layer are tested in CI against a fake
`unreal` module; the in-editor check is `tests/ue_smoke.py` (see [docs/TESTING.md](docs/TESTING.md)).

## Install as a Python library

```sh
pip install trysac-ue-asset-intake-toolset
# or
uv add trysac-ue-asset-intake-toolset
```

Requires Python 3.10 or later. Standard library only at runtime.

## Usage

```python
from ue_asset_intake_toolset import decide_nanite, safe_asset_name

print(safe_asset_name("my cool mesh!.fbx", "StaticMesh", existing=set()))  # SM_MyCoolMesh
print(decide_nanite(triangles=60000, is_static=True, threshold=20000))  # True
```

Adapter functions (`import_static_mesh`, `import_batch`, `validate_assets`, `fix_assets`, `write_provenance`, `export_provenance_log`) take the `unreal` module (or a fake) as their first argument. Mutating functions default to `dry_run=True`. After a real import, `ImportOptions` normalizes the new mesh and its textures: Nanite (`auto` by triangle count, `on` or `off`), simple box collision, a material instance in slot 0 and a texture size cap.

`ue_asset_intake_toolset.mcp` exposes the same six operations with flat, JSON-friendly parameters and a JSON string result (first key `summary`; errors come back as `{"summary": "error: ...", "error": {...}}` instead of raising). The plugin's toolset class forwards to it.

## Public API

Core (pure, imports nothing from Unreal):

- `safe_asset_name(name, asset_type, existing, max_length=64)`: returns a PascalCase name with its prefix (`SM_`, `SK_`, `T_`, `M_`, `MI_`), never equal to a name in `existing` (case-insensitive); collisions get `_01`, `_02`, and so on.
- `decide_nanite(triangles, is_static, threshold=20000)`: True when a static mesh has at least `threshold` triangles.
- `validate_manifest(data)`: returns a tuple of `ManifestEntry` from a list or an object with an `entries` list.
- `validate_assets(assets, *, reference_height_cm=180.0, tolerance=10.0, nanite_threshold=20000, max_texture_size=4096)`: returns a `ValidationReport` with sorted `Violation` records.
- `Provenance(origin, tool, plan, prompt_ref, license, source_url, created_at)`: `origin` is one of `generated`, `in_engine`, `sourced`; `created_at` is ISO 8601.

Adapter (each takes `ue` first):

- `import_static_mesh(ue, source_path, dest_path, name=None, provenance=None, dry_run=True, options=ImportOptions())` returns `ImportResult`.
- `import_batch(ue, entries, batch_limit=5, cursor=0, dry_run=True, options=ImportOptions())` returns `BatchResult`; `cursor` is None when finished.
- `validate_assets(ue, folder, *, reference_height_cm=180.0, tolerance=10.0, nanite_threshold=20000, max_texture_size=4096)` is read-only and returns `ValidationReport`.
- `fix_assets(ue, fixes, dry_run=True)` returns `FixResult`. Allowed fixes: `rename_with_redirector` (`new_name`), `set_texture_max_size` (`size`, power of two up to 16384), `set_lod_group` (`group`), `add_simple_collision`, `toggle_nanite` (`enabled`). Assets are never deleted.
- `write_provenance(ue, asset_path, provenance, dry_run=True)` returns `WriteResult`.
- `export_provenance_log(ue, folder, fmt='md')` is read-only and returns `ExportResult`; `fmt` is `md`, `csv` or `json`.

Errors: every rejected input raises `IntakeError` with a `code` and a message truncated to 200 characters. Codes: `invalid_manifest`, `path_not_allowed`, `name_conflict`, `unknown_fix`.

Limits: 1000 manifest entries; `batch_limit` 1 to 1000; 1000 fixes per call; names up to 1024 characters; paths up to 512 characters; provenance fields up to 2000 characters; 10000 assets to validate; 10000 provenance records to export. Paths must be under `/Game` with forward slashes (backslashes are converted) and must not contain `.` or `..` segments.

## Why not the Unreal Interchange importer

The specification does not name a best-known alternative for this package, so this section is omitted.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Testing](docs/TESTING.md) and [security](docs/SECURITY.md)
- [Project record](docs/PROJECT.md) and [stack](docs/STACK.md)

## License

[MIT](LICENSE) (c) 2026 Miguel Gomez

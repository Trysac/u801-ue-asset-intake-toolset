# Architecture

## Purpose

`trysac-ue-asset-intake-toolset` is a small Python library with no runtime dependencies. It imports, validates and normalizes 3D assets and textures for Unreal Engine 5.8 and records their provenance.

## Shape

```text
caller code --> ue_asset_intake_toolset (public API re-exported in __init__.py)
                    |
                    +-- core/   pure logic, never imports unreal
                    +-- adapter.py  functions that receive the unreal module as ue
```

- `core/naming.py`: `safe_asset_name` and the prefix table.
- `core/nanite.py`: `decide_nanite`.
- `core/manifest.py`: `validate_manifest` and `ManifestEntry`, a stdlib validator.
- `core/validation.py`: `validate_assets` over plain `AssetInfo` descriptions, producing `Violation` records.
- `core/provenance.py`: `Provenance` and rendering to md, csv and json.
- `core/paths.py`: path normalization and the `/Game` confinement.
- `core/errors.py`: `IntakeError`.
- `adapter.py`: the six Unreal-facing functions. Each takes `ue: Any` as its first parameter, never imports `unreal` at module level, and wraps mutations in `ue.ScopedEditorTransaction`.

## Public API

The names listed in `__all__` of `src/ue_asset_intake_toolset/__init__.py` are the public API. Anything else is internal and may change without a major version.

## Errors

Invalid input raises `IntakeError`, a subclass of `Exception` with a `code` attribute (`invalid_manifest`, `path_not_allowed`, `name_conflict` or `unknown_fix`). The library does not print or exit.

## Side effects

The core has no I/O and no global state. The adapter performs effects only through the `ue` object it is given. Dry-run is the default for every mutating adapter function.

## Unreal integration

The Unreal plugin packaging (`.uplugin`, the `ToolsetDefinition` class and its tool decorators) is out of scope for this package. The adapter functions are the intended entry points for that layer. The Unreal API calls inside the adapter are assumptions that were checked only against a fake module.

## Decisions

No architecture decision records are present in the reviewed tree.

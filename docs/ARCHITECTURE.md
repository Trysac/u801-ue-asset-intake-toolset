# Architecture

## Purpose

`trysac-ue-asset-intake-toolset` is a small Python library with no runtime dependencies. It imports, validates and normalizes 3D assets and textures for Unreal Engine 5.8 and records their provenance.

## Shape

```text
AI agent --MCP--> Unreal MCP server --> Toolset Registry
                                            |
   plugin/AssetIntakeToolset/Content/Python/asset_intake_toolset_mcp.py  (AssetIntakeTools)
                                            |  forwards with the real unreal module
                                            v
   ue_asset_intake_toolset.mcp      flat params in, JSON string out, errors as data
                                            v
   ue_asset_intake_toolset.adapter  functions that receive the unreal module as ue
          |                 \
          v                  compat.py  subsystem-or-legacy API resolution
   core/  pure logic, never imports unreal
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

- `plugin/AssetIntakeToolset/AssetIntakeToolset.uplugin` declares a Python-only editor plugin that
  depends on `PythonScriptPlugin` and `ToolsetRegistry`.
- `plugin/AssetIntakeToolset/Content/Python/asset_intake_toolset_mcp.py` defines
  `AssetIntakeTools(unreal.ToolsetDefinition)`; each tool is a static method marked with
  `@toolset_registry.tool_call`, with Google-style docstrings that the registry turns into the tool
  schema. It contains no logic: it forwards to `mcp.py`.
- `tools/build_plugin.py` copies the plugin and vendors the package into `Content/Python/` so the
  editor's Python can import it without pip.
- `compat.py` prefers UE 5.x editor subsystems and falls back to the deprecated libraries.
- The real-engine check is `tests/ue_smoke.py` plus the manual steps in `docs/TESTING.md`.

## Decisions

See `docs/decisions/` (0002: pure core with an injected adapter; 0003: plugin shell, JSON results
and API compatibility).

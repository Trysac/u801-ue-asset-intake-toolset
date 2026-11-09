# Testing

## Running

```sh
uv run python scripts/check.py                 # every gate (lint, format, types, tests, docs...)
uv run pytest --cov=ue_asset_intake_toolset    # tests with branch coverage report
uv run python tools/build_plugin.py            # build the Unreal plugin zip into dist/
```

## Policy

- Coverage target for `src/ue_asset_intake_toolset` is 85 % (branch coverage).
- Tests call the public API and assert return values, `IntakeError` codes, the JSON returned by the
  MCP layer and the calls recorded on the fake `unreal` module.
- Deterministic: no network, no wall clock, no dependence on test order.

## Tests in CI (no Unreal needed)

| File | What it covers |
|---|---|
| `tests/test_core.py`, `tests/test_properties.py` | Naming, Nanite, manifest, validation, provenance, paths (Hypothesis properties, golden files in `tests/golden/`). |
| `tests/test_adapter.py` | Adapter against `tests/fakes/unreal.py` (`FakeUnreal`, `Tripwire`). |
| `tests/test_mcp.py` | MCP layer: dry runs make no mutating call, real imports normalize Nanite/collision/material/textures, errors come back as data, the UE 5.8 subsystem path (`FakeUnreal58`) and the legacy library path. |
| `tests/test_plugin_shell.py` | Loads `plugin/.../Content/Python/asset_intake_toolset_mcp.py` with a fake `unreal` and a fake `toolset_registry`: every MCP function is a documented `tool_call` static method returning `str`, and each forwards correctly. |
| `tests/test_build_plugin.py` | The plugin zip contains the `.uplugin`, the toolset module and the vendored package; the `.uplugin` depends on `PythonScriptPlugin` and `ToolsetRegistry` and its version matches the package. |

## In-editor check (manual, Unreal Engine 5.8)

CI cannot run Unreal, so these steps are the acceptance test for the real engine. Never mark the
plugin as verified in Unreal without running them.

1. Install the plugin (README, "Install in Unreal Engine") in a blank UE 5.8 project.
2. Compare the decorator order in `asset_intake_toolset_mcp.py` (`@staticmethod` above
   `@toolset_registry.tool_call`) with the engine's own example,
   `Engine/Plugins/Experimental/ToolsetRegistry/Content/Python/toolset_registry/toolsets/core/actor.py`,
   and match it if it differs.
3. Enable Python *Developer Mode* (Editor Preferences > Plugins > Python), restart, and check in
   `Intermediate/PythonStub/unreal.py` that `StaticMeshEditorSubsystem` (or
   `EditorStaticMeshLibrary`), `ScriptCollisionShapeType` (or `ScriptingCollisionShapeType`),
   `AssetImportTask`, `EditorAssetLibrary.set_metadata_tag` and `StaticMesh.set_material` exist.
4. Run `py "<repo>/tests/ue_smoke.py"` in the Output Log (Python). Open
   `Saved/Smoke/u801-ue-asset-intake-toolset.json`: every step must have `"ok": true`.
5. From the agent: `list_toolsets` shows `AssetIntakeTools`; `describe_toolset` lists six tools
   with their parameter descriptions; a dry-run `import_static_mesh` returns a summary.
6. Real import of one FBX and one GLB with `dry_run=false`: check Nanite, collision, material,
   texture max size and the provenance metadata in the editor; Ctrl+Z undoes the import.
7. Delete `/Game/__Smoke_AssetIntake__` by hand. Record the date, engine version and result in
   `docs/PROJECT.md`.

## Not covered

Interchange-specific import options, skeletal mesh retargeting, and behavior on engine versions
other than 5.8.

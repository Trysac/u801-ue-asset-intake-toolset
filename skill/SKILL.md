---
name: ue-asset-intake
description: Import AI-generated or external 3D models and textures into Unreal Engine 5.8 through the AssetIntakeTools MCP toolset — safe names, Nanite by triangle count, box collision, material instance, texture caps — then validate folders and export a provenance log. Use whenever an asset file must enter /Game.
---
# Asset intake (Unreal MCP toolset `AssetIntakeTools`)

Requires the Asset Intake Toolset plugin enabled and the Unreal MCP server connected.

1. **Plan:** `call_tool` → `AssetIntakeTools.import_static_mesh` with `dry_run: true`. Read `summary`
   and `asset_path`.
2. **Import:** same call with `dry_run: false`. Always pass `provenance_json` (origin `generated`,
   `in_engine` or `sourced`, the tool and plan used, a prompt reference, the license, ISO date).
   Use `material_instance` for the project's master toon/PBR instance and `max_texture_size`
   (1024 for small props, 2048 for hero assets).
3. **Many files:** `import_batch` with a JSON manifest, 5 entries per call, following `cursor`.
4. **Check:** `validate_assets` on the folder; fix with `fix_assets` (dry run first).
5. **Record:** `export_provenance_log` (`md`) into the project's asset log / credits.

Rules: one MCP call at a time; commit before large real imports; never claim an asset is licensed
without a provenance record; if a result has `error`, read `error.code` and fix the input instead of
retrying blindly.

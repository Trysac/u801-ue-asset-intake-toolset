# Project record

## Objective

Provide a pure core and a thin Unreal adapter that import, validate and normalize 3D assets and textures for agents driving Unreal Engine 5.8 through its experimental Unreal MCP server, and record their provenance. The package targets the case where AI-generated meshes and textures arrive with wrong names, scale, Nanite, collision and texture sizes, and without license provenance.

## Scope

- In scope: the pure core (naming, Nanite decision, manifest validation, asset validation, provenance rendering, path confinement) and the adapter functions `import_static_mesh`, `import_batch`, `validate_assets`, `fix_assets`, `write_provenance` and `export_provenance_log`, tested on a fake `unreal` module.
- In scope since 0.2.0: the Unreal plugin (`.uplugin`, `ToolsetDefinition` shell), the `mcp` layer, post-import normalization and the subsystem compatibility layer.
- Out of scope: retopology, custom LODs, skeletal retargeting and advanced Interchange configuration.
- Naming deviation: the package is named `ue_asset_intake_toolset` rather than `ue_asset_intake`.

## Timeline

| Date | Event |
|---|---|
| 2026-11-08 | Repository created from the factory utility template; factory run (core + adapter). |
| 2026-11-08 | Interactive session (Claude Code): plugin shell, `mcp` layer, normalization, compat layer, build tool, smoke test, skill, docs (0.2.0). Not yet verified inside Unreal. |
| pending | In-editor verification on UE 5.8 (`docs/TESTING.md`): date, engine version, smoke result. |

## Effort metrics

| Metric | Value |
|---|---|
| Tokens (input / output) | 431426 / 198226 |
| Time | pending measurement |
| Fix rounds | pending measurement (up to 4 allowed) |
| Cost (USD) | budget 1.3 USD; actual pending measurement |

## Factory run u801 (measured from API usage)

| Phase | Model | Batch | Input | Output | Cache write | Cache read | Cost (USD) |
|---|---|---|---|---|---|---|---|
| generation | claude-sonnet-5-5 | yes | 2473 | 128000 | 5188 | 0 | 0.6528 |
| generation | claude-sonnet-5-5 | yes | 2473 | 50784 | 0 | 5188 | 0.2569 |
| fix-1 | claude-sonnet-5-5 | no | 4 | 704 | 16371 | 15517 | 0.0495 |
| fix-2 | claude-sonnet-5-5 | no | 14 | 1912 | 12791 | 130158 | 0.0641 |
| audit | claude-sonnet-5-5 | no | 12 | 4532 | 39028 | 140093 | 0.1569 |
| fix-3 | claude-sonnet-5-5 | no | 6 | 2418 | 9631 | 42762 | 0.0525 |
| docs | claude-haiku-5-5 | no | 92726 | 9876 | 0 | 0 | 0.0142 |

Total: $1.2471. Prices: Anthropic list prices.

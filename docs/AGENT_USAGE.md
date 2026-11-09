# Agent usage

Once the plugin is enabled, the Unreal MCP server lists the toolset `AssetIntakeTools`. With the
default *tool search* mode the agent sees three meta-tools: `list_toolsets`, `describe_toolset` and
`call_tool`. Calls run one at a time on the editor's game thread: never issue them in parallel.

Every tool returns a JSON string. The first key is always `summary` (one line). Errors are data:
`{"summary": "error: ...", "error": {"code": "...", "message": "..."}}` with codes
`invalid_manifest`, `path_not_allowed`, `name_conflict`, `unknown_fix` or `unreal_error`.
Mutating tools default to `dry_run: true`: call once to see the plan, then again with `false`.

## Typical flow for an AI-generated mesh

1. `import_static_mesh` with `dry_run: true`, check `asset_path`.
2. `import_static_mesh` with `dry_run: false` and `provenance_json`.
3. `validate_assets` on the folder; `fix_assets` for what it reports.
4. At the end of the day, `export_provenance_log` with `fmt: "md"` for the credits and the dev log.

## import_static_mesh

```json
{"toolset": "AssetIntakeTools", "tool": "import_static_mesh", "arguments": {
  "source_path": "D:/gen/rock_01.glb", "dest_folder": "/Game/Art/Env",
  "nanite": "auto", "collision": true, "material_instance": "/Game/Art/Materials/MI_Toon_Rock",
  "max_texture_size": 1024,
  "provenance_json": "{\"origin\":\"generated\",\"tool\":\"Meshy\",\"plan\":\"Pro\",\"prompt_ref\":\"rock-01\",\"license\":\"commercial (paid plan)\",\"source_url\":\"\",\"created_at\":\"2026-11-12T10:00:00Z\"}",
  "dry_run": false}}
```

```json
{"summary": "imported D:/gen/rock_01.glb as /Game/Art/Env/SM_Rock01 (/Game/Art/Env/SM_Rock01: nanite=on; /Game/Art/Env/SM_Rock01: box collision; ...)",
 "asset_path": "/Game/Art/Env/SM_Rock01", "dry_run": false}
```

## import_batch

`manifest_json` is a JSON list (or `{"entries": [...]}`) of objects with `source_path` and optional
`asset_type`, `name`, `dest_path`, `provenance`. Process `batch_limit` entries per call and pass the
returned `cursor` until it is `null`.

```json
{"summary": "imported 5 of 12 entries", "results": [{"summary": "...", "asset_path": "...", "dry_run": false}], "cursor": 5}
```

## validate_assets

```json
{"toolset": "AssetIntakeTools", "tool": "validate_assets", "arguments": {"folder": "/Game/Art"}}
```

Returns `violations` with codes such as `bad_name`, `scale_anomaly`, `missing_collision`,
`nanite_mismatch`, `texture_too_large` and `texture_not_pow2`.

## fix_assets

```json
{"toolset": "AssetIntakeTools", "tool": "fix_assets", "arguments": {
  "fixes_json": "[{\"fix\": \"set_texture_max_size\", \"asset\": \"/Game/Art/T_Moss\", \"size\": 1024}]",
  "dry_run": false}}
```

Allowed fixes: `rename_with_redirector` (`new_name`), `set_texture_max_size` (`size`),
`set_lod_group` (`group`), `add_simple_collision`, `toggle_nanite` (`enabled`). Nothing is deleted.

## write_provenance and export_provenance_log

`write_provenance` stores the seven provenance fields as metadata tags on one asset.
`export_provenance_log` renders every tagged asset under a folder as `md`, `csv` or `json`; use it
for credits, license declarations and dev logs.

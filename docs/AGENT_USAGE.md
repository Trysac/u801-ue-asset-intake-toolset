# Agent usage

This page shows how an agent would call the toolset once the Unreal plugin wraps the adapter
functions as MCP tools. The plugin packaging (`.uplugin`, `Content/Python/`, the
`ToolsetDefinition` class) is built separately; what is described here is the behavior of the
adapter, which is tested only against a fake `unreal` module and never inside Unreal.

Mutating tools default to `dry_run: true`. Every result carries a one-line `summary`.

## import_batch

Request:

```json
{"tool": "import_batch", "arguments": {"entries": [{"source_path": "C:\\gen\\my cool mesh!.fbx", "dest_path": "/Game/Props"}], "batch_limit": 5, "cursor": 0}}
```

Expected response (dry run):

```json
{"summary": "dry run: would import 1 of 1 entries", "cursor": null}
```

The `cursor` is the index of the next entry, or `null` when the manifest is finished.

## validate_assets

```json
{"tool": "validate_assets", "arguments": {"folder": "/Game/Props"}}
```

The report lists `violations` with codes such as `bad_name`, `scale_anomaly`, `missing_collision`,
`nanite_mismatch`, `texture_too_large` and `texture_not_pow2`.

## fix_assets

```json
{"tool": "fix_assets", "arguments": {"fixes": [{"fix": "set_texture_max_size", "asset": "/Game/Props/T_Moss", "size": 1024}], "dry_run": false}}
```

Allowed fixes: `rename_with_redirector`, `set_texture_max_size`, `set_lod_group`,
`add_simple_collision`, `toggle_nanite`. Nothing is ever deleted.

## Errors

`IntakeError.code` is one of `invalid_manifest`, `path_not_allowed`, `name_conflict`,
`unknown_fix`. Any path outside `/Game` is rejected before the unreal module is touched.

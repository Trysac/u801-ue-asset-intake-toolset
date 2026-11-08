# Security notes

## Threat model

`trysac-ue-asset-intake-toolset` is a library with no network access and no credentials. It runs inside a caller that already holds an Unreal editor session.

Defended:

- **Asset paths**: `normalize_game_path` rejects any path not under `/Game`, any `.` or `..` segment, control characters, and strings longer than 512 characters. Adapter functions that receive such a path raise `IntakeError` with code `path_not_allowed` before calling the `unreal` module.
- **Manifest input**: `validate_manifest` rejects unknown keys, non-string fields, unsupported asset types and more than 1000 entries, naming the entry index.
- **Fixes**: `fix_assets` validates every fix before applying any of them. Parameters are checked against strict patterns (names `[A-Za-z0-9_]{1,64}`, power-of-two texture sizes up to 16384, boolean Nanite flags). A rename is refused with `name_conflict` when the target exists. No asset or actor is deleted.
- **Spreadsheet injection**: CSV export prefixes cells that begin with `=`, `+`, `-`, `@`, tab or carriage return with an apostrophe.
- **Markdown injection**: Markdown export escapes pipes and replaces line breaks in cells.
- **Error messages**: messages are truncated to 200 characters, and asset names in messages are truncated.
- **Dry run**: mutating adapter functions default to `dry_run=True` and record no mutating call in that mode.

Not defended:

- **Source paths**: `normalize_source_path` checks only that the path is non-empty, a string of at most 512 characters and free of control characters. Any disk path is accepted, and the Unreal importer reads it.
- **Caller trust**: the library does not authenticate the caller and does not restrict who may pass `dry_run=False`.
- **Provenance content**: provenance fields are free text up to 2000 characters. The library does not verify licenses, URLs or origins beyond the allowed `origin` values and ISO 8601 `created_at`.
- **Race conditions**: the name-conflict check in `fix_assets` runs before the rename; another editor action between the check and the rename is not prevented.
- **Unreal API behaviour**: the calls made through `ue` are assumptions tested only against a fake. Incorrect assumptions could mutate assets differently from what is described here.
- **Exposure of the MCP server**: access control for the Unreal MCP server is outside this package.

## Publishing

The package holds no credentials and performs no network I/O.

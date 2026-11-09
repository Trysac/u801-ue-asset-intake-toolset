# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-11-08

### Added

- Unreal plugin `plugin/AssetIntakeToolset/` (Python only): `AssetIntakeTools` toolset registered in the Toolset Registry with six documented tools.
- `mcp` module: flat parameters, JSON string results with `summary` first, errors returned as data.
- Post-import normalization (`ImportOptions`): Nanite auto/on/off, box collision, material instance, texture size cap.
- `compat` module: prefers `StaticMeshEditorSubsystem` and the renamed collision enum, falls back to the legacy library.
- `tools/build_plugin.py` (plugin zip with the vendored package), `tests/ue_smoke.py` (in-editor check), `skill/SKILL.md`, ADR 0003.

### Changed

- `docs/AGENT_USAGE.md` describes real `call_tool` usage; `docs/TESTING.md` lists the in-editor acceptance steps.

## [0.1.0] - 2026-11-08

### Added

- Add pure asset-intake core (naming, Nanite, manifest, validation, provenance) and an Unreal adapter with dry-run defaults, batch cursors and non-destructive fixes.
- Initial project structure from the factory utility template.

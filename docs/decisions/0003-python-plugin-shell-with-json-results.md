# Python plugin shell with JSON string results and an API compatibility layer

Status: accepted (pending verification in Unreal Engine 5.8)

## Context

The package must become an Unreal MCP toolset: a `unreal.ToolsetDefinition` subclass in a plugin's
`Content/Python/`, discovered by the Toolset Registry. The registry is experimental, its handling of
complex parameter and return types is not documented in detail, and the `Editor*Library` classes the
adapter used are deprecated in UE 5.x in favor of editor subsystems. Nothing can run in CI inside
Unreal.

## Decision

- Ship a Python-only plugin (`plugin/AssetIntakeToolset/`) whose toolset module only forwards to a
  new `mcp.py` layer. All behavior stays in the package, so it is covered by CI.
- Tools take primitive parameters (str, int, float, bool); structured inputs (manifests, fixes,
  provenance) travel as JSON strings. Every tool returns a JSON string whose first key is `summary`;
  errors are returned as data, never raised to the agent.
- `compat.py` resolves `StaticMeshEditorSubsystem` first and falls back to
  `EditorStaticMeshLibrary`; the collision enum is resolved by name.
- `tools/build_plugin.py` vendors the package into the plugin; no pip inside the editor.

## Consequences

The schema the agent sees is simple and certain to be supported, at the cost of the agent parsing
JSON from a string. If the registry proves to handle dataclasses well, a later version can return
them directly without changing `mcp.py` callers. The decorator order and the engine API names are
confirmed by the manual steps in `docs/TESTING.md`.

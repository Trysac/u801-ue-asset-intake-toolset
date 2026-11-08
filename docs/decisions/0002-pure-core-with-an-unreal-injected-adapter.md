# Pure core with an unreal-injected adapter

Status: accepted (generated, pending human review)

## Context

Agents import AI-generated assets through the experimental Unreal MCP server. The logic must be testable without Unreal, which is only available in a supervised session.

## Decision

Keep all decisions (naming, Nanite, manifest, validation, provenance, path confinement) in a pure stdlib core. The adapter receives the unreal module as its first parameter, never imports it, validates every path and parameter before the first call, wraps mutations in ScopedEditorTransaction and defaults to dry runs. Tests use a recording fake.

## Consequences

Core and adapter logic run in CI with no engine. The Unreal API calls are assumptions that have to be verified in the supervised plugin session. Each new tool needs a fake method as well.

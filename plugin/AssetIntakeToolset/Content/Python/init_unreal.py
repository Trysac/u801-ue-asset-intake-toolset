"""Editor startup: register this plugin's MCP toolset with the Toolset Registry (same pattern as Epic's toolsets)."""

from toolset_registry.registration import Registration

import asset_intake_toolset_mcp

_registration = Registration([asset_intake_toolset_mcp.AssetIntakeTools])
_registration.register()

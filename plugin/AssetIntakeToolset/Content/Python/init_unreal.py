"""Editor startup: register this plugin's MCP toolset with the Toolset Registry."""

import asset_intake_toolset_mcp
from toolset_registry.registration import Registration

_registration = Registration([asset_intake_toolset_mcp.AssetIntakeTools])
_registration.register()

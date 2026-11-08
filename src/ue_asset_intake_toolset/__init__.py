"""Pure core and Unreal adapter of an MCP toolset that imports, validates and normalizes assets."""

from __future__ import annotations

from .adapter import (
    BatchResult,
    ExportResult,
    FixResult,
    ImportResult,
    WriteResult,
    export_provenance_log,
    fix_assets,
    import_batch,
    import_static_mesh,
    validate_assets,
    write_provenance,
)
from .core.errors import IntakeError
from .core.manifest import ManifestEntry, validate_manifest
from .core.naming import safe_asset_name
from .core.nanite import decide_nanite
from .core.provenance import Provenance
from .core.validation import AssetInfo, ValidationReport, Violation

__all__ = [
    "AssetInfo",
    "BatchResult",
    "ExportResult",
    "FixResult",
    "ImportResult",
    "IntakeError",
    "ManifestEntry",
    "Provenance",
    "ValidationReport",
    "Violation",
    "WriteResult",
    "__version__",
    "decide_nanite",
    "export_provenance_log",
    "fix_assets",
    "import_batch",
    "import_static_mesh",
    "safe_asset_name",
    "validate_assets",
    "validate_manifest",
    "write_provenance",
]

__version__ = "0.1.0"

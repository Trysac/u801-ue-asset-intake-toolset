"""Unreal MCP toolset that exposes ue_asset_intake_toolset to AI agents.

Discovered by the Toolset Registry at editor startup (this file lives in the plugin's
Content/Python). Every tool forwards to ``ue_asset_intake_toolset.mcp`` with the real ``unreal``
module and returns a JSON string whose first key is ``summary``. Mutating tools default to
``dry_run=True`` and run inside an editor transaction (Ctrl+Z undoes them). Nothing is deleted.
"""

import toolset_registry
import unreal

from ue_asset_intake_toolset import mcp


@unreal.uclass()
class AssetIntakeTools(unreal.ToolsetDefinition):
    """Import, normalize and validate 3D assets and textures, and keep a provenance log.

    Use it to bring AI-generated or external meshes into /Game with safe names, Nanite by triangle
    count, simple collision, a material instance and capped texture sizes, then validate a folder
    and export where every asset came from (generated, in_engine or sourced) for license compliance.
    """

    @staticmethod
    @toolset_registry.tool_call
    def import_static_mesh(
        source_path: str,
        dest_folder: str = "/Game/Imported",
        asset_name: str = "",
        nanite: str = "auto",
        nanite_threshold: int = 20000,
        collision: bool = True,
        material_instance: str = "",
        max_texture_size: int = 2048,
        provenance_json: str = "",
        dry_run: bool = True,
    ) -> str:
        """Import one mesh file (FBX, GLB, OBJ) and normalize it.

        Args:
            source_path: Absolute path of the file on disk.
            dest_folder: Content folder under /Game where the asset is created.
            asset_name: Desired name; a safe SM_ name is derived if empty or invalid.
            nanite: "auto" (by triangle count), "on" or "off".
            nanite_threshold: Triangle count from which "auto" enables Nanite.
            collision: Add simple box collision when the mesh has none.
            material_instance: Optional /Game path of a material instance for slot 0.
            max_texture_size: Cap for imported textures (power of two; 0 keeps them as is).
            provenance_json: Optional JSON object with origin, tool, plan, prompt_ref, license,
                source_url and created_at (ISO 8601).
            dry_run: When true (default) nothing is changed; the result describes the plan.

        Returns:
            JSON with summary, asset_path and dry_run.
        """
        return mcp.import_static_mesh(
            unreal,
            source_path,
            dest_folder,
            asset_name,
            nanite,
            nanite_threshold,
            collision,
            material_instance,
            max_texture_size,
            provenance_json,
            dry_run,
        )

    @staticmethod
    @toolset_registry.tool_call
    def import_batch(
        manifest_json: str,
        batch_limit: int = 5,
        cursor: int = 0,
        nanite: str = "auto",
        collision: bool = True,
        material_instance: str = "",
        max_texture_size: int = 2048,
        dry_run: bool = True,
    ) -> str:
        """Import up to batch_limit entries of a manifest, starting at cursor.

        Args:
            manifest_json: JSON list (or {"entries": [...]}) of objects with source_path and
                optional asset_type, name, dest_path and provenance.
            batch_limit: Maximum entries processed in this call (keeps each call short).
            cursor: Index of the first entry to process; pass the returned cursor to continue.
            nanite: "auto", "on" or "off" for every mesh in this slice.
            collision: Add simple box collision to meshes without collision.
            material_instance: Optional /Game path of a material instance for slot 0.
            max_texture_size: Cap for imported textures (power of two; 0 keeps them as is).
            dry_run: When true (default) nothing is changed.

        Returns:
            JSON with summary, results and cursor (null when the manifest is finished).
        """
        return mcp.import_batch(
            unreal,
            manifest_json,
            batch_limit,
            cursor,
            nanite,
            collision,
            material_instance,
            max_texture_size,
            dry_run,
        )

    @staticmethod
    @toolset_registry.tool_call
    def validate_assets(
        folder: str,
        reference_height_cm: float = 180.0,
        tolerance: float = 10.0,
        nanite_threshold: int = 20000,
        max_texture_size: int = 4096,
    ) -> str:
        """Check naming, scale, collision, Nanite and texture sizes under a folder (read-only).

        Args:
            folder: Content folder under /Game, searched recursively.
            reference_height_cm: Expected height of a typical asset, used to flag bad scale.
            tolerance: Allowed ratio before a height is reported as a scale anomaly.
            nanite_threshold: Triangle count from which Nanite is expected.
            max_texture_size: Textures larger than this are reported.

        Returns:
            JSON with summary and violations (path, code, message).
        """
        return mcp.validate_assets(
            unreal, folder, reference_height_cm, tolerance, nanite_threshold, max_texture_size
        )

    @staticmethod
    @toolset_registry.tool_call
    def fix_assets(fixes_json: str, dry_run: bool = True) -> str:
        """Apply non-destructive fixes reported by validate_assets.

        Args:
            fixes_json: JSON list of objects with "fix" (rename_with_redirector,
                set_texture_max_size, set_lod_group, add_simple_collision, toggle_nanite),
                "asset" and the fix parameter (new_name, size, group or enabled).
            dry_run: When true (default) nothing is changed.

        Returns:
            JSON with summary, applied and dry_run.
        """
        return mcp.fix_assets(unreal, fixes_json, dry_run)

    @staticmethod
    @toolset_registry.tool_call
    def write_provenance(asset_path: str, provenance_json: str, dry_run: bool = True) -> str:
        """Record where an asset came from as metadata tags on the asset.

        Args:
            asset_path: /Game path of the asset.
            provenance_json: JSON object with origin (generated, in_engine or sourced), tool,
                plan, prompt_ref, license, source_url and created_at (ISO 8601).
            dry_run: When true (default) nothing is changed.

        Returns:
            JSON with summary, asset_path and dry_run.
        """
        return mcp.write_provenance(unreal, asset_path, provenance_json, dry_run)

    @staticmethod
    @toolset_registry.tool_call
    def export_provenance_log(folder: str, fmt: str = "md") -> str:
        """Render the provenance of every tagged asset under a folder (read-only).

        Args:
            folder: Content folder under /Game.
            fmt: "md", "csv" or "json".

        Returns:
            JSON with summary, content, count and fmt.
        """
        return mcp.export_provenance_log(unreal, folder, fmt)

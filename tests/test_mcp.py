"""The MCP layer: JSON in, JSON out, errors as data, normalization after import."""

from __future__ import annotations

import json

import pytest

from tests.fakes.unreal import FakeUnreal, FakeUnreal58, Tripwire
from ue_asset_intake_toolset import mcp
from ue_asset_intake_toolset.compat import box_collision_shape, static_mesh_api

PROV = json.dumps(
    {
        "origin": "generated",
        "tool": "Meshy",
        "plan": "Pro",
        "prompt_ref": "p-1",
        "license": "commercial",
        "source_url": "",
        "created_at": "2026-11-12T10:00:00Z",
    }
)


def _load(raw: str) -> dict:
    data = json.loads(raw)
    assert next(iter(data)) == "summary"
    return data


def test_dry_run_touches_nothing_mutating() -> None:
    ue = FakeUnreal()
    data = _load(mcp.import_static_mesh(ue, "C:/gen/rock.fbx", "/Game/Props"))
    assert data["dry_run"] is True
    assert ue.mutating_calls == []


def test_real_import_normalizes_mesh_and_textures() -> None:
    ue = FakeUnreal()
    ue.add_asset("/Game/Materials/MI_Toon", class_name="MaterialInstanceConstant")
    ue.import_spec = {"triangles": 50000}
    ue.import_textures = ["T_Rock_D"]
    data = _load(
        mcp.import_static_mesh(
            ue,
            "C:/gen/rock.fbx",
            "/Game/Props",
            material_instance="/Game/Materials/MI_Toon",
            max_texture_size=1024,
            provenance_json=PROV,
            dry_run=False,
        )
    )
    path = data["asset_path"]
    mesh = ue.assets[path]
    assert mesh.nanite is True and mesh.collisions == 1
    assert mesh.props["material_0"] == "/Game/Materials/MI_Toon"
    assert ue.assets["/Game/Props/T_Rock_D"].props["max_texture_size"] == 1024
    assert mesh.tags["provenance.tool"] == "Meshy"
    assert "nanite=on" in data["summary"]


@pytest.mark.parametrize(("triangles", "expected"), [(100, False), (20000, True)])
def test_nanite_auto_uses_threshold(triangles: int, expected: bool) -> None:
    ue = FakeUnreal()
    ue.import_spec = {"triangles": triangles}
    data = _load(mcp.import_static_mesh(ue, "C:/a.fbx", "/Game/P", dry_run=False))
    assert ue.assets[data["asset_path"]].nanite is expected


def test_nanite_forced_and_no_collision() -> None:
    ue = FakeUnreal()
    ue.import_spec = {"triangles": 10}
    data = _load(
        mcp.import_static_mesh(
            ue, "C:/a.fbx", "/Game/P", nanite="on", collision=False, dry_run=False
        )
    )
    mesh = ue.assets[data["asset_path"]]
    assert mesh.nanite is True and mesh.collisions == 0


def test_works_with_ue58_subsystem() -> None:
    ue = FakeUnreal58()
    ue.import_spec = {"triangles": 30000}
    data = _load(mcp.import_static_mesh(ue, "C:/a.fbx", "/Game/P", dry_run=False))
    mesh = ue.assets[data["asset_path"]]
    assert mesh.nanite is True
    assert ("EditorStaticMeshLibrary.add_simple_collisions", (mesh.path, "BOX58"), True) in ue.calls
    assert static_mesh_api(ue) is ue.subsystem
    assert box_collision_shape(ue) == "BOX58"


def test_compat_errors_without_enum() -> None:
    with pytest.raises(AttributeError):
        box_collision_shape(Tripwire.__new__(type("X", (), {})))


def test_compat_subsystem_missing_falls_back() -> None:
    ue = FakeUnreal58()
    ue.get_editor_subsystem = lambda cls: None  # type: ignore[method-assign]
    ue.EditorStaticMeshLibrary = "legacy"  # type: ignore[attr-defined]
    assert static_mesh_api(ue) == "legacy"


@pytest.mark.parametrize(
    ("kwargs", "code"),
    [
        ({"nanite": "maybe"}, "invalid_manifest"),
        ({"max_texture_size": 1000}, "invalid_manifest"),
        ({"nanite_threshold": -1}, "invalid_manifest"),
        ({"provenance_json": "{bad"}, "invalid_manifest"),
        ({"dest_folder": "/Engine/X"}, "path_not_allowed"),
    ],
)
def test_errors_come_back_as_data(kwargs: dict, code: str) -> None:
    data = _load(mcp.import_static_mesh(FakeUnreal(), "C:/a.fbx", **kwargs))
    assert data["error"]["code"] == code
    assert data["summary"].startswith("error:")


def test_missing_material_is_reported() -> None:
    ue = FakeUnreal()
    data = _load(
        mcp.import_static_mesh(
            ue, "C:/a.fbx", "/Game/P", material_instance="/Game/M/MI_X", dry_run=False
        )
    )
    assert data["error"]["code"] == "invalid_manifest"


def test_unexpected_unreal_failure_is_reported() -> None:
    class Broken(FakeUnreal):
        def AssetImportTask(self):
            raise AttributeError("no AssetImportTask")

    data = _load(mcp.import_static_mesh(Broken(), "C:/a.fbx", "/Game/P", dry_run=False))
    assert data["error"]["code"] == "unreal_error"


def test_batch_validate_fix_provenance_roundtrip() -> None:
    ue = FakeUnreal()
    ue.import_spec = {"triangles": 10, "height": 180.0}
    manifest = json.dumps(
        [{"source_path": "C:/a.fbx", "dest_path": "/Game/B", "provenance": json.loads(PROV)}]
    )
    batch = _load(mcp.import_batch(ue, manifest, dry_run=False))
    assert batch["cursor"] is None and len(batch["results"]) == 1
    report = _load(mcp.validate_assets(ue, "/Game/B"))
    assert "violations" in report
    fixes = json.dumps(
        [{"fix": "toggle_nanite", "asset": batch["results"][0]["asset_path"], "enabled": True}]
    )
    fixed = _load(mcp.fix_assets(ue, fixes, dry_run=False))
    assert fixed["dry_run"] is False
    log = _load(mcp.export_provenance_log(ue, "/Game/B", "json"))
    assert log["count"] == 1
    wrote = _load(mcp.write_provenance(ue, batch["results"][0]["asset_path"], PROV))
    assert wrote["dry_run"] is True


def test_write_provenance_requires_payload() -> None:
    data = _load(mcp.write_provenance(FakeUnreal(), "/Game/A", ""))
    assert data["error"]["code"] == "invalid_manifest"


def test_parse_json_rejects_huge_input() -> None:
    data = _load(mcp.fix_assets(FakeUnreal(), "x" * (mcp.MAX_JSON_CHARS + 1)))
    assert data["error"]["code"] == "invalid_manifest"


def test_to_json_handles_plain_values() -> None:
    assert json.loads(mcp.to_json({"a": (1, 2), "summary": "s", "p": object.__new__(object)}))[
        "a"
    ] == [1, 2]
    assert json.loads(mcp.to_json([1, None]))[1] is None

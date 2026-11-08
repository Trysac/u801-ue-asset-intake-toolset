import json
from pathlib import Path
from typing import Any

import pytest
from fakes.unreal import FakeUnreal, Tripwire

from ue_asset_intake_toolset import (
    IntakeError,
    Provenance,
    export_provenance_log,
    fix_assets,
    import_batch,
    import_static_mesh,
    validate_assets,
    write_provenance,
)

HERE = Path(__file__).parent
PROV = Provenance("generated", "meshgen", "free", "p-001", "CC0-1.0", "", "2025-01-02T03:04:05Z")


def test_import_dry_run() -> None:
    ue = FakeUnreal()
    result = import_static_mesh(ue, "C:\\src\\my cool mesh!.fbx", "/Game/Props")
    assert result.summary.startswith("dry run")
    assert ue.mutating_calls == []
    assert result.asset_path == "/Game/Props/SM_MyCoolMesh"


def test_import_real_with_conflict_and_provenance() -> None:
    ue = FakeUnreal()
    ue.add_asset("/Game/Props/SM_MyCoolMesh")
    result = import_static_mesh(
        ue, "my cool mesh!.fbx", "/Game/Props", provenance=PROV, dry_run=False
    )
    assert result.asset_path == "/Game/Props/SM_MyCoolMesh_01"
    assert result.summary.startswith("imported")
    assert ue.assets[result.asset_path].tags["provenance.origin"] == "generated"
    assert ue.calls[-1][0] == "EditorAssetLibrary.set_metadata_tag" or ue.mutating_calls


def _entries(n: int) -> list[dict[str, Any]]:
    return [{"source_path": f"C:/src/m{i}.fbx", "dest_path": "/Game/B"} for i in range(n)]


def test_import_batch_cursor() -> None:
    ue = FakeUnreal()
    first = import_batch(ue, _entries(7), batch_limit=5, dry_run=False)
    assert len(first.results) == 5 and first.cursor == 5
    second = import_batch(ue, _entries(7), batch_limit=5, cursor=first.cursor, dry_run=False)
    assert len(second.results) == 2 and second.cursor is None
    assert len(ue.assets) == 7
    dry = import_batch(ue, _entries(2), dry_run=True)
    assert dry.summary.startswith("dry run") and dry.cursor is None


def test_import_batch_errors() -> None:
    ue = FakeUnreal()
    for kwargs in ({"batch_limit": 0}, {"batch_limit": "5"}, {"cursor": 9}, {"cursor": -1}):
        with pytest.raises(IntakeError) as err:
            import_batch(ue, _entries(3), **kwargs)
        assert err.value.code == "invalid_manifest"
    assert ue.calls == []


def test_path_outside_game_calls_nothing() -> None:
    trip: Any = Tripwire()
    calls = [
        lambda: import_static_mesh(trip, "a.fbx", "/Engine/x"),
        lambda: import_static_mesh(trip, "a.fbx", "/Game/../Engine"),
        lambda: import_batch(trip, [{"source_path": "a", "dest_path": "/Temp"}]),
        lambda: validate_assets(trip, "/Engine"),
        lambda: fix_assets(trip, [{"fix": "add_simple_collision", "asset": "/Engine/X"}]),
        lambda: write_provenance(trip, "/Engine/X", PROV),
        lambda: export_provenance_log(trip, "/Engine", "md"),
    ]
    for call in calls:
        with pytest.raises(IntakeError) as err:
            call()
        assert err.value.code == "path_not_allowed"
    ue = FakeUnreal()
    with pytest.raises(IntakeError):
        import_static_mesh(ue, "a.fbx", "/Engine/x")
    assert ue.calls == []


def test_write_provenance() -> None:
    ue = FakeUnreal()
    ue.add_asset("/Game/P/SM_A")
    dry = write_provenance(ue, "/Game/P/SM_A", PROV)
    assert dry.summary.startswith("dry run") and ue.calls == []
    done = write_provenance(ue, "/Game/P/SM_A", PROV, dry_run=False)
    assert done.summary.startswith("wrote")
    assert ue.assets["/Game/P/SM_A"].tags["provenance.license"] == "CC0-1.0"
    with pytest.raises(IntakeError):
        write_provenance(ue, "/Game/P/SM_Missing", PROV, dry_run=False)


@pytest.mark.parametrize("fmt", ["md", "csv", "json"])
def test_export_matches_golden(fmt: str) -> None:
    ue = FakeUnreal()
    data = json.loads((HERE / "fixtures" / "provenance" / "assets.json").read_text("utf-8"))
    for path, tags in data.items():
        ue.add_asset(path, tags=tags)
    result = export_provenance_log(ue, "/Game/Fixture", fmt)
    golden = (HERE / "golden" / f"provenance.{fmt}").read_text("utf-8")
    assert result.content == golden
    assert result.count == 2 and ue.mutating_calls == []


def test_export_bad_format_and_missing() -> None:
    ue = FakeUnreal()
    with pytest.raises(IntakeError):
        export_provenance_log(ue, "/Game/Fixture", "xml")
    assert ue.calls == []


def test_validate_assets_adapter() -> None:
    ue = FakeUnreal()
    ue.add_asset("/Game/A/SM_Good", triangles=60000, height=180.0, collisions=1, nanite=True)
    ue.add_asset("/Game/A/bad", triangles=10, height=18000.0)
    ue.add_asset("/Game/A/T_Big", class_name="Texture2D", size=(8192, 8192))
    ue.add_asset("/Game/A/M_Skip", class_name="Material")
    first = validate_assets(ue, "/Game/A")
    assert first == validate_assets(ue, "/Game/A")
    codes = {(v.path, v.code) for v in first.violations}
    assert ("/Game/A/bad", "scale_anomaly") in codes
    assert ("/Game/A/T_Big", "texture_too_large") in codes
    assert not [c for c in codes if c[0] == "/Game/A/SM_Good"]
    assert first.checked == 3 and ue.mutating_calls == []


def _ue_with_fix_assets() -> FakeUnreal:
    ue = FakeUnreal()
    ue.add_asset("/Game/T/SM_A")
    ue.add_asset("/Game/T/T_A", class_name="Texture2D")
    ue.add_asset("/Game/T/SM_Taken")
    return ue


FIXES = [
    {"fix": "rename_with_redirector", "asset": "/Game/T/SM_A", "new_name": "SM_B"},
    {"fix": "set_texture_max_size", "asset": "/Game/T/T_A", "size": 1024},
    {"fix": "set_lod_group", "asset": "/Game/T/SM_Taken", "group": "LevelArchitecture"},
    {"fix": "add_simple_collision", "asset": "/Game/T/SM_Taken"},
    {"fix": "toggle_nanite", "asset": "/Game/T/SM_Taken", "enabled": True},
]


def test_fix_assets_dry_run_and_apply() -> None:
    ue = _ue_with_fix_assets()
    dry = fix_assets(ue, FIXES)
    assert dry.summary.startswith("dry run") and len(dry.applied) == 5
    assert ue.mutating_calls == []
    done = fix_assets(ue, FIXES, dry_run=False)
    assert done.summary == "applied 5 fixes"
    assert "/Game/T/SM_B" in ue.assets and "/Game/T/SM_A" not in ue.assets
    assert ue.assets["/Game/T/T_A"].props["max_texture_size"] == 1024
    taken = ue.assets["/Game/T/SM_Taken"]
    assert taken.props["lod_group"] == "LevelArchitecture"
    assert taken.collisions == 1 and taken.nanite is True


def test_fix_assets_errors() -> None:
    ue = _ue_with_fix_assets()
    with pytest.raises(IntakeError) as err:
        fix_assets(ue, [{"fix": "delete_asset", "asset": "/Game/T/SM_A"}])
    assert err.value.code == "unknown_fix"
    with pytest.raises(IntakeError) as err:
        fix_assets(
            ue, [{"fix": "rename_with_redirector", "asset": "/Game/T/SM_A", "new_name": "SM_Taken"}]
        )
    assert err.value.code == "name_conflict"
    bad: list[Any] = [
        "notadict",
        {"fix": "rename_with_redirector", "asset": "/Game/T/SM_A", "new_name": "bad name!"},
        {"fix": "set_texture_max_size", "asset": "/Game/T/T_A", "size": 1000},
        {"fix": "set_texture_max_size", "asset": "/Game/T/T_A", "size": True},
        {"fix": "set_lod_group", "asset": "/Game/T/SM_A", "group": ""},
        {"fix": "toggle_nanite", "asset": "/Game/T/SM_A", "enabled": "yes"},
    ]
    for item in bad:
        with pytest.raises(IntakeError) as err:
            fix_assets(ue, [item])
        assert err.value.code == "invalid_manifest"
    with pytest.raises(IntakeError):
        fix_assets(ue, "nope")  # type: ignore[arg-type]
    with pytest.raises(IntakeError):
        fix_assets(
            ue, [{"fix": "set_lod_group", "asset": "/Game/T/Missing", "group": "G"}], dry_run=False
        )
    assert ue.mutating_calls[-1][0] == "ScopedEditorTransaction"

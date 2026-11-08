import json

import pytest

from ue_asset_intake_toolset import (
    AssetInfo,
    IntakeError,
    Provenance,
    decide_nanite,
    safe_asset_name,
    validate_manifest,
)
from ue_asset_intake_toolset.core.paths import normalize_game_path, normalize_source_path
from ue_asset_intake_toolset.core.provenance import render_provenance
from ue_asset_intake_toolset.core.validation import validate_assets

PROV = Provenance("generated", "meshgen", "free", "p-001", "CC0-1.0", "", "2025-01-02T03:04:05Z")


def test_safe_asset_name_acceptance() -> None:
    assert safe_asset_name("my cool mesh!.fbx", "StaticMesh", existing=set()) == "SM_MyCoolMesh"


def test_safe_asset_name_suffixes() -> None:
    assert safe_asset_name("foo", "StaticMesh", {"SM_Foo"}) == "SM_Foo_01"
    assert safe_asset_name("foo", "StaticMesh", {"SM_Foo", "SM_Foo_01"}) == "SM_Foo_02"
    assert safe_asset_name("foo", "StaticMesh", {"sm_foo"}) == "SM_Foo_01"


def test_safe_asset_name_misc() -> None:
    assert safe_asset_name("SM_rock", "StaticMesh", set()) == "SM_Rock"
    assert safe_asset_name("C:\\a\\moss tex.png", "Texture", set()) == "T_MossTex"
    assert safe_asset_name("!!!", "Material", set()) == "M_Asset"
    assert safe_asset_name("x", "MaterialInstance", set()) == "MI_X"
    long = safe_asset_name("a" * 500, "SkeletalMesh", {"SK_" + "A" * 61})
    assert len(long) == 64 and long.endswith("_01")


def test_safe_asset_name_errors() -> None:
    for args in (("x", "Nope", set()), ("x" * 2000, "Texture", set())):
        with pytest.raises(IntakeError) as err:
            safe_asset_name(*args)
        assert err.value.code == "invalid_manifest"
    with pytest.raises(IntakeError):
        safe_asset_name("x", "Texture", set(), max_length=3)


def test_decide_nanite() -> None:
    assert decide_nanite(triangles=60000, is_static=True, threshold=20000) is True
    assert decide_nanite(triangles=60000, is_static=False, threshold=20000) is False
    assert decide_nanite(100, True) is False
    with pytest.raises(IntakeError):
        decide_nanite(-1, True)


def test_manifest_missing_source_path() -> None:
    with pytest.raises(IntakeError) as err:
        validate_manifest([{"source_path": "a.fbx"}, {"name": "x"}])
    assert err.value.code == "invalid_manifest"
    assert "entry 1" in str(err.value)


def test_manifest_valid_and_invalid() -> None:
    ok = validate_manifest(
        {"entries": [{"source_path": "a.fbx", "provenance": PROV.to_dict(), "name": "n"}]}
    )
    assert ok[0].provenance == PROV and ok[0].dest_path == "/Game/Imported"
    bad: list[object] = [
        "text",
        {"entries": 3},
        [3],
        [{"source_path": "a", "extra": 1}],
        [{"source_path": "  "}],
        [{"source_path": "a", "asset_type": "Nope"}],
        [{"source_path": "a", "name": 3}],
        [{"source_path": "a", "dest_path": 3}],
        [{"source_path": "a", "provenance": {"origin": "x", "created_at": "2025-01-01"}}],
        [{"source_path": "a"}] * 1001,
    ]
    for data in bad:
        with pytest.raises(IntakeError) as err:
            validate_manifest(data)
        assert err.value.code == "invalid_manifest"


def test_validate_assets_idempotent_and_scale() -> None:
    assets = [
        AssetInfo("/Game/A/SM_Tall", "StaticMesh", 100, 18000.0, has_collision=True),
        AssetInfo("/Game/A/bad name", "StaticMesh", 60000, 180.0),
        AssetInfo("/Game/A/T_Big", "Texture", texture_size=(8192, 100)),
    ]
    first = validate_assets(assets, reference_height_cm=180.0, tolerance=10.0)
    second = validate_assets(assets, reference_height_cm=180.0, tolerance=10.0)
    assert first == second and first.violations == second.violations
    pairs = {(v.path, v.code) for v in first.violations}
    assert ("/Game/A/SM_Tall", "scale_anomaly") in pairs
    assert ("/Game/A/bad name", "bad_name") in pairs
    assert ("/Game/A/bad name", "missing_collision") in pairs
    assert ("/Game/A/bad name", "nanite_mismatch") in pairs
    assert ("/Game/A/T_Big", "texture_too_large") in pairs
    assert ("/Game/A/T_Big", "texture_not_pow2") in pairs


def test_validate_assets_small_unknown_and_errors() -> None:
    report = validate_assets(
        [
            AssetInfo("/Game/A/SM_Tiny", "StaticMesh", 5, 1.0, has_collision=True),
            AssetInfo("/Game/A/X_Thing", "Weird"),
            AssetInfo("/Game/A/M_Ok", "Material"),
        ]
    )
    codes = {(v.path, v.code) for v in report.violations}
    assert ("/Game/A/SM_Tiny", "scale_anomaly") in codes
    assert ("/Game/A/X_Thing", "unknown_asset_type") in codes
    assert report.summary.startswith("3 assets checked")
    for kwargs in ({"reference_height_cm": 0}, {"tolerance": 1}, {"max_texture_size": 0}):
        with pytest.raises(IntakeError):
            validate_assets([], **kwargs)  # type: ignore[arg-type]
    with pytest.raises(IntakeError):
        validate_assets([AssetInfo("/Game/A", "Material")] * 10001)


def test_paths() -> None:
    assert normalize_game_path("\\Game\\\\Props/") == "/Game/Props"
    assert normalize_game_path("/Game") == "/Game"
    for bad in ("/Engine/X", "/Gamex", "/Game/../Engine", "/Game/./x", "/Game/a\x00", "", 5):
        with pytest.raises(IntakeError) as err:
            normalize_game_path(bad)
        assert err.value.code == "path_not_allowed"
    with pytest.raises(IntakeError):
        normalize_game_path("/Game/" + "a" * 600)
    assert normalize_source_path("C:\\x\\a.fbx") == "C:/x/a.fbx"
    for bad2 in ("  ", 5, "a\nb"):
        with pytest.raises(IntakeError) as err2:
            normalize_source_path(bad2)
        assert err2.value.code == "invalid_manifest"


def test_provenance_errors_and_render() -> None:
    with pytest.raises(IntakeError):
        Provenance("magic", "", "", "", "", "", "2025-01-01T00:00:00Z")
    with pytest.raises(IntakeError):
        Provenance("sourced", "", "", "", "", "", "yesterday")
    for data in (5, {"origin": "sourced", "created_at": "2025-01-01", "zzz": "1"}):
        with pytest.raises(IntakeError):
            Provenance.from_dict(data)
    with pytest.raises(IntakeError):
        Provenance.from_dict({"origin": "sourced", "created_at": 5})
    with pytest.raises(IntakeError):
        Provenance.from_dict({"origin": "sourced", "created_at": "2025-01-01", "tool": "x" * 3000})
    with pytest.raises(IntakeError):
        render_provenance([], "xml")
    assert json.loads(render_provenance([], "json")) == []
    tricky = Provenance("sourced", "=cmd", "a|b", "l1\nl2", "", "", "2025-01-01")
    assert "'=cmd" in render_provenance([("/Game/X", tricky)], "csv")
    md = render_provenance([("/Game/X", tricky)], "md")
    assert "a\\|b" in md and "l1 l2" in md
    with pytest.raises(IntakeError):
        render_provenance([("/Game/X", PROV)] * 10001, "md")

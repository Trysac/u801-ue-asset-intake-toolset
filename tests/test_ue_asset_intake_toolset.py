import ue_asset_intake_toolset as pkg


def test_version_and_exports() -> None:
    assert pkg.__version__ == "0.2.0"
    for name in pkg.__all__:
        assert hasattr(pkg, name)

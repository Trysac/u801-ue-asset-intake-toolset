"""Behavior tests for the public API of ue_asset_intake_toolset."""

from __future__ import annotations

import pytest

import ue_asset_intake_toolset


def test_normalize_trims_and_lowercases() -> None:
    assert ue_asset_intake_toolset.normalize("  Hello World ") == "hello world"


@pytest.mark.parametrize("value", ["", "   ", "\t\n"])
def test_normalize_rejects_blank_input(value: str) -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        ue_asset_intake_toolset.normalize(value)


def test_version_is_semver() -> None:
    parts = ue_asset_intake_toolset.__version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)

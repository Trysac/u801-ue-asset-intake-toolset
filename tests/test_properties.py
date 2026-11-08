import re

from hypothesis import given, settings
from hypothesis import strategies as st

from ue_asset_intake_toolset import AssetInfo, safe_asset_name
from ue_asset_intake_toolset.core.naming import PREFIXES
from ue_asset_intake_toolset.core.validation import validate_assets

CFG = settings(derandomize=True, max_examples=150, deadline=None)


@CFG
@given(
    name=st.text(max_size=200),
    kind=st.sampled_from(sorted(PREFIXES)),
    existing=st.sets(st.text(max_size=70), max_size=30),
)
def test_rename_never_collides_and_is_valid(name: str, kind: str, existing: set[str]) -> None:
    result = safe_asset_name(name, kind, existing)
    assert result.lower() not in {e.lower() for e in existing}
    assert re.fullmatch(r"[A-Za-z0-9_]{1,64}", result)
    assert result.startswith(PREFIXES[kind])


@CFG
@given(name=st.text(max_size=80), count=st.integers(1, 8))
def test_repeated_renames_are_distinct(name: str, count: int) -> None:
    taken: set[str] = set()
    for _ in range(count):
        taken.add(safe_asset_name(name, "StaticMesh", taken))
    assert len(taken) == count


asset_strategy = st.builds(
    AssetInfo,
    path=st.from_regex(r"/Game/[A-Za-z0-9_]{1,10}", fullmatch=True),
    asset_type=st.sampled_from([*PREFIXES, "Other"]),
    triangles=st.integers(0, 10**6),
    bounds_height_cm=st.floats(0, 1e6, allow_nan=False),
    texture_size=st.tuples(st.integers(0, 16384), st.integers(0, 16384)),
    has_collision=st.booleans(),
    nanite_enabled=st.booleans(),
)


@CFG
@given(assets=st.lists(asset_strategy, max_size=10))
def test_validation_idempotent_and_order_independent(assets: list[AssetInfo]) -> None:
    first = validate_assets(assets)
    assert first == validate_assets(assets)
    assert first == validate_assets(list(reversed(assets)))

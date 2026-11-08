"""Deterministic asset validation over plain descriptions."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from .errors import IntakeError
from .naming import PREFIXES
from .nanite import decide_nanite

MAX_ASSETS = 10000
_VALID = re.compile(r"[A-Za-z0-9_]{1,64}")


@dataclass(frozen=True)
class AssetInfo:
    """Plain description of an asset."""

    path: str
    asset_type: str
    triangles: int = 0
    bounds_height_cm: float = 0.0
    texture_size: tuple[int, int] = (0, 0)
    has_collision: bool = False
    nanite_enabled: bool = False


@dataclass(frozen=True)
class Violation:
    """One rule violation."""

    path: str
    code: str
    message: str


@dataclass(frozen=True)
class ValidationReport:
    """Result of a validation run."""

    summary: str
    checked: int
    violations: tuple[Violation, ...]


def _check(a: AssetInfo, ref: float, tol: float, thr: int, max_tex: int) -> list[Violation]:
    out: list[Violation] = []
    name = a.path.rsplit("/", 1)[-1]
    prefix = PREFIXES.get(a.asset_type)
    if not _VALID.fullmatch(name) or (prefix is not None and not name.startswith(prefix)):
        out.append(Violation(a.path, "bad_name", f"name {name[:64]!r} breaks naming rules"))
    if prefix is None:
        out.append(Violation(a.path, "unknown_asset_type", f"type {a.asset_type[:50]!r}"))
        return out
    if a.asset_type in ("StaticMesh", "SkeletalMesh") and a.bounds_height_cm > 0:
        h = a.bounds_height_cm
        if h > ref * tol or h < ref / tol:
            out.append(
                Violation(a.path, "scale_anomaly", f"height {h:g} cm vs reference {ref:g} cm")
            )
    if a.asset_type == "StaticMesh":
        if not a.has_collision:
            out.append(Violation(a.path, "missing_collision", "no simple collision"))
        if decide_nanite(a.triangles, True, thr) != a.nanite_enabled:
            out.append(Violation(a.path, "nanite_mismatch", f"{a.triangles} triangles"))
    if a.asset_type == "Texture":
        dims = [d for d in a.texture_size if d > 0]
        if any(d > max_tex for d in dims):
            out.append(Violation(a.path, "texture_too_large", f"limit {max_tex}"))
        if any(d & (d - 1) for d in dims):
            out.append(Violation(a.path, "texture_not_pow2", "size is not a power of two"))
    return out


def validate_assets(
    assets: Sequence[AssetInfo],
    *,
    reference_height_cm: float = 180.0,
    tolerance: float = 10.0,
    nanite_threshold: int = 20000,
    max_texture_size: int = 4096,
) -> ValidationReport:
    """Validate assets; the report is sorted and identical on every run."""
    if reference_height_cm <= 0 or tolerance <= 1 or max_texture_size < 1:
        raise IntakeError("invalid_manifest", "invalid validation parameters")
    if len(assets) > MAX_ASSETS:
        raise IntakeError("invalid_manifest", "too many assets to validate")
    found: list[Violation] = []
    for asset in assets:
        found.extend(
            _check(asset, reference_height_cm, tolerance, nanite_threshold, max_texture_size)
        )
    found.sort(key=lambda v: (v.path, v.code, v.message))
    return ValidationReport(
        f"{len(assets)} assets checked, {len(found)} violations", len(assets), tuple(found)
    )

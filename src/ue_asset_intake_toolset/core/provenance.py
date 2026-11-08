"""Provenance records and their md / csv / json rendering."""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, cast

from .errors import IntakeError

Origin = Literal["generated", "in_engine", "sourced"]
ORIGINS = ("generated", "in_engine", "sourced")
FIELDS = ("origin", "tool", "plan", "prompt_ref", "license", "source_url", "created_at")
MAX_FIELD_LENGTH = 2000
MAX_RECORDS = 10000
_COLUMNS = ("asset", *FIELDS)
_MD_HEAD = ("Asset", "Origin", "Tool", "Plan", "Prompt", "License", "Source", "Created")


@dataclass(frozen=True)
class Provenance:
    """Where an asset came from. ``created_at`` is an ISO 8601 string."""

    origin: Origin
    tool: str
    plan: str
    prompt_ref: str
    license: str
    source_url: str
    created_at: str

    def __post_init__(self) -> None:
        if self.origin not in ORIGINS:
            raise IntakeError("invalid_manifest", "provenance origin is not allowed")
        try:
            datetime.fromisoformat(self.created_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise IntakeError("invalid_manifest", "created_at must be ISO 8601") from exc

    def to_dict(self) -> dict[str, str]:
        """Return the seven fields as a dict."""
        return {f: str(getattr(self, f)) for f in FIELDS}

    @classmethod
    def from_dict(cls, data: Any) -> Provenance:
        """Build from a mapping; missing optional fields become empty strings."""
        if not isinstance(data, Mapping):
            raise IntakeError("invalid_manifest", "provenance must be an object")
        unknown = sorted(str(k)[:30] for k in data if k not in FIELDS)
        if unknown:
            raise IntakeError("invalid_manifest", f"unknown provenance keys: {unknown[:5]}")
        values: dict[str, str] = {}
        for field in FIELDS:
            value = data.get(field, "")
            if not isinstance(value, str) or len(value) > MAX_FIELD_LENGTH:
                raise IntakeError(
                    "invalid_manifest",
                    f"provenance field {field} must be a string up to 2000 chars",
                )
            values[field] = value
        return cls(
            origin=cast(Origin, values["origin"]),
            tool=values["tool"],
            plan=values["plan"],
            prompt_ref=values["prompt_ref"],
            license=values["license"],
            source_url=values["source_url"],
            created_at=values["created_at"],
        )


def _csv_safe(cell: str) -> str:
    return "'" + cell if cell and cell[0] in "=+-@\t\r" else cell


def _md_cell(cell: str) -> str:
    return cell.replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def render_provenance(records: Iterable[tuple[str, Provenance]], fmt: str) -> str:
    """Render ``(asset_path, Provenance)`` records, sorted by path, as md, csv or json."""
    if fmt not in ("md", "csv", "json"):
        raise IntakeError("invalid_manifest", "format must be md, csv or json")
    rows = sorted(records, key=lambda r: r[0])
    if len(rows) > MAX_RECORDS:
        raise IntakeError("invalid_manifest", "too many provenance records")
    if fmt == "json":
        data = [{"asset": a, **p.to_dict()} for a, p in rows]
        return json.dumps(data, indent=2, sort_keys=True) + "\n"
    if fmt == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf, lineterminator="\n")
        writer.writerow(_COLUMNS)
        for asset, prov in rows:
            writer.writerow([_csv_safe(c) for c in (asset, *prov.to_dict().values())])
        return buf.getvalue()
    lines = [
        "# Provenance log",
        "",
        "| " + " | ".join(_MD_HEAD) + " |",
        "|" + "---|" * len(_MD_HEAD),
    ]
    for asset, prov in rows:
        cells = [_md_cell(c) for c in (asset, *prov.to_dict().values())]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"

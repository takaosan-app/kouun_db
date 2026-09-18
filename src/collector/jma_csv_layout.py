from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ValueKind = Literal[
    "numeric",
    "direction",
    "text",
]


@dataclass(frozen=True, slots=True)
class ColumnSpec:
    element_key: str
    header_name: str
    value_kind: ValueKind
    value_index: int
    quality_index: int
    homogeneity_index: int
    phenomenon_index: int | None = None
    subheader_name: str | None = None


@dataclass(frozen=True, slots=True)
class CsvLayout:
    name: str
    column_count: int
    columns: tuple[ColumnSpec, ...]

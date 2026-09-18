from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

ValueState = Literal[
    "observed",
    "questionable",
    "missing",
    "not_observed",
]


@dataclass(frozen=True, slots=True)
class ObservationRecord:
    observed_on: date
    element_key: str
    raw_value: str
    value: Decimal | None
    value_state: ValueState
    quality_code: str
    homogeneity_number: str | None
    no_phenomenon: bool | None
    text_value: str | None = None


@dataclass(frozen=True, slots=True)
class ObservationParseIssue:
    issue_code: str
    observed_on: date
    element_key: str
    raw_value: str
    message: str


@dataclass(frozen=True, slots=True)
class ParsedJmaCsv:
    station_name: str
    observations: tuple[ObservationRecord, ...]
    source_dates: tuple[date, ...] = ()
    issues: tuple[ObservationParseIssue, ...] = ()


@dataclass(frozen=True, slots=True)
class SourceFileRecord:
    source_key: str
    storage_path: str
    sha256: str
    retrieved_at: datetime
    requested_start_date: date | None
    requested_end_date: date | None
    encoding: str
    content_type: str | None
    byte_size: int
    source_row_count: int
    collector_version: str
    request_parameters: dict[str, object]
    metadata: dict[str, object]


@dataclass(frozen=True, slots=True)
class ObsdlAreaPageSourceFileRecord(SourceFileRecord):
    area_count: int
    domestic_area_count: int


@dataclass(frozen=True, slots=True)
class ObsdlAreaRecord:
    area_code: str
    area_name: str


@dataclass(frozen=True, slots=True)
class ParsedObsdlAreaPage:
    areas: tuple[ObsdlAreaRecord, ...]


@dataclass(frozen=True, slots=True)
class ObservationSourceFileRecord(SourceFileRecord):
    station_key: str
    source_station_id: str


@dataclass(frozen=True, slots=True)
class AmedasMasterSourceFileRecord(SourceFileRecord):
    effective_on: date
    source_csv_name: str
    logical_station_count: int


@dataclass(frozen=True, slots=True)
class AreaObservationStation:
    source_station_id: str
    station_key: str
    station_name: str


@dataclass(frozen=True, slots=True)
class AreaObservationSourceFileRecord(
    SourceFileRecord
):
    area_code: str
    capability_code: str
    stations: tuple[
        AreaObservationStation,
        ...,
    ]
    observation_count: int


@dataclass(frozen=True, slots=True)
class ObsdlStationPageSourceFileRecord(SourceFileRecord):
    area_code: str
    active_count: int
    ended_count: int


@dataclass(frozen=True, slots=True)
class ObsdlStationRecord:
    source_station_id: str
    area_code: str
    name: str
    kana_name: str
    capability_code: str
    latitude: Decimal
    longitude: Decimal
    elevation_m: Decimal | None
    observation_ended_on: date | None
    raw_record: dict[str, str]


@dataclass(frozen=True, slots=True)
class ParsedObsdlStationPage:
    area_code: str
    stations: tuple[ObsdlStationRecord, ...]


@dataclass(frozen=True, slots=True)
class AmedasStationRecord:
    area_name: str
    official_station_number: str
    source_row_number: int
    station_type_code: str
    name: str
    kana_name: str | None
    information_name: str | None
    address: str
    latitude: Decimal
    longitude: Decimal
    elevation_m: Decimal | None
    wind_sensor_height_m: Decimal | None
    temperature_sensor_height_m: Decimal | None
    observation_start_raw: str
    remarks_1: str | None
    remarks_2: str | None
    raw_record: dict[str, str]


@dataclass(frozen=True, slots=True)
class ParsedAmedasMaster:
    effective_on: date
    source_csv_name: str
    stations: tuple[AmedasStationRecord, ...]

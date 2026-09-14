from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

from bs4 import BeautifulSoup, Tag

from collector.models import (
    ObsdlStationRecord,
    ParsedObsdlStationPage,
)

STATION_ID_PATTERN = re.compile(r"[as]\d{4,5}")
PREFECTURE_CODE_PATTERN = re.compile(r"\d{2}")
CAPABILITY_PATTERN = re.compile(r"[012]{6}")

NAME_PATTERN = re.compile(
    r"(?:^|\n)地点名[：:]\s*(.+?)(?:\n|$)"
)
KANA_PATTERN = re.compile(
    r"(?:^|\n)カナ[：:]\s*(.+?)(?:\n|$)"
)
LATITUDE_PATTERN = re.compile(
    r"北緯[：:]\s*(\d+)度(\d+(?:\.\d+)?)分"
)
LONGITUDE_PATTERN = re.compile(
    r"東経[：:]\s*(\d+)度(\d+(?:\.\d+)?)分"
)
ELEVATION_PATTERN = re.compile(
    r"標高[：:]\s*(-?\d+(?:\.\d+)?)m"
)
ENDED_ON_PATTERN = re.compile(
    r"(\d{4})年(\d{2})月(\d{2})日に観測終了"
)


class ObsdlStationParseError(ValueError):
    pass


def parse_obsdl_station_page(
    content: bytes,
    prefecture_code: str,
) -> ParsedObsdlStationPage:
    if not PREFECTURE_CODE_PATTERN.fullmatch(
        prefecture_code
    ):
        raise ObsdlStationParseError(
            "Prefecture code must contain two digits."
        )

    soup = BeautifulSoup(
        content,
        "html.parser",
        from_encoding="utf-8",
    )
    stations_by_id: dict[str, ObsdlStationRecord] = {}

    for node in soup.select("#stationMap div.station"):
        if not isinstance(node, Tag):
            continue

        record = _parse_station_node(
            node,
            prefecture_code,
        )
        existing = stations_by_id.get(
            record.source_station_id
        )

        if existing is not None and existing != record:
            raise ObsdlStationParseError(
                "Conflicting HTML entries for station "
                f"{record.source_station_id}"
            )

        stations_by_id[record.source_station_id] = record

    if not stations_by_id:
        raise ObsdlStationParseError(
            "No station entries were found."
        )

    return ParsedObsdlStationPage(
        prefecture_code=prefecture_code,
        stations=tuple(stations_by_id.values()),
    )


def _parse_station_node(
    node: Tag,
    prefecture_code: str,
) -> ObsdlStationRecord:
    values: dict[str, str] = {}

    for input_node in node.find_all(
        "input",
        recursive=False,
    ):
        name = input_node.get("name")
        value = input_node.get("value")

        if isinstance(name, str) and isinstance(value, str):
            values[name] = value.strip()

    source_station_id = _require_value(
        values,
        "stid",
    )
    name = _require_value(values, "stname")
    actual_prefecture_code = _require_value(
        values,
        "prid",
    )
    capability_code = _require_value(
        values,
        "kansoku",
    )

    if not STATION_ID_PATTERN.fullmatch(
        source_station_id
    ):
        raise ObsdlStationParseError(
            f"Invalid station ID: {source_station_id}"
        )

    if actual_prefecture_code != prefecture_code:
        raise ObsdlStationParseError(
            "Station prefecture code does not match request: "
            f"{actual_prefecture_code} != {prefecture_code}"
        )

    if not CAPABILITY_PATTERN.fullmatch(
        capability_code
    ):
        raise ObsdlStationParseError(
            "Invalid capability code for station "
            f"{source_station_id}: {capability_code}"
        )

    title = node.get("title")

    if not isinstance(title, str) or not title:
        raise ObsdlStationParseError(
            f"Station title is missing: {source_station_id}"
        )

    title_name = _extract_text(
        NAME_PATTERN,
        title,
        "station name",
    )

    if title_name != name:
        raise ObsdlStationParseError(
            "Station name does not match title: "
            f"{name!r} != {title_name!r}"
        )

    raw_record = {
        "title": title,
        **values,
    }

    return ObsdlStationRecord(
        source_station_id=source_station_id,
        prefecture_code=prefecture_code,
        name=name,
        kana_name=_extract_text(
            KANA_PATTERN,
            title,
            "kana name",
        ),
        capability_code=capability_code,
        latitude=_extract_coordinate(
            LATITUDE_PATTERN,
            title,
            "latitude",
        ),
        longitude=_extract_coordinate(
            LONGITUDE_PATTERN,
            title,
            "longitude",
        ),
        elevation_m=_extract_elevation(title),
        observation_ended_on=_extract_ended_on(title),
        raw_record=raw_record,
    )


def _require_value(
    values: dict[str, str],
    key: str,
) -> str:
    value = values.get(key)

    if value is None or not value:
        raise ObsdlStationParseError(
            f"Station field is missing: {key}"
        )

    return value


def _extract_text(
    pattern: re.Pattern[str],
    title: str,
    field: str,
) -> str:
    match = pattern.search(title)

    if match is None:
        raise ObsdlStationParseError(
            f"Station title has no {field}."
        )

    return match.group(1).strip()


def _extract_coordinate(
    pattern: re.Pattern[str],
    title: str,
    field: str,
) -> Decimal:
    match = pattern.search(title)

    if match is None:
        raise ObsdlStationParseError(
            f"Station title has no {field}."
        )

    degrees = Decimal(match.group(1))
    minutes = Decimal(match.group(2))

    return degrees + minutes / Decimal(60)


def _extract_elevation(
    title: str,
) -> Decimal | None:
    match = ELEVATION_PATTERN.search(title)

    if match is None:
        return None

    return Decimal(match.group(1))


def _extract_ended_on(
    title: str,
) -> date | None:
    match = ENDED_ON_PATTERN.search(title)

    if match is None:
        return None

    return date(
        int(match.group(1)),
        int(match.group(2)),
        int(match.group(3)),
    )

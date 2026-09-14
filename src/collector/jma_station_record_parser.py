from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from collector.models import AmedasStationRecord


EXPECTED_HEADERS = (
    "都府県振興局",
    "観測所番号",
    "種類",
    "観測所名",
    "ｶﾀｶﾅ名",
    "気象情報等に表記する名称",
    "所在地",
    "緯度(度)",
    "緯度(分)",
    "経度(度)",
    "経度(分)",
    "海面上の高さ(ｍ)",
    "風速計の高さ(ｍ)",
    "温度計の高さ(ｍ)",
    "観測開始年月日",
    "備考1",
    "備考2",
)

EMPTY_MARKERS = frozenset(("", "-", "－"))


class AmedasMasterError(ValueError):
    pass


def normalize_row(
    row: dict[str | None, str | list[str] | None],
    row_number: int,
) -> dict[str, str]:
    if None in row:
        raise AmedasMasterError(
            f"Row {row_number} contains extra columns."
        )

    normalized: dict[str, str] = {}

    for header in EXPECTED_HEADERS:
        value = row.get(header)

        if not isinstance(value, str):
            raise AmedasMasterError(
                f"Row {row_number} is missing {header!r}."
            )

        normalized[header] = value.strip()

    return normalized


def parse_station(
    row: dict[str, str],
    row_number: int,
) -> AmedasStationRecord:
    station_number = _required(
        row,
        "観測所番号",
        row_number,
    )

    if not re.fullmatch(r"\d{5}", station_number):
        raise AmedasMasterError(
            f"Invalid station number at row {row_number}: "
            f"{station_number!r}"
        )

    latitude = _parse_coordinate(
        row,
        degree_key="緯度(度)",
        minute_key="緯度(分)",
        maximum=Decimal("90"),
        row_number=row_number,
    )
    longitude = _parse_coordinate(
        row,
        degree_key="経度(度)",
        minute_key="経度(分)",
        maximum=Decimal("180"),
        row_number=row_number,
    )

    return AmedasStationRecord(
        area_name=_required(
            row,
            "都府県振興局",
            row_number,
        ),
        official_station_number=station_number,
        source_row_number=row_number,
        station_type_code=_required(
            row,
            "種類",
            row_number,
        ),
        name=_required(row, "観測所名", row_number),
        kana_name=_optional(row["ｶﾀｶﾅ名"]),
        information_name=_optional(
            row["気象情報等に表記する名称"]
        ),
        address=_required(row, "所在地", row_number),
        latitude=latitude,
        longitude=longitude,
        elevation_m=_optional_decimal(
            row["海面上の高さ(ｍ)"],
            "海面上の高さ",
            row_number,
        ),
        wind_sensor_height_m=_optional_decimal(
            row["風速計の高さ(ｍ)"],
            "風速計の高さ",
            row_number,
        ),
        temperature_sensor_height_m=_optional_decimal(
            row["温度計の高さ(ｍ)"],
            "温度計の高さ",
            row_number,
        ),
        observation_start_raw=_required(
            row,
            "観測開始年月日",
            row_number,
        ),
        remarks_1=_optional(row["備考1"]),
        remarks_2=_optional(row["備考2"]),
        raw_record=row,
    )


def _parse_coordinate(
    row: dict[str, str],
    *,
    degree_key: str,
    minute_key: str,
    maximum: Decimal,
    row_number: int,
) -> Decimal:
    degrees = _decimal(
        _required(row, degree_key, row_number),
        degree_key,
        row_number,
    )
    minutes = _decimal(
        _required(row, minute_key, row_number),
        minute_key,
        row_number,
    )

    if minutes < 0 or minutes >= 60:
        raise AmedasMasterError(
            f"Invalid minutes at row {row_number}: "
            f"{minutes}"
        )

    result = degrees + minutes / Decimal("60")

    if result < -maximum or result > maximum:
        raise AmedasMasterError(
            f"Coordinate is out of range at row {row_number}."
        )

    return result


def _optional_decimal(
    value: str,
    field: str,
    row_number: int,
) -> Decimal | None:
    normalized = _optional(value)

    if normalized is None:
        return None

    return _decimal(normalized, field, row_number)


def _decimal(
    value: str,
    field: str,
    row_number: int,
) -> Decimal:
    try:
        return Decimal(value)
    except InvalidOperation as error:
        raise AmedasMasterError(
            f"Invalid {field} at row {row_number}: "
            f"{value!r}"
        ) from error


def _required(
    row: dict[str, str],
    key: str,
    row_number: int,
) -> str:
    value = row[key].strip()

    if value in EMPTY_MARKERS:
        raise AmedasMasterError(
            f"Required field {key!r} is empty "
            f"at row {row_number}."
        )

    return value


def _optional(value: str) -> str | None:
    normalized = value.strip()

    if normalized in EMPTY_MARKERS:
        return None

    return normalized

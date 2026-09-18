from __future__ import annotations

import csv
import io
import re
import zipfile
from collections.abc import Iterator
from decimal import Decimal, InvalidOperation

from collector.models import ClimateNormalSeriesRecord

CSV_PATH_PATTERN = re.compile(
    r"^daily/area[0-9]{2}/"
    r"nml_amd_d_([0-9]{5})\.csv$"
)

ELEMENT_SPECS: dict[str, tuple[str, Decimal]] = {
    "0500": (
        "daily_mean_temperature",
        Decimal("10"),
    ),
    "0600": (
        "daily_max_temperature",
        Decimal("10"),
    ),
    "0700": (
        "daily_min_temperature",
        Decimal("10"),
    ),
    "3500": (
        "daily_sunshine_duration",
        Decimal("10"),
    ),
    "4000": (
        "daily_precipitation",
        Decimal("10"),
    ),
    "6200": (
        "daily_max_snow_depth",
        Decimal("1"),
    ),
    "6300": (
        "daily_snowfall",
        Decimal("1"),
    ),
}


class ClimateNormalParseError(ValueError):
    pass


def parse_daily_values(
    row: list[str],
    *,
    filename: str,
    row_number: int,
    divisor: Decimal,
) -> tuple[
    tuple[Decimal | None, ...],
    tuple[int, ...],
]:
    values: list[Decimal | None] = []
    remarks: list[int] = []

    for day_index in range(31):
        value_text = row[7 + day_index * 2].strip()
        remark_text = row[8 + day_index * 2].strip()

        try:
            remark = int(remark_text)
        except ValueError as error:
            raise ClimateNormalParseError(
                f"Invalid remark in {filename}, "
                f"row {row_number}, day {day_index + 1}."
            ) from error

        if remark not in (0, 8):
            raise ClimateNormalParseError(
                f"Unsupported remark {remark} in "
                f"{filename}, row {row_number}, "
                f"day {day_index + 1}."
            )

        if remark == 0:
            value = None
        else:
            try:
                value = Decimal(value_text) / divisor
            except InvalidOperation as error:
                raise ClimateNormalParseError(
                    f"Invalid value in {filename}, "
                    f"row {row_number}, "
                    f"day {day_index + 1}."
                ) from error

        values.append(value)
        remarks.append(remark)

    return tuple(values), tuple(remarks)


def iter_climate_normal_series(
    content: bytes,
) -> Iterator[ClimateNormalSeriesRecord]:
    series_count = 0

    try:
        archive = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile as error:
        raise ClimateNormalParseError(
            "Climate-normal source is not a valid ZIP."
        ) from error

    with archive:
        for member in archive.infolist():
            match = CSV_PATH_PATTERN.fullmatch(
                member.filename
            )
            if match is None:
                continue

            source_station_id = match.group(1)

            with archive.open(member) as binary_file:
                text_file = io.TextIOWrapper(
                    binary_file,
                    encoding="ascii",
                    newline="",
                )
                reader = csv.reader(text_file)

                for row_number, row in enumerate(
                    reader,
                    start=1,
                ):
                    if len(row) != 69:
                        raise ClimateNormalParseError(
                            f"Expected 69 fields in "
                            f"{member.filename}, row "
                            f"{row_number}; got {len(row)}."
                        )

                    normal_kind = row[0].strip()
                    row_station_id = row[1].strip()
                    source_element_code = row[2].strip()

                    if normal_kind != "25":
                        raise ClimateNormalParseError(
                            f"Unexpected normal kind in "
                            f"{member.filename}, row "
                            f"{row_number}: {normal_kind}"
                        )

                    if row_station_id != source_station_id:
                        raise ClimateNormalParseError(
                            f"Station number mismatch in "
                            f"{member.filename}, row "
                            f"{row_number}."
                        )

                    element_spec = ELEMENT_SPECS.get(
                        source_element_code
                    )
                    if element_spec is None:
                        continue

                    element_key, divisor = element_spec

                    try:
                        material_years = int(
                            row[3].strip()
                        )
                        statistics_started_year = int(
                            row[4].strip()
                        )
                        statistics_ended_year = int(
                            row[5].strip()
                        )
                        month = int(row[6].strip())
                    except ValueError as error:
                        raise ClimateNormalParseError(
                            f"Invalid record metadata in "
                            f"{member.filename}, row "
                            f"{row_number}."
                        ) from error

                    if not 0 <= material_years <= 30:
                        raise ClimateNormalParseError(
                            f"Invalid material years in "
                            f"{member.filename}, row "
                            f"{row_number}."
                        )

                    if material_years == 0:
                        if (
                            statistics_started_year != 0
                            or statistics_ended_year != 0
                        ):
                            raise ClimateNormalParseError(
                                f"Invalid empty statistics "
                                f"period in {member.filename}, "
                                f"row {row_number}."
                            )

                        started_year = None
                        ended_year = None
                    else:
                        if not (
                            1991
                            <= statistics_started_year
                            <= statistics_ended_year
                            <= 2020
                        ):
                            raise ClimateNormalParseError(
                                f"Invalid statistics period in "
                                f"{member.filename}, row "
                                f"{row_number}."
                            )

                        if material_years > (
                            statistics_ended_year
                            - statistics_started_year
                            + 1
                        ):
                            raise ClimateNormalParseError(
                                f"Material years exceed the "
                                f"statistics period in "
                                f"{member.filename}, row "
                                f"{row_number}."
                            )

                        started_year = (
                            statistics_started_year
                        )
                        ended_year = statistics_ended_year

                    if not 1 <= month <= 12:
                        raise ClimateNormalParseError(
                            f"Invalid month in "
                            f"{member.filename}, row "
                            f"{row_number}."
                        )

                    daily_values, daily_remarks = (
                        parse_daily_values(
                            row,
                            filename=member.filename,
                            row_number=row_number,
                            divisor=divisor,
                        )
                    )

                    series_count += 1
                    yield ClimateNormalSeriesRecord(
                        source_station_id=source_station_id,
                        source_element_code=(
                            source_element_code
                        ),
                        element_key=element_key,
                        month=month,
                        material_years=material_years,
                        statistics_started_year=started_year,
                        statistics_ended_year=ended_year,
                        daily_values=daily_values,
                        daily_remarks=daily_remarks,
                    )

    if series_count == 0:
        raise ClimateNormalParseError(
            "No supported climate-normal records found."
        )

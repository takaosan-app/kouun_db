from __future__ import annotations

import csv
import io

from collector.jma_csv_parser import (
    ENCODING,
    parse_jma_csv,
)
from collector.models import ParsedJmaCsv


class JmaMultiCsvError(ValueError):
    pass


def parse_jma_multi_csv(
    content: bytes,
) -> tuple[ParsedJmaCsv, ...]:
    rows = _read_rows(content)
    header_index = _find_header_index(rows)
    station_groups = _find_station_groups(
        rows,
        header_index,
    )

    parsed_stations: list[ParsedJmaCsv] = []

    for start, end, expected_name in station_groups:
        station_content = _build_station_csv(
            rows,
            start=start,
            end=end,
        )
        parsed = parse_jma_csv(station_content)

        if parsed.station_name != expected_name:
            raise JmaMultiCsvError(
                "Parsed station name does not match "
                f"the station header: "
                f"{parsed.station_name!r} != "
                f"{expected_name!r}"
            )

        parsed_stations.append(parsed)

    return tuple(parsed_stations)


def _read_rows(
    content: bytes,
) -> list[list[str]]:
    if not content:
        raise JmaMultiCsvError(
            "CSV content is empty."
        )

    try:
        text = content.decode(ENCODING)
    except UnicodeDecodeError as error:
        raise JmaMultiCsvError(
            f"CSV is not valid {ENCODING} text."
        ) from error

    if "<html" in text[:1000].lower():
        raise JmaMultiCsvError(
            "Received HTML instead of CSV."
        )

    try:
        return list(
            csv.reader(
                io.StringIO(text, newline="")
            )
        )
    except csv.Error as error:
        raise JmaMultiCsvError(
            f"Invalid CSV structure: {error}"
        ) from error


def _find_header_index(
    rows: list[list[str]],
) -> int:
    for index, row in enumerate(rows):
        if row and row[0].strip() == "年月日":
            return index

    raise JmaMultiCsvError(
        "Date header was not found."
    )


def _find_station_groups(
    rows: list[list[str]],
    header_index: int,
) -> tuple[tuple[int, int, str], ...]:
    if header_index == 0:
        raise JmaMultiCsvError(
            "Station header was not found."
        )

    header_row = rows[header_index]
    station_row = rows[header_index - 1]

    if len(station_row) != len(header_row):
        raise JmaMultiCsvError(
            "Station and observation headers have "
            "different column counts."
        )

    groups: list[tuple[int, int, str]] = []
    start = 1

    while start < len(station_row):
        station_name = station_row[start].strip()

        if not station_name:
            raise JmaMultiCsvError(
                "Station name is empty at column "
                f"{start + 1}."
            )

        end = start + 1

        while (
            end < len(station_row)
            and station_row[end].strip()
            == station_name
        ):
            end += 1

        groups.append(
            (
                start,
                end,
                station_name,
            )
        )
        start = end

    names = [
        station_name
        for _, _, station_name in groups
    ]

    if len(names) != len(set(names)):
        raise JmaMultiCsvError(
            "Station names are not unique in the CSV."
        )

    if not groups:
        raise JmaMultiCsvError(
            "No station columns were found."
        )

    return tuple(groups)


def _build_station_csv(
    rows: list[list[str]],
    *,
    start: int,
    end: int,
) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(
        output,
        lineterminator="\r\n",
    )

    for row in rows:
        first_cell = row[0] if row else ""
        station_cells = [
            row[index]
            if index < len(row)
            else ""
            for index in range(start, end)
        ]
        writer.writerow(
            [
                first_cell,
                *station_cells,
            ]
        )

    return output.getvalue().encode(ENCODING)

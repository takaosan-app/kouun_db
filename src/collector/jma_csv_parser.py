from __future__ import annotations

import csv
import io
from datetime import date
from decimal import Decimal, InvalidOperation

from collector.jma_csv_layout import (
    CsvLayout,
    LAYOUTS_BY_COLUMN_COUNT,
    ValueKind,
)
from collector.models import ObservationRecord, ParsedJmaCsv, ValueState

ENCODING = "cp932"

QUALITY_STATES: dict[str, ValueState] = {
    "8": "observed",
    "5": "observed",
    "4": "observed",
    "2": "questionable",
    "1": "missing",
    "0": "not_observed",
}


class JmaCsvError(ValueError):
    pass


def parse_jma_csv(content: bytes) -> ParsedJmaCsv:
    if not content:
        raise JmaCsvError("CSV content is empty.")

    try:
        text = content.decode(ENCODING)
    except UnicodeDecodeError as error:
        raise JmaCsvError("CSV is not valid CP932 text.") from error

    if "<html" in text[:1000].lower():
        raise JmaCsvError("Received HTML instead of CSV.")

    try:
        rows = list(csv.reader(io.StringIO(text, newline="")))
    except csv.Error as error:
        raise JmaCsvError(f"Invalid CSV structure: {error}") from error

    header_index = _find_header_index(rows)
    layout = _select_layout(rows[header_index])
    _validate_header(rows[header_index], layout)

    station_name = _read_station_name(rows, header_index)
    detail_index = _find_detail_header_index(
        rows,
        header_index + 1,
    )
    _validate_detail_header(
        rows,
        header_index,
        detail_index,
        layout,
    )

    observations: list[ObservationRecord] = []
    previous_date: date | None = None

    for row_number, row in enumerate(
        rows[detail_index + 1 :],
        start=detail_index + 2,
    ):
        if not any(cell.strip() for cell in row):
            continue

        if len(row) != layout.column_count:
            raise JmaCsvError(
                f"Row {row_number} has {len(row)} columns; "
                f"expected {layout.column_count}."
            )

        observed_on = _parse_date(row[0], row_number)

        if previous_date is not None and observed_on <= previous_date:
            raise JmaCsvError(
                f"Dates are not strictly increasing at row {row_number}."
            )

        previous_date = observed_on

        for column in layout.columns:
            observations.append(
                _parse_observation(
                    row=row,
                    row_number=row_number,
                    observed_on=observed_on,
                    element_key=column.element_key,
                    value_kind=column.value_kind,
                    value_index=column.value_index,
                    phenomenon_index=column.phenomenon_index,
                    quality_index=column.quality_index,
                    homogeneity_index=column.homogeneity_index,
                )
            )
    if not observations:
        raise JmaCsvError("CSV contains no observation rows.")

    return ParsedJmaCsv(
        station_name=station_name,
        observations=tuple(observations),
    )


def _find_header_index(rows: list[list[str]]) -> int:
    for index, row in enumerate(rows):
        if row and row[0].strip() == "年月日":
            return index

    raise JmaCsvError("Date header was not found.")


def _validate_header(
    row: list[str],
    layout: CsvLayout,
) -> None:
    if not row or row[0].strip() != "年月日":
        raise JmaCsvError("CSV does not start with a date column.")

    for column in layout.columns:
        actual = row[column.value_index].strip()

        if actual != column.header_name:
            raise JmaCsvError(
                f"Header mismatch for {column.element_key}: "
                f"expected {column.header_name!r}, "
                f"received {actual!r}."
            )


def _read_station_name(rows: list[list[str]], header_index: int) -> str:
    if header_index == 0:
        raise JmaCsvError("Station header was not found.")

    names = {
        cell.strip()
        for cell in rows[header_index - 1][1:]
        if cell.strip()
    }

    if len(names) != 1:
        raise JmaCsvError(
            f"Expected one station name, received: {sorted(names)}"
        )

    return names.pop()


def _select_layout(row: list[str]) -> CsvLayout:
    try:
        return LAYOUTS_BY_COLUMN_COUNT[len(row)]
    except KeyError as error:
        raise JmaCsvError(
            f"Unsupported CSV layout with {len(row)} columns."
        ) from error


def _find_detail_header_index(
    rows: list[list[str]],
    start_index: int,
) -> int:
    for index in range(start_index, len(rows)):
        if any(
            cell.strip() == "品質情報"
            for cell in rows[index]
        ):
            return index

    raise JmaCsvError("Detail header was not found.")


def _validate_detail_header(
    rows: list[list[str]],
    header_index: int,
    detail_index: int,
    layout: CsvLayout,
) -> None:
    detail_row = rows[detail_index]

    if len(detail_row) != layout.column_count:
        raise JmaCsvError(
            "CSV detail header has an unexpected column count."
        )

    subheader_rows = rows[
        header_index + 1 : detail_index
    ]

    for column in layout.columns:
        if (
            detail_row[column.quality_index].strip()
            != "品質情報"
        ):
            raise JmaCsvError(
                f"Quality header mismatch for "
                f"{column.element_key}."
            )

        if (
            detail_row[column.homogeneity_index].strip()
            != "均質番号"
        ):
            raise JmaCsvError(
                f"Homogeneity header mismatch for "
                f"{column.element_key}."
            )

        if column.phenomenon_index is not None:
            if (
                detail_row[
                    column.phenomenon_index
                ].strip()
                != "現象なし情報"
            ):
                raise JmaCsvError(
                    f"Phenomenon header mismatch for "
                    f"{column.element_key}."
                )

        if column.subheader_name is not None:
            found = any(
                len(row) > column.value_index
                and row[column.value_index].strip()
                == column.subheader_name
                for row in subheader_rows
            )

            if not found:
                raise JmaCsvError(
                    f"Subheader mismatch for "
                    f"{column.element_key}."
                )


def _parse_date(raw_date: str, row_number: int) -> date:
    try:
        year, month, day = (int(part) for part in raw_date.split("/"))
        return date(year, month, day)
    except (TypeError, ValueError) as error:
        raise JmaCsvError(
            f"Invalid date at row {row_number}: {raw_date!r}"
        ) from error


def _parse_observation(
    *,
    row: list[str],
    row_number: int,
    observed_on: date,
    element_key: str,
    value_kind: ValueKind,
    value_index: int,
    phenomenon_index: int | None,
    quality_index: int,
    homogeneity_index: int,
) -> ObservationRecord:
    raw_value = row[value_index].strip()
    quality_code = row[quality_index].strip()

    if not quality_code:
        raise JmaCsvError(
            f"Quality code is empty at row {row_number}, "
            f"element {element_key}."
        )

    try:
        value_state = QUALITY_STATES[quality_code]
    except KeyError as error:
        raise JmaCsvError(
            f"Unknown quality code {quality_code!r} "
            f"at row {row_number}, element {element_key}."
        ) from error

    value, text_value = _parse_value(
        raw_value,
        value_kind,
        value_state,
        row_number,
        element_key,
    )

    no_phenomenon = _parse_no_phenomenon(
        row=row,
        column_index=phenomenon_index,
        value_state=value_state,
        row_number=row_number,
        element_key=element_key,
    )

    homogeneity_number = row[homogeneity_index].strip() or None

    return ObservationRecord(
        observed_on=observed_on,
        element_key=element_key,
        raw_value=raw_value,
        value=value,
        text_value=text_value,
        value_state=value_state,
        quality_code=quality_code,
        homogeneity_number=homogeneity_number,
        no_phenomenon=no_phenomenon,
    )


def _parse_value(
    raw_value: str,
    value_kind: ValueKind,
    value_state: ValueState,
    row_number: int,
    element_key: str,
) -> tuple[Decimal | None, str | None]:
    if value_state not in ("observed", "questionable"):
        if raw_value:
            raise JmaCsvError(
                f"Unexpected value for state {value_state} "
                f"at row {row_number}, element {element_key}."
            )
        return None, None

    if not raw_value:
        raise JmaCsvError(
            f"Value is empty for state {value_state} "
            f"at row {row_number}, element {element_key}."
        )

    if value_kind in ("direction", "text"):
        return None, raw_value

    if value_kind == "numeric":
        try:
            return Decimal(raw_value), None
        except InvalidOperation as error:
            raise JmaCsvError(
                f"Invalid numeric value {raw_value!r} "
                f"at row {row_number}, element {element_key}."
            ) from error

    raise JmaCsvError(
        f"Unknown value kind {value_kind!r} "
        f"for element {element_key}."
    )


def _parse_no_phenomenon(
    *,
    row: list[str],
    column_index: int | None,
    value_state: ValueState,
    row_number: int,
    element_key: str,
) -> bool | None:
    if column_index is None:
        return None

    raw_flag = row[column_index].strip()

    if value_state not in ("observed", "questionable"):
        if raw_flag:
            raise JmaCsvError(
                f"Unexpected phenomenon flag at row {row_number}, "
                f"element {element_key}."
            )
        return None

    if raw_flag == "1":
        return True

    if raw_flag == "0":
        return False

    raise JmaCsvError(
        f"Invalid phenomenon flag {raw_flag!r} "
        f"at row {row_number}, element {element_key}."
    )
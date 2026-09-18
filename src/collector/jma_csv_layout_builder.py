from __future__ import annotations

from dataclasses import dataclass

from collector.jma_csv_layout import (
    ColumnSpec,
    CsvLayout,
    ValueKind,
)


class CsvLayoutBuildError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ElementDefinition:
    element_key: str
    value_kind: ValueKind


ELEMENTS: dict[
    tuple[str, str | None],
    ElementDefinition,
] = {
    ("平均気温(℃)", None): ElementDefinition(
        "daily_mean_temperature",
        "numeric",
    ),
    ("最高気温(℃)", None): ElementDefinition(
        "daily_max_temperature",
        "numeric",
    ),
    ("最低気温(℃)", None): ElementDefinition(
        "daily_min_temperature",
        "numeric",
    ),
    ("降水量の合計(mm)", None): ElementDefinition(
        "daily_precipitation",
        "numeric",
    ),
    ("日照時間(時間)", None): ElementDefinition(
        "daily_sunshine_duration",
        "numeric",
    ),
    ("平均現地気圧(hPa)", None): ElementDefinition(
        "daily_mean_station_pressure",
        "numeric",
    ),
    ("平均海面気圧(hPa)", None): ElementDefinition(
        "daily_mean_sea_level_pressure",
        "numeric",
    ),
    ("平均湿度(％)", None): ElementDefinition(
        "daily_mean_relative_humidity",
        "numeric",
    ),
    ("最小相対湿度(％)", None): ElementDefinition(
        "daily_min_relative_humidity",
        "numeric",
    ),
    ("平均風速(m/s)", None): ElementDefinition(
        "daily_mean_wind_speed",
        "numeric",
    ),
    ("最大風速(m/s)", None): ElementDefinition(
        "daily_max_wind_speed",
        "numeric",
    ),
    ("最大風速(m/s)", "風向"): ElementDefinition(
        "daily_max_wind_direction",
        "direction",
    ),
    ("最大瞬間風速(m/s)", None): ElementDefinition(
        "daily_max_instantaneous_wind_speed",
        "numeric",
    ),
    (
        "最大瞬間風速(m/s)",
        "風向",
    ): ElementDefinition(
        "daily_max_instantaneous_wind_direction",
        "direction",
    ),
    ("最多風向(16方位)", None): ElementDefinition(
        "daily_most_frequent_wind_direction",
        "direction",
    ),
    ("最深積雪(cm)", None): ElementDefinition(
        "daily_max_snow_depth",
        "numeric",
    ),
    ("降雪量合計(cm)", None): ElementDefinition(
        "daily_snowfall",
        "numeric",
    ),
    (
        "天気概況(昼：06時～18時)",
        None,
    ): ElementDefinition(
        "daily_weather_summary_daytime",
        "text",
    ),
    (
        "天気概況(夜：18時～翌日06時)",
        None,
    ): ElementDefinition(
        "daily_weather_summary_nighttime",
        "text",
    ),
}


def build_csv_layout(
    header_row: list[str],
    subheader_rows: list[list[str]],
    detail_row: list[str],
) -> CsvLayout:
    column_count = len(header_row)

    if not header_row or header_row[0].strip() != "年月日":
        raise CsvLayoutBuildError(
            "CSV does not start with a date column."
        )

    if len(detail_row) != column_count:
        raise CsvLayoutBuildError(
            "CSV header rows have different column counts."
        )

    columns: list[ColumnSpec] = []

    for start, end, header_name in _find_header_groups(
        header_row
    ):
        columns.extend(
            _build_group_columns(
                header_name=header_name,
                start=start,
                end=end,
                subheader_rows=subheader_rows,
                detail_row=detail_row,
            )
        )

    if not columns:
        raise CsvLayoutBuildError(
            "No observation columns were found."
        )

    return CsvLayout(
        name="detected",
        column_count=column_count,
        columns=tuple(columns),
    )


def _find_header_groups(
    header_row: list[str],
) -> list[tuple[int, int, str]]:
    groups: list[tuple[int, int, str]] = []
    start = 1

    while start < len(header_row):
        header_name = header_row[start].strip()

        if not header_name:
            raise CsvLayoutBuildError(
                f"Observation header is empty at column {start + 1}."
            )

        end = start + 1

        while (
            end < len(header_row)
            and header_row[end].strip() == header_name
        ):
            end += 1

        groups.append((start, end, header_name))
        start = end

    return groups


def _build_group_columns(
    *,
    header_name: str,
    start: int,
    end: int,
    subheader_rows: list[list[str]],
    detail_row: list[str],
) -> list[ColumnSpec]:
    value_indices = [
        index
        for index in range(start, end)
        if not detail_row[index].strip()
    ]
    homogeneity_indices = _find_detail_indices(
        detail_row,
        start,
        end,
        "均質番号",
    )

    if len(homogeneity_indices) != 1:
        raise CsvLayoutBuildError(
            f"Expected one homogeneity column for {header_name!r}."
        )

    columns: list[ColumnSpec] = []

    for position, value_index in enumerate(value_indices):
        segment_end = (
            value_indices[position + 1]
            if position + 1 < len(value_indices)
            else end
        )
        quality_indices = _find_detail_indices(
            detail_row,
            value_index + 1,
            segment_end,
            "品質情報",
        )

        if len(quality_indices) != 1:
            raise CsvLayoutBuildError(
                f"Expected one quality column for "
                f"{header_name!r} at column {value_index + 1}."
            )

        phenomenon_indices = _find_detail_indices(
            detail_row,
            value_index + 1,
            segment_end,
            "現象なし情報",
        )

        if len(phenomenon_indices) > 1:
            raise CsvLayoutBuildError(
                f"Multiple phenomenon columns for {header_name!r}."
            )

        subheader_name = _read_subheader(
            subheader_rows,
            value_index,
        )
        definition = ELEMENTS.get(
            (header_name, subheader_name)
        )

        if definition is None:
            raise CsvLayoutBuildError(
                "Unknown observation header: "
                f"{header_name!r}, subheader={subheader_name!r}."
            )

        columns.append(
            ColumnSpec(
                element_key=definition.element_key,
                header_name=header_name,
                value_kind=definition.value_kind,
                value_index=value_index,
                quality_index=quality_indices[0],
                homogeneity_index=homogeneity_indices[0],
                phenomenon_index=(
                    phenomenon_indices[0]
                    if phenomenon_indices
                    else None
                ),
                subheader_name=subheader_name,
            )
        )

    return columns


def _find_detail_indices(
    row: list[str],
    start: int,
    end: int,
    name: str,
) -> list[int]:
    return [
        index
        for index in range(start, end)
        if row[index].strip() == name
    ]


def _read_subheader(
    rows: list[list[str]],
    column_index: int,
) -> str | None:
    names = {
        row[column_index].strip()
        for row in rows
        if len(row) > column_index
        and row[column_index].strip()
    }

    if len(names) > 1:
        raise CsvLayoutBuildError(
            f"Multiple subheaders at column {column_index + 1}: "
            f"{sorted(names)}"
        )

    return names.pop() if names else None

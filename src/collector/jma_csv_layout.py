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


CORE_COLUMNS = (
    ColumnSpec(
        "daily_mean_temperature",
        "平均気温(℃)",
        "numeric",
        1,
        2,
        3,
    ),
    ColumnSpec(
        "daily_max_temperature",
        "最高気温(℃)",
        "numeric",
        4,
        5,
        6,
    ),
    ColumnSpec(
        "daily_min_temperature",
        "最低気温(℃)",
        "numeric",
        7,
        8,
        9,
    ),
    ColumnSpec(
        "daily_precipitation",
        "降水量の合計(mm)",
        "numeric",
        10,
        12,
        13,
        phenomenon_index=11,
    ),
)


EXTENDED_COLUMNS = (
    *CORE_COLUMNS,
    ColumnSpec(
        "daily_sunshine_duration",
        "日照時間(時間)",
        "numeric",
        14,
        16,
        17,
        phenomenon_index=15,
    ),
    ColumnSpec(
        "daily_mean_station_pressure",
        "平均現地気圧(hPa)",
        "numeric",
        18,
        19,
        20,
    ),
    ColumnSpec(
        "daily_mean_sea_level_pressure",
        "平均海面気圧(hPa)",
        "numeric",
        21,
        22,
        23,
    ),
    ColumnSpec(
        "daily_mean_relative_humidity",
        "平均湿度(％)",
        "numeric",
        24,
        25,
        26,
    ),
    ColumnSpec(
        "daily_min_relative_humidity",
        "最小相対湿度(％)",
        "numeric",
        27,
        28,
        29,
    ),
    ColumnSpec(
        "daily_mean_wind_speed",
        "平均風速(m/s)",
        "numeric",
        30,
        31,
        32,
    ),
    ColumnSpec(
        "daily_max_wind_speed",
        "最大風速(m/s)",
        "numeric",
        33,
        34,
        37,
    ),
    ColumnSpec(
        "daily_max_wind_direction",
        "最大風速(m/s)",
        "direction",
        35,
        36,
        37,
        subheader_name="風向",
    ),
    ColumnSpec(
        "daily_max_instantaneous_wind_speed",
        "最大瞬間風速(m/s)",
        "numeric",
        38,
        39,
        42,
    ),
    ColumnSpec(
        "daily_max_instantaneous_wind_direction",
        "最大瞬間風速(m/s)",
        "direction",
        40,
        41,
        42,
        subheader_name="風向",
    ),
    ColumnSpec(
        "daily_most_frequent_wind_direction",
        "最多風向(16方位)",
        "direction",
        43,
        44,
        45,
    ),
    ColumnSpec(
        "daily_max_snow_depth",
        "最深積雪(cm)",
        "numeric",
        46,
        48,
        49,
        phenomenon_index=47,
    ),
    ColumnSpec(
        "daily_snowfall",
        "降雪量合計(cm)",
        "numeric",
        50,
        52,
        53,
        phenomenon_index=51,
    ),
    ColumnSpec(
        "daily_weather_summary_daytime",
        "天気概況(昼：06時～18時)",
        "text",
        54,
        55,
        56,
    ),
    ColumnSpec(
        "daily_weather_summary_nighttime",
        "天気概況(夜：18時～翌日06時)",
        "text",
        57,
        58,
        59,
    ),
)


CORE_LAYOUT = CsvLayout(
    name="core",
    column_count=14,
    columns=CORE_COLUMNS,
)

EXTENDED_LAYOUT = CsvLayout(
    name="extended",
    column_count=60,
    columns=EXTENDED_COLUMNS,
)

LAYOUTS_BY_COLUMN_COUNT = {
    CORE_LAYOUT.column_count: CORE_LAYOUT,
    EXTENDED_LAYOUT.column_count: EXTENDED_LAYOUT,
}
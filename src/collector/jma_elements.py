from __future__ import annotations

from typing import TypedDict


class ElementRequest(TypedDict):
    code: str
    option: str
    name: str
    unit: str


CORE_ELEMENTS: tuple[ElementRequest, ...] = (
    {
        "code": "201",
        "option": "",
        "name": "daily_mean_temperature",
        "unit": "degC",
    },
    {
        "code": "202",
        "option": "",
        "name": "daily_max_temperature",
        "unit": "degC",
    },
    {
        "code": "203",
        "option": "",
        "name": "daily_min_temperature",
        "unit": "degC",
    },
    {
        "code": "101",
        "option": "",
        "name": "daily_precipitation",
        "unit": "mm",
    },
)


EXTENDED_ELEMENTS: tuple[ElementRequest, ...] = (
    *CORE_ELEMENTS,
    {
        "code": "401",
        "option": "",
        "name": "daily_sunshine_duration",
        "unit": "h",
    },
    {
        "code": "601",
        "option": "",
        "name": "daily_mean_station_pressure",
        "unit": "hPa",
    },
    {
        "code": "602",
        "option": "",
        "name": "daily_mean_sea_level_pressure",
        "unit": "hPa",
    },
    {
        "code": "605",
        "option": "",
        "name": "daily_mean_relative_humidity",
        "unit": "percent",
    },
    {
        "code": "606",
        "option": "",
        "name": "daily_min_relative_humidity",
        "unit": "percent",
    },
    {
        "code": "301",
        "option": "",
        "name": "daily_mean_wind_speed",
        "unit": "m/s",
    },
    {
        "code": "302",
        "option": "",
        "name": "daily_max_wind",
        "unit": "mixed",
    },
    {
        "code": "304",
        "option": "",
        "name": "daily_max_instantaneous_wind",
        "unit": "mixed",
    },
    {
        "code": "305",
        "option": "",
        "name": "daily_most_frequent_wind_direction",
        "unit": "direction",
    },
    {
        "code": "501",
        "option": "",
        "name": "daily_max_snow_depth",
        "unit": "cm",
    },
    {
        "code": "503",
        "option": "",
        "name": "daily_snowfall",
        "unit": "cm",
    },
    {
        "code": "701",
        "option": "",
        "name": "daily_weather_summary_daytime",
        "unit": "text",
    },
    {
        "code": "702",
        "option": "",
        "name": "daily_weather_summary_nighttime",
        "unit": "text",
    },
)

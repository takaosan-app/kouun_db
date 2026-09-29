from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TableSpec:
    """How one analysis table is copied to the app database.

    The table has the same name in analysis (source) and weather (target).
    """

    name: str
    columns: tuple[str, ...]
    key_columns: tuple[str, ...]
    station_scoped: bool
    date_column: str | None = None
    retention: str | None = None
    delete_missing: bool = False


WEATHER_ELEMENT = TableSpec(
    name="weather_element",
    columns=(
        "element_code", "element_key", "column_name", "display_name",
        "unit", "value_kind", "scale_divisor", "decimal_places",
        "quality_bit_position", "display_order",
    ),
    key_columns=("element_code",),
    station_scoped=False,
)

WEATHER_STATION = TableSpec(
    name="weather_station",
    columns=(
        "station_id", "station_key", "obsdl_station_id",
        "official_station_number", "name", "kana_name",
        "station_type_code", "location", "elevation",
        "observation_started_on", "observation_ended_on",
        "metadata_effective_from", "source_updated_at",
    ),
    key_columns=("station_id",),
    station_scoped=True,
)

STATION_ELEMENT_CAPABILITY = TableSpec(
    name="station_element_capability",
    columns=(
        "id", "station_id", "element_code", "valid_from", "valid_to",
        "source_updated_at",
    ),
    key_columns=("id",),
    station_scoped=True,
    delete_missing=True,
)

CLIMATE_NORMAL_RELEASE = TableSpec(
    name="climate_normal_release",
    columns=(
        "climate_normal_release_id", "release_key", "name", "version",
        "statistics_started_on", "statistics_ended_on",
        "applicable_from", "applicable_to", "published_on",
        "source_updated_at",
    ),
    key_columns=("climate_normal_release_id",),
    station_scoped=False,
)

STATION_DAILY_WEATHER_NORMAL = TableSpec(
    name="station_daily_weather_normal",
    columns=(
        "climate_normal_release_id", "station_id", "month", "day",
        "mean_temperature", "max_temperature", "min_temperature",
        "precipitation", "sunshine_duration", "max_snow_depth",
        "snowfall", "availability_mask", "source_updated_at",
    ),
    key_columns=("climate_normal_release_id", "station_id", "month", "day"),
    station_scoped=True,
)

FEATURE_CALCULATION_VERSION = TableSpec(
    name="feature_calculation_version",
    columns=(
        "calculation_version", "version_name", "description",
        "effective_from",
    ),
    key_columns=("calculation_version",),
    station_scoped=False,
)

STATION_DAILY_WEATHER = TableSpec(
    name="station_daily_weather",
    columns=(
        "station_id", "observed_on",
        "mean_temperature", "max_temperature", "min_temperature",
        "precipitation", "rain_observed", "sunshine_duration",
        "mean_station_pressure", "mean_sea_level_pressure",
        "mean_relative_humidity", "min_relative_humidity",
        "mean_wind_speed", "max_wind_speed", "max_wind_direction_code",
        "max_instantaneous_wind_speed",
        "max_instantaneous_wind_direction_code",
        "most_frequent_wind_direction_code",
        "max_snow_depth", "snowfall", "quality_mask",
        "source_updated_at",
    ),
    key_columns=("station_id", "observed_on"),
    station_scoped=True,
    date_column="observed_on",
    retention="18 months",
)

STATION_DAILY_WEATHER_FEATURE = TableSpec(
    name="station_daily_weather_feature",
    columns=(
        "station_id", "observed_on", "calculation_version",
        "climate_normal_release_id",
        "cumulative_mean_temperature", "cumulative_max_temperature",
        "cumulative_min_temperature", "cumulative_precipitation",
        "cumulative_sunshine_duration",
        "cumulative_mean_relative_humidity", "cumulative_mean_wind_speed",
        "valid_mean_temperature_days", "valid_max_temperature_days",
        "valid_min_temperature_days", "valid_precipitation_days",
        "valid_sunshine_duration_days",
        "valid_mean_relative_humidity_days", "valid_mean_wind_speed_days",
        "cumulative_mean_temperature_anomaly",
        "cumulative_max_temperature_anomaly",
        "cumulative_min_temperature_anomaly",
        "cumulative_precipitation_anomaly",
        "cumulative_sunshine_duration_anomaly",
        "valid_mean_temperature_normal_days",
        "valid_max_temperature_normal_days",
        "valid_min_temperature_normal_days",
        "valid_precipitation_normal_days",
        "valid_sunshine_duration_normal_days",
        "cumulative_rain_days", "cumulative_precipitation_ge_1mm_days",
        "cumulative_precipitation_ge_5mm_days",
        "cumulative_precipitation_ge_10mm_days",
        "cumulative_max_temperature_ge_30c_days",
        "cumulative_max_temperature_ge_35c_days",
        "cumulative_min_temperature_ge_25c_days",
        "cumulative_min_temperature_lt_0c_days",
        "cumulative_sunshine_lt_1h_days", "cumulative_sunshine_lt_3h_days",
        "consecutive_rain_days", "consecutive_dry_days",
        "consecutive_hot_days", "consecutive_cold_days",
        "consecutive_low_sunshine_days",
        "source_updated_at", "calculated_at",
    ),
    key_columns=("station_id", "observed_on"),
    station_scoped=True,
    date_column="observed_on",
    retention="11 years",
)

# Catalogs first, so that foreign keys are satisfied.
CATALOG_TABLES = (
    WEATHER_ELEMENT,
    WEATHER_STATION,
    STATION_ELEMENT_CAPABILITY,
    CLIMATE_NORMAL_RELEASE,
    FEATURE_CALCULATION_VERSION,
)
DAILY_TABLES = (
    STATION_DAILY_WEATHER,
    STATION_DAILY_WEATHER_FEATURE,
)

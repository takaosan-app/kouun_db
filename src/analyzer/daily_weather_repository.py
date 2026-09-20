from __future__ import annotations

from datetime import date

import psycopg


UPSERT_DAILY_WEATHER = """
    WITH direction_codes AS (
        SELECT
            name_ja,
            direction_code
        FROM analysis.wind_direction
    ),
    source_rows AS (
        SELECT
            observation.station_id,
            observation.observed_on,
            element.element_key,
            observation.value,
            observation.text_value,
            observation.value_state,
            observation.no_phenomenon,
            observation.updated_at
        FROM weather.observation AS observation
        JOIN weather.element AS element
            ON element.id = observation.element_id
        WHERE observation.granularity = 'daily'
          AND observation.observed_on BETWEEN %s AND %s
          AND (
              %s::text IS NULL
              OR EXISTS (
                  SELECT 1
                  FROM weather.station_observation_area AS membership
                  WHERE membership.station_id = observation.station_id
                    AND membership.area_code = %s
              )
          )
          AND element.element_key = ANY(%s::text[])
    ),
    daily_rows AS (
        SELECT
            source_rows.station_id,
            source_rows.observed_on,
            CAST(ROUND(MAX(source_rows.value) FILTER (
                WHERE source_rows.element_key = 'daily_mean_temperature'
            ) * 10) AS smallint) AS mean_temperature,
            CAST(ROUND(MAX(source_rows.value) FILTER (
                WHERE source_rows.element_key = 'daily_max_temperature'
            ) * 10) AS smallint) AS max_temperature,
            CAST(ROUND(MAX(source_rows.value) FILTER (
                WHERE source_rows.element_key = 'daily_min_temperature'
            ) * 10) AS smallint) AS min_temperature,
            CAST(ROUND(MAX(source_rows.value) FILTER (
                WHERE source_rows.element_key = 'daily_precipitation'
            ) * 10) AS smallint) AS precipitation,
            CASE
                WHEN COUNT(*) FILTER (
                    WHERE source_rows.element_key = 'daily_precipitation'
                      AND source_rows.value_state IN ('observed', 'questionable')
                ) = 0 THEN NULL
                ELSE BOOL_OR(
                    source_rows.value > 0
                    OR COALESCE(
                        source_rows.no_phenomenon = false,
                        false
                    )
                ) FILTER (
                    WHERE source_rows.element_key = 'daily_precipitation'
                )
            END AS rain_observed,
            CAST(ROUND(MAX(source_rows.value) FILTER (
                WHERE source_rows.element_key = 'daily_sunshine_duration'
            ) * 10) AS smallint) AS sunshine_duration,
            CAST(ROUND(MAX(source_rows.value) FILTER (
                WHERE source_rows.element_key = 'daily_mean_station_pressure'
            ) * 10) AS smallint) AS mean_station_pressure,
            CAST(ROUND(MAX(source_rows.value) FILTER (
                WHERE source_rows.element_key = 'daily_mean_sea_level_pressure'
            ) * 10) AS smallint) AS mean_sea_level_pressure,
            CAST(ROUND(MAX(source_rows.value) FILTER (
                WHERE source_rows.element_key = 'daily_mean_relative_humidity'
            ) * 10) AS smallint) AS mean_relative_humidity,
            CAST(ROUND(MAX(source_rows.value) FILTER (
                WHERE source_rows.element_key = 'daily_min_relative_humidity'
            ) * 10) AS smallint) AS min_relative_humidity,
            CAST(ROUND(MAX(source_rows.value) FILTER (
                WHERE source_rows.element_key = 'daily_mean_wind_speed'
            ) * 10) AS smallint) AS mean_wind_speed,
            CAST(ROUND(MAX(source_rows.value) FILTER (
                WHERE source_rows.element_key = 'daily_max_wind_speed'
            ) * 10) AS smallint) AS max_wind_speed,
            MAX(max_wind_direction.direction_code)
                AS max_wind_direction_code,
            CAST(ROUND(MAX(source_rows.value) FILTER (
                WHERE source_rows.element_key = 'daily_max_instantaneous_wind_speed'
            ) * 10) AS smallint) AS max_instantaneous_wind_speed,
            MAX(max_instantaneous_direction.direction_code)
                AS max_instantaneous_wind_direction_code,
            MAX(most_frequent_direction.direction_code)
                AS most_frequent_wind_direction_code,
            CAST(ROUND(MAX(source_rows.value) FILTER (
                WHERE source_rows.element_key = 'daily_max_snow_depth'
            ) * 10) AS smallint) AS max_snow_depth,
            CAST(ROUND(MAX(source_rows.value) FILTER (
                WHERE source_rows.element_key = 'daily_snowfall'
            ) * 10) AS smallint) AS snowfall,
            BIT_OR(
                CASE
                    WHEN source_rows.value_state <> 'questionable' THEN 0
                    ELSE 1::bigint << CASE source_rows.element_key
                        WHEN 'daily_mean_temperature' THEN 0
                        WHEN 'daily_max_temperature' THEN 1
                        WHEN 'daily_min_temperature' THEN 2
                        WHEN 'daily_precipitation' THEN 3
                        WHEN 'daily_sunshine_duration' THEN 4
                        WHEN 'daily_mean_station_pressure' THEN 5
                        WHEN 'daily_mean_sea_level_pressure' THEN 6
                        WHEN 'daily_mean_relative_humidity' THEN 7
                        WHEN 'daily_min_relative_humidity' THEN 8
                        WHEN 'daily_mean_wind_speed' THEN 9
                        WHEN 'daily_max_wind_speed' THEN 10
                        WHEN 'daily_max_wind_direction' THEN 11
                        WHEN 'daily_max_instantaneous_wind_speed' THEN 12
                        WHEN 'daily_max_instantaneous_wind_direction' THEN 13
                        WHEN 'daily_most_frequent_wind_direction' THEN 14
                        WHEN 'daily_max_snow_depth' THEN 15
                        WHEN 'daily_snowfall' THEN 16
                    END
                END
            ) AS quality_mask,
            MAX(source_rows.updated_at) AS source_updated_at
        FROM source_rows
        LEFT JOIN direction_codes AS max_wind_direction
            ON source_rows.element_key = 'daily_max_wind_direction'
           AND max_wind_direction.name_ja = source_rows.text_value
        LEFT JOIN direction_codes AS max_instantaneous_direction
            ON source_rows.element_key = 'daily_max_instantaneous_wind_direction'
           AND max_instantaneous_direction.name_ja = source_rows.text_value
        LEFT JOIN direction_codes AS most_frequent_direction
            ON source_rows.element_key = 'daily_most_frequent_wind_direction'
           AND most_frequent_direction.name_ja = source_rows.text_value
        GROUP BY
            source_rows.station_id,
            source_rows.observed_on
    )
    INSERT INTO analysis.station_daily_weather (
        station_id,
        observed_on,
        mean_temperature,
        max_temperature,
        min_temperature,
        precipitation,
        rain_observed,
        sunshine_duration,
        mean_station_pressure,
        mean_sea_level_pressure,
        mean_relative_humidity,
        min_relative_humidity,
        mean_wind_speed,
        max_wind_speed,
        max_wind_direction_code,
        max_instantaneous_wind_speed,
        max_instantaneous_wind_direction_code,
        most_frequent_wind_direction_code,
        max_snow_depth,
        snowfall,
        quality_mask,
        source_updated_at
    )
    SELECT
        station_id,
        observed_on,
        mean_temperature,
        max_temperature,
        min_temperature,
        precipitation,
        rain_observed,
        sunshine_duration,
        mean_station_pressure,
        mean_sea_level_pressure,
        mean_relative_humidity,
        min_relative_humidity,
        mean_wind_speed,
        max_wind_speed,
        max_wind_direction_code,
        max_instantaneous_wind_speed,
        max_instantaneous_wind_direction_code,
        most_frequent_wind_direction_code,
        max_snow_depth,
        snowfall,
        quality_mask,
        source_updated_at
    FROM daily_rows
    ON CONFLICT (station_id, observed_on) DO UPDATE
    SET
        mean_temperature = EXCLUDED.mean_temperature,
        max_temperature = EXCLUDED.max_temperature,
        min_temperature = EXCLUDED.min_temperature,
        precipitation = EXCLUDED.precipitation,
        rain_observed = EXCLUDED.rain_observed,
        sunshine_duration = EXCLUDED.sunshine_duration,
        mean_station_pressure = EXCLUDED.mean_station_pressure,
        mean_sea_level_pressure = EXCLUDED.mean_sea_level_pressure,
        mean_relative_humidity = EXCLUDED.mean_relative_humidity,
        min_relative_humidity = EXCLUDED.min_relative_humidity,
        mean_wind_speed = EXCLUDED.mean_wind_speed,
        max_wind_speed = EXCLUDED.max_wind_speed,
        max_wind_direction_code = EXCLUDED.max_wind_direction_code,
        max_instantaneous_wind_speed = EXCLUDED.max_instantaneous_wind_speed,
        max_instantaneous_wind_direction_code =
            EXCLUDED.max_instantaneous_wind_direction_code,
        most_frequent_wind_direction_code =
            EXCLUDED.most_frequent_wind_direction_code,
        max_snow_depth = EXCLUDED.max_snow_depth,
        snowfall = EXCLUDED.snowfall,
        quality_mask = EXCLUDED.quality_mask,
        source_updated_at = EXCLUDED.source_updated_at,
        refreshed_at = now()
    RETURNING 1
"""


DAILY_ELEMENT_KEYS: tuple[str, ...] = (
    "daily_mean_temperature",
    "daily_max_temperature",
    "daily_min_temperature",
    "daily_precipitation",
    "daily_sunshine_duration",
    "daily_mean_station_pressure",
    "daily_mean_sea_level_pressure",
    "daily_mean_relative_humidity",
    "daily_min_relative_humidity",
    "daily_mean_wind_speed",
    "daily_max_wind_speed",
    "daily_max_wind_direction",
    "daily_max_instantaneous_wind_speed",
    "daily_max_instantaneous_wind_direction",
    "daily_most_frequent_wind_direction",
    "daily_max_snow_depth",
    "daily_snowfall",
)


def upsert_daily_weather(
    connection: psycopg.Connection,
    *,
    start_date: date,
    end_date: date,
    area_code: str | None,
) -> int:
    rows = connection.execute(
        UPSERT_DAILY_WEATHER,
        (
            start_date,
            end_date,
            area_code,
            area_code,
            list(DAILY_ELEMENT_KEYS),
        ),
    ).fetchall()

    return len(rows)

from __future__ import annotations

from dataclasses import dataclass

import psycopg


@dataclass(frozen=True, slots=True)
class ClimateNormalSyncCounts:
    staged: int
    changed: int
    deleted: int


CREATE_CLIMATE_NORMAL_STAGE = """
    CREATE TEMPORARY TABLE
        l1_climate_normal_stage
    ON COMMIT DROP
    AS
    WITH expanded AS (
        SELECT
            target_release.climate_normal_release_id,
            series.station_id,
            series.month,
            indices.day_number AS day,
            element.element_key,
            series.daily_values[
                indices.day_number
            ] AS value,
            series.updated_at
        FROM weather.climate_normal_series AS series
        JOIN weather.climate_normal_release
            AS source_release
            ON source_release.id = series.release_id
        JOIN analysis.climate_normal_release
            AS target_release
            ON target_release.release_key =
                source_release.release_key
        JOIN analysis.weather_station AS station
            ON station.station_id = series.station_id
        JOIN weather.element AS element
            ON element.id = series.element_id
        CROSS JOIN LATERAL generate_subscripts(
            series.daily_values,
            1
        ) AS indices(day_number)
        WHERE series.station_id IS NOT NULL
          AND series.daily_values[
              indices.day_number
          ] IS NOT NULL
          AND series.daily_remarks[
              indices.day_number
          ] = 8
          AND indices.day_number <=
              CASE
                  WHEN series.month = 2 THEN 29
                  WHEN series.month IN (4, 6, 9, 11)
                      THEN 30
                  ELSE 31
              END
          AND element.element_key IN (
              'daily_mean_temperature',
              'daily_max_temperature',
              'daily_min_temperature',
              'daily_precipitation',
              'daily_sunshine_duration',
              'daily_max_snow_depth',
              'daily_snowfall'
          )
    )
    SELECT
        climate_normal_release_id,
        station_id,
        month,
        day,

        CAST(ROUND(MAX(value) FILTER (
            WHERE element_key =
                'daily_mean_temperature'
        ) * 10) AS smallint)
            AS mean_temperature,

        CAST(ROUND(MAX(value) FILTER (
            WHERE element_key =
                'daily_max_temperature'
        ) * 10) AS smallint)
            AS max_temperature,

        CAST(ROUND(MAX(value) FILTER (
            WHERE element_key =
                'daily_min_temperature'
        ) * 10) AS smallint)
            AS min_temperature,

        CAST(ROUND(MAX(value) FILTER (
            WHERE element_key =
                'daily_precipitation'
        ) * 10) AS smallint)
            AS precipitation,

        CAST(ROUND(MAX(value) FILTER (
            WHERE element_key =
                'daily_sunshine_duration'
        ) * 10) AS smallint)
            AS sunshine_duration,

        CAST(ROUND(MAX(value) FILTER (
            WHERE element_key =
                'daily_max_snow_depth'
        ) * 10) AS smallint)
            AS max_snow_depth,

        CAST(ROUND(MAX(value) FILTER (
            WHERE element_key =
                'daily_snowfall'
        ) * 10) AS smallint)
            AS snowfall,

        CAST(
            BIT_OR(
                CASE element_key
                    WHEN 'daily_mean_temperature'
                        THEN 1 << 0
                    WHEN 'daily_max_temperature'
                        THEN 1 << 1
                    WHEN 'daily_min_temperature'
                        THEN 1 << 2
                    WHEN 'daily_precipitation'
                        THEN 1 << 3
                    WHEN 'daily_sunshine_duration'
                        THEN 1 << 4
                    WHEN 'daily_max_snow_depth'
                        THEN 1 << 5
                    WHEN 'daily_snowfall'
                        THEN 1 << 6
                    ELSE 0
                END
            )
            AS smallint
        ) AS availability_mask,

        MAX(updated_at) AS source_updated_at
    FROM expanded
    GROUP BY
        climate_normal_release_id,
        station_id,
        month,
        day
"""


ADD_CLIMATE_NORMAL_STAGE_KEY = """
    ALTER TABLE l1_climate_normal_stage
    ADD PRIMARY KEY (
        climate_normal_release_id,
        station_id,
        month,
        day
    )
"""


COUNT_CLIMATE_NORMAL_STAGE = """
    SELECT count(*)
    FROM l1_climate_normal_stage
"""


DELETE_STALE_CLIMATE_NORMALS = """
    WITH deleted AS (
        DELETE FROM
            analysis.station_daily_weather_normal
            AS target
        WHERE EXISTS (
            SELECT 1
            FROM analysis.climate_normal_release
                AS target_release
            JOIN weather.climate_normal_release
                AS source_release
                ON source_release.release_key =
                    target_release.release_key
            WHERE
                target_release.climate_normal_release_id =
                    target.climate_normal_release_id
        )
          AND NOT EXISTS (
              SELECT 1
              FROM l1_climate_normal_stage AS stage
              WHERE stage.climate_normal_release_id =
                        target.climate_normal_release_id
                AND stage.station_id =
                        target.station_id
                AND stage.month = target.month
                AND stage.day = target.day
          )
        RETURNING 1
    )
    SELECT count(*)
    FROM deleted
"""


UPSERT_CLIMATE_NORMALS = """
    WITH changed AS (
        INSERT INTO
            analysis.station_daily_weather_normal
            AS target (
                climate_normal_release_id,
                station_id,
                month,
                day,
                mean_temperature,
                max_temperature,
                min_temperature,
                precipitation,
                sunshine_duration,
                max_snow_depth,
                snowfall,
                availability_mask,
                source_updated_at
            )
        SELECT
            climate_normal_release_id,
            station_id,
            month,
            day,
            mean_temperature,
            max_temperature,
            min_temperature,
            precipitation,
            sunshine_duration,
            max_snow_depth,
            snowfall,
            availability_mask,
            source_updated_at
        FROM l1_climate_normal_stage
        ON CONFLICT (
            climate_normal_release_id,
            station_id,
            month,
            day
        ) DO UPDATE
        SET
            mean_temperature =
                EXCLUDED.mean_temperature,
            max_temperature =
                EXCLUDED.max_temperature,
            min_temperature =
                EXCLUDED.min_temperature,
            precipitation =
                EXCLUDED.precipitation,
            sunshine_duration =
                EXCLUDED.sunshine_duration,
            max_snow_depth =
                EXCLUDED.max_snow_depth,
            snowfall =
                EXCLUDED.snowfall,
            availability_mask =
                EXCLUDED.availability_mask,
            source_updated_at =
                EXCLUDED.source_updated_at,
            refreshed_at = now()
        WHERE ROW(
            target.mean_temperature,
            target.max_temperature,
            target.min_temperature,
            target.precipitation,
            target.sunshine_duration,
            target.max_snow_depth,
            target.snowfall,
            target.availability_mask,
            target.source_updated_at
        ) IS DISTINCT FROM ROW(
            EXCLUDED.mean_temperature,
            EXCLUDED.max_temperature,
            EXCLUDED.min_temperature,
            EXCLUDED.precipitation,
            EXCLUDED.sunshine_duration,
            EXCLUDED.max_snow_depth,
            EXCLUDED.snowfall,
            EXCLUDED.availability_mask,
            EXCLUDED.source_updated_at
        )
        RETURNING 1
    )
    SELECT count(*)
    FROM changed
"""


def sync_daily_climate_normals(
    connection: psycopg.Connection,
) -> ClimateNormalSyncCounts:
    connection.execute(
        CREATE_CLIMATE_NORMAL_STAGE
    )
    connection.execute(
        ADD_CLIMATE_NORMAL_STAGE_KEY
    )

    staged_row = connection.execute(
        COUNT_CLIMATE_NORMAL_STAGE
    ).fetchone()
    deleted_row = connection.execute(
        DELETE_STALE_CLIMATE_NORMALS
    ).fetchone()
    changed_row = connection.execute(
        UPSERT_CLIMATE_NORMALS
    ).fetchone()

    if (
        staged_row is None
        or deleted_row is None
        or changed_row is None
    ):
        raise RuntimeError(
            "Could not count L1 daily climate-normal "
            "changes."
        )

    return ClimateNormalSyncCounts(
        staged=int(staged_row[0]),
        changed=int(changed_row[0]),
        deleted=int(deleted_row[0]),
    )

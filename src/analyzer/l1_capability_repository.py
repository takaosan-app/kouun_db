from __future__ import annotations

import psycopg


DELETE_STALE_CAPABILITIES = """
    WITH latest_profile AS (
        SELECT DISTINCT ON (
            profile.station_id
        )
            profile.station_id,
            profile.capability_code
        FROM weather.jma_obsdl_station_profile AS profile
        JOIN weather.source_file AS source_file
            ON source_file.id = profile.source_file_id
        WHERE profile.station_id IS NOT NULL
        ORDER BY
            profile.station_id,
            source_file.retrieved_at DESC,
            profile.id DESC
    ),
    capability_elements (
        position,
        element_key
    ) AS (
        VALUES
            (1, 'daily_precipitation'),
            (2, 'daily_mean_wind_speed'),
            (2, 'daily_max_wind_speed'),
            (2, 'daily_max_wind_direction'),
            (2, 'daily_max_instantaneous_wind_speed'),
            (
                2,
                'daily_max_instantaneous_wind_direction'
            ),
            (
                2,
                'daily_most_frequent_wind_direction'
            ),
            (3, 'daily_mean_temperature'),
            (3, 'daily_max_temperature'),
            (3, 'daily_min_temperature'),
            (4, 'daily_sunshine_duration'),
            (5, 'daily_max_snow_depth'),
            (5, 'daily_snowfall'),
            (6, 'daily_mean_station_pressure'),
            (6, 'daily_mean_sea_level_pressure'),
            (6, 'daily_mean_relative_humidity'),
            (6, 'daily_min_relative_humidity')
    ),
    expected AS (
        SELECT
            profile.station_id,
            element.element_code
        FROM latest_profile AS profile
        CROSS JOIN capability_elements AS mapping
        JOIN analysis.weather_element AS element
            ON element.element_key = mapping.element_key
        WHERE substring(
            profile.capability_code
            FROM mapping.position
            FOR 1
        ) <> '0'
    )
    DELETE FROM analysis.station_element_capability
        AS target
    WHERE target.valid_from IS NULL
      AND NOT EXISTS (
          SELECT 1
          FROM expected
          WHERE expected.station_id =
              target.station_id
            AND expected.element_code =
              target.element_code
      )
    RETURNING 1
"""


INSERT_CAPABILITIES = """
    WITH latest_profile AS (
        SELECT DISTINCT ON (
            profile.station_id
        )
            profile.station_id,
            profile.capability_code,
            source_file.retrieved_at
        FROM weather.jma_obsdl_station_profile AS profile
        JOIN weather.source_file AS source_file
            ON source_file.id = profile.source_file_id
        WHERE profile.station_id IS NOT NULL
        ORDER BY
            profile.station_id,
            source_file.retrieved_at DESC,
            profile.id DESC
    ),
    capability_elements (
        position,
        element_key
    ) AS (
        VALUES
            (1, 'daily_precipitation'),
            (2, 'daily_mean_wind_speed'),
            (2, 'daily_max_wind_speed'),
            (2, 'daily_max_wind_direction'),
            (2, 'daily_max_instantaneous_wind_speed'),
            (
                2,
                'daily_max_instantaneous_wind_direction'
            ),
            (
                2,
                'daily_most_frequent_wind_direction'
            ),
            (3, 'daily_mean_temperature'),
            (3, 'daily_max_temperature'),
            (3, 'daily_min_temperature'),
            (4, 'daily_sunshine_duration'),
            (5, 'daily_max_snow_depth'),
            (5, 'daily_snowfall'),
            (6, 'daily_mean_station_pressure'),
            (6, 'daily_mean_sea_level_pressure'),
            (6, 'daily_mean_relative_humidity'),
            (6, 'daily_min_relative_humidity')
    )
    INSERT INTO analysis.station_element_capability
        AS target (
            station_id,
            element_code,
            valid_from,
            valid_to,
            source_updated_at
        )
    SELECT
        profile.station_id,
        element.element_code,
        NULL,
        NULL,
        profile.retrieved_at
    FROM latest_profile AS profile
    JOIN analysis.weather_station AS station
        ON station.station_id = profile.station_id
    CROSS JOIN capability_elements AS mapping
    JOIN analysis.weather_element AS element
        ON element.element_key = mapping.element_key
    WHERE substring(
        profile.capability_code
        FROM mapping.position
        FOR 1
    ) <> '0'
    ON CONFLICT (
        station_id,
        element_code,
        valid_from
    ) DO UPDATE
    SET
        source_updated_at =
            EXCLUDED.source_updated_at,
        refreshed_at = now()
    WHERE target.source_updated_at
        IS DISTINCT FROM EXCLUDED.source_updated_at
    RETURNING 1
"""


def sync_station_element_capabilities(
    connection: psycopg.Connection,
) -> tuple[int, int]:
    deleted_rows = connection.execute(
        DELETE_STALE_CAPABILITIES
    ).fetchall()

    inserted_or_updated_rows = connection.execute(
        INSERT_CAPABILITIES
    ).fetchall()

    return (
        len(inserted_or_updated_rows),
        len(deleted_rows),
    )

from __future__ import annotations

import psycopg


DELETE_STALE_STATION_AREAS = """
    DELETE FROM analysis.weather_station_area AS target
    WHERE NOT EXISTS (
        SELECT 1
        FROM weather.station_observation_area AS source
        WHERE source.station_id = target.station_id
          AND source.area_code = target.area_code
    )
    RETURNING 1
"""


INSERT_STATION_AREAS = """
    INSERT INTO analysis.weather_station_area (
        station_id,
        area_code
    )
    SELECT
        source.station_id,
        source.area_code
    FROM weather.station_observation_area AS source
    JOIN analysis.weather_station AS station
        ON station.station_id = source.station_id
    JOIN analysis.weather_area AS area
        ON area.area_code = source.area_code
    ON CONFLICT (
        station_id,
        area_code
    ) DO NOTHING
    RETURNING 1
"""


def sync_weather_station_areas(
    connection: psycopg.Connection,
) -> tuple[int, int]:
    deleted_rows = connection.execute(
        DELETE_STALE_STATION_AREAS
    ).fetchall()

    inserted_rows = connection.execute(
        INSERT_STATION_AREAS
    ).fetchall()

    return (
        len(inserted_rows),
        len(deleted_rows),
    )

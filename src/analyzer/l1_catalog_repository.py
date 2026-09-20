from __future__ import annotations

import psycopg


SYNC_WEATHER_AREAS = """
    INSERT INTO analysis.weather_area AS target (
        area_code,
        area_name
    )
    SELECT
        source.area_code,
        source.area_name
    FROM weather.observation_area AS source
    WHERE source.area_code <> '99'
    ON CONFLICT (area_code) DO UPDATE
    SET
        area_name = EXCLUDED.area_name
    WHERE target.area_name IS DISTINCT FROM EXCLUDED.area_name
    RETURNING 1
"""


def sync_weather_areas(
    connection: psycopg.Connection,
) -> int:
    rows = connection.execute(
        SYNC_WEATHER_AREAS
    ).fetchall()

    return len(rows)


SYNC_WEATHER_STATIONS = """
    WITH latest_version AS (
        SELECT DISTINCT ON (
            version.station_id
        )
            version.station_id,
            version.effective_from,
            version.station_type_code,
            version.name,
            version.kana_name,
            version.location,
            version.elevation_m,
            version.observation_started_on,
            version.created_at,
            source_file.retrieved_at
        FROM weather.station_version AS version
        JOIN weather.source_file AS source_file
            ON source_file.id = version.source_file_id
        ORDER BY
            version.station_id,
            version.effective_from DESC,
            version.id DESC
    ),
    obsdl_mapping AS (
        SELECT DISTINCT ON (
            mapping.station_id
        )
            mapping.station_id,
            mapping.source_station_id,
            mapping.created_at
        FROM weather.station_source_id AS mapping
        JOIN weather.source AS source
            ON source.id = mapping.source_id
        WHERE source.source_key = 'jma_obsdl'
        ORDER BY
            mapping.station_id,
            mapping.valid_to DESC NULLS FIRST,
            mapping.valid_from DESC NULLS FIRST,
            mapping.id DESC
    ),
    official_mapping AS (
        SELECT DISTINCT ON (
            mapping.station_id
        )
            mapping.station_id,
            mapping.source_station_id,
            mapping.created_at
        FROM weather.station_source_id AS mapping
        JOIN weather.source AS source
            ON source.id = mapping.source_id
        WHERE source.source_key = 'jma_amedas_master'
        ORDER BY
            mapping.station_id,
            mapping.valid_to DESC NULLS FIRST,
            mapping.valid_from DESC NULLS FIRST,
            mapping.id DESC
    ),
    latest_profile AS (
        SELECT DISTINCT ON (
            profile.station_id
        )
            profile.station_id,
            profile.observation_ended_on,
            profile.created_at
        FROM weather.jma_obsdl_station_profile AS profile
        JOIN weather.source_file AS source_file
            ON source_file.id = profile.source_file_id
        WHERE profile.station_id IS NOT NULL
        ORDER BY
            profile.station_id,
            source_file.retrieved_at DESC,
            profile.id DESC
    ),
    source_rows AS (
        SELECT
            station.id AS station_id,
            station.station_key,
            obsdl_mapping.source_station_id
                AS obsdl_station_id,
            official_mapping.source_station_id
                AS official_station_number,
            latest_version.name,
            latest_version.kana_name,
            latest_version.station_type_code,
            latest_version.location,
            CAST(
                ROUND(
                    latest_version.elevation_m * 10
                )
                AS integer
            ) AS elevation,
            latest_version.observation_started_on,
            latest_profile.observation_ended_on,
            latest_version.effective_from
                AS metadata_effective_from,
            GREATEST(
                latest_version.created_at,
                latest_version.retrieved_at,
                obsdl_mapping.created_at,
                official_mapping.created_at,
                latest_profile.created_at
            ) AS source_updated_at
        FROM weather.station AS station
        JOIN latest_version
            ON latest_version.station_id = station.id
        JOIN obsdl_mapping
            ON obsdl_mapping.station_id = station.id
        JOIN official_mapping
            ON official_mapping.station_id = station.id
        JOIN latest_profile
            ON latest_profile.station_id = station.id
    )
    INSERT INTO analysis.weather_station AS target (
        station_id,
        station_key,
        obsdl_station_id,
        official_station_number,
        name,
        kana_name,
        station_type_code,
        location,
        elevation,
        observation_started_on,
        observation_ended_on,
        metadata_effective_from,
        source_updated_at
    )
    SELECT
        station_id,
        station_key,
        obsdl_station_id,
        official_station_number,
        name,
        kana_name,
        station_type_code,
        location,
        elevation,
        observation_started_on,
        observation_ended_on,
        metadata_effective_from,
        source_updated_at
    FROM source_rows
    ON CONFLICT (station_id) DO UPDATE
    SET
        station_key = EXCLUDED.station_key,
        obsdl_station_id =
            EXCLUDED.obsdl_station_id,
        official_station_number =
            EXCLUDED.official_station_number,
        name = EXCLUDED.name,
        kana_name = EXCLUDED.kana_name,
        station_type_code =
            EXCLUDED.station_type_code,
        location = EXCLUDED.location,
        elevation = EXCLUDED.elevation,
        observation_started_on =
            EXCLUDED.observation_started_on,
        observation_ended_on =
            EXCLUDED.observation_ended_on,
        metadata_effective_from =
            EXCLUDED.metadata_effective_from,
        source_updated_at =
            EXCLUDED.source_updated_at,
        refreshed_at = now()
    WHERE (
        target.station_key,
        target.obsdl_station_id,
        target.official_station_number,
        target.name,
        target.kana_name,
        target.station_type_code,
        target.location,
        target.elevation,
        target.observation_started_on,
        target.observation_ended_on,
        target.metadata_effective_from,
        target.source_updated_at
    ) IS DISTINCT FROM (
        EXCLUDED.station_key,
        EXCLUDED.obsdl_station_id,
        EXCLUDED.official_station_number,
        EXCLUDED.name,
        EXCLUDED.kana_name,
        EXCLUDED.station_type_code,
        EXCLUDED.location,
        EXCLUDED.elevation,
        EXCLUDED.observation_started_on,
        EXCLUDED.observation_ended_on,
        EXCLUDED.metadata_effective_from,
        EXCLUDED.source_updated_at
    )
    RETURNING 1
"""


def sync_weather_stations(
    connection: psycopg.Connection,
) -> int:
    rows = connection.execute(
        SYNC_WEATHER_STATIONS
    ).fetchall()

    return len(rows)

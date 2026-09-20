from __future__ import annotations

import psycopg


SYNC_CLIMATE_NORMAL_RELEASES = """
    WITH source_rows AS (
        SELECT
            release.release_key,
            release.name,
            release.version,
            release.statistics_started_on,
            release.statistics_ended_on,
            release.applicable_from,
            release.applicable_to,
            release.published_on,
            COALESCE(
                MAX(series.updated_at),
                release.created_at
            ) AS source_updated_at
        FROM weather.climate_normal_release AS release
        LEFT JOIN weather.climate_normal_series AS series
            ON series.release_id = release.id
        GROUP BY
            release.id,
            release.release_key,
            release.name,
            release.version,
            release.statistics_started_on,
            release.statistics_ended_on,
            release.applicable_from,
            release.applicable_to,
            release.published_on,
            release.created_at
    ),
    changed AS (
        INSERT INTO analysis.climate_normal_release
            AS target (
                release_key,
                name,
                version,
                statistics_started_on,
                statistics_ended_on,
                applicable_from,
                applicable_to,
                published_on,
                source_updated_at
            )
        SELECT
            release_key,
            name,
            version,
            statistics_started_on,
            statistics_ended_on,
            applicable_from,
            applicable_to,
            published_on,
            source_updated_at
        FROM source_rows
        ON CONFLICT (release_key) DO UPDATE
        SET
            name = EXCLUDED.name,
            version = EXCLUDED.version,
            statistics_started_on =
                EXCLUDED.statistics_started_on,
            statistics_ended_on =
                EXCLUDED.statistics_ended_on,
            applicable_from =
                EXCLUDED.applicable_from,
            applicable_to =
                EXCLUDED.applicable_to,
            published_on =
                EXCLUDED.published_on,
            source_updated_at =
                EXCLUDED.source_updated_at,
            refreshed_at = now()
        WHERE ROW(
            target.name,
            target.version,
            target.statistics_started_on,
            target.statistics_ended_on,
            target.applicable_from,
            target.applicable_to,
            target.published_on,
            target.source_updated_at
        ) IS DISTINCT FROM ROW(
            EXCLUDED.name,
            EXCLUDED.version,
            EXCLUDED.statistics_started_on,
            EXCLUDED.statistics_ended_on,
            EXCLUDED.applicable_from,
            EXCLUDED.applicable_to,
            EXCLUDED.published_on,
            EXCLUDED.source_updated_at
        )
        RETURNING 1
    )
    SELECT count(*)
    FROM changed
"""


def sync_climate_normal_releases(
    connection: psycopg.Connection,
) -> int:
    row = connection.execute(
        SYNC_CLIMATE_NORMAL_RELEASES
    ).fetchone()

    if row is None:
        raise RuntimeError(
            "Could not count changed climate-normal "
            "releases."
        )

    return int(row[0])

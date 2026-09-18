from __future__ import annotations

from dataclasses import dataclass
import re

import psycopg


@dataclass(frozen=True, slots=True)
class StationCollectionTarget:
    station_id: int
    source_station_id: str
    station_key: str
    name: str
    capability_code: str


class StationCollectionTargetError(RuntimeError):
    pass


def list_station_collection_targets(
    connection: psycopg.Connection,
    area_code: str,
) -> tuple[StationCollectionTarget, ...]:
    if not re.fullmatch(r"\d{2}", area_code):
        raise ValueError(
            "Area code must contain two digits."
        )

    rows = connection.execute(
        """
        WITH latest_source_file AS (
            SELECT source_file.id
            FROM weather.source_file AS source_file
            JOIN weather.source AS source
                ON source.id = source_file.source_id
            WHERE source.source_key = 'jma_obsdl_station'
              AND EXISTS (
                  SELECT 1
                  FROM weather.jma_obsdl_station_profile
                      AS area_profile
                  WHERE area_profile.source_file_id =
                      source_file.id
                    AND area_profile.area_code = %s
              )
            ORDER BY
                source_file.retrieved_at DESC,
                source_file.id DESC
            LIMIT 1
        )
        SELECT
            station.id,
            profile.source_station_id,
            station.station_key,
            profile.name,
            profile.capability_code
        FROM weather.jma_obsdl_station_profile AS profile
        JOIN latest_source_file
            ON latest_source_file.id =
                profile.source_file_id
        JOIN weather.station AS station
            ON station.id = profile.station_id
        WHERE profile.observation_ended_on IS NULL
        ORDER BY profile.source_station_id
        """,
        (area_code,),
    ).fetchall()

    if not rows:
        raise StationCollectionTargetError(
            "No active stations were found for area "
            f"{area_code}."
        )

    return tuple(
        StationCollectionTarget(
            station_id=int(row[0]),
            source_station_id=str(row[1]),
            station_key=str(row[2]),
            name=str(row[3]),
            capability_code=str(row[4]),
        )
        for row in rows
    )

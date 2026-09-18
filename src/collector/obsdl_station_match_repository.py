from __future__ import annotations

import psycopg

from collector.models import ObsdlStationRecord

NAME_MATCH_DISTANCE_METERS = 1000
LOCATION_ONLY_DISTANCE_METERS = 100


class ObsdlStationMatchError(RuntimeError):
    pass


def match_active_station(
    connection: psycopg.Connection,
    station: ObsdlStationRecord,
) -> int:
    station_ids = _find_station_ids(
        connection,
        station=station,
        required_name=station.name,
        distance_meters=NAME_MATCH_DISTANCE_METERS,
    )

    if len(station_ids) == 1:
        return station_ids[0]

    if len(station_ids) > 1:
        raise ObsdlStationMatchError(
            "Active station matched multiple logical "
            f"stations by name: {station.name} "
            f"({station.source_station_id})"
        )

    station_ids = _find_station_ids(
        connection,
        station=station,
        required_name=None,
        distance_meters=LOCATION_ONLY_DISTANCE_METERS,
    )

    if not station_ids:
        raise ObsdlStationMatchError(
            "Active station could not be matched: "
            f"{station.name} "
            f"({station.source_station_id})"
        )

    if len(station_ids) > 1:
        raise ObsdlStationMatchError(
            "Active station matched multiple logical "
            "stations by location: "
            f"{station.name} "
            f"({station.source_station_id})"
        )

    return station_ids[0]


def _find_station_ids(
    connection: psycopg.Connection,
    *,
    station: ObsdlStationRecord,
    required_name: str | None,
    distance_meters: int,
) -> tuple[int, ...]:
    rows = connection.execute(
        """
        SELECT DISTINCT logical_station.id
        FROM weather.station AS logical_station
        JOIN weather.station_version AS version
            ON version.station_id = logical_station.id
        WHERE version.effective_to IS NULL
          AND (
              %s::text IS NULL
              OR version.name = %s
          )
          AND ST_DWithin(
              version.location,
              ST_SetSRID(
                  ST_MakePoint(%s, %s),
                  4326
              )::geography,
              %s
          )
        """,
        (
            required_name,
            required_name,
            station.longitude,
            station.latitude,
            distance_meters,
        ),
    ).fetchall()

    return tuple(
        int(row[0])
        for row in rows
    )

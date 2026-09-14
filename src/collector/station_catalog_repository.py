from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass

import psycopg

from collector.models import AmedasStationRecord

SOURCE_KEY = "jma_amedas_master"

STATION_KEY_OVERRIDES = {
    "50331": "shizuoka",
}


class StationCatalogError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class StationCatalogIds:
    source_id: int
    station_ids: dict[str, int]


def resolve_station_catalog(
    connection: psycopg.Connection,
    stations: Collection[AmedasStationRecord],
) -> StationCatalogIds:
    source_id = _resolve_source_id(connection)
    logical_stations = _group_logical_stations(stations)
    station_ids: dict[str, int] = {}

    for official_number, station in sorted(
        logical_stations.items()
    ):
        station_id = _resolve_existing_station_id(
            connection,
            source_id,
            official_number,
        )

        if station_id is None:
            station_id = _create_station_mapping(
                connection,
                source_id,
                station,
            )
        else:
            connection.execute(
                """
                UPDATE weather.station
                SET name = %s
                WHERE id = %s
                """,
                (
                    station.name,
                    station_id,
                ),
            )

        station_ids[official_number] = station_id

    return StationCatalogIds(
        source_id=source_id,
        station_ids=station_ids,
    )


def _resolve_source_id(
    connection: psycopg.Connection,
) -> int:
    row = connection.execute(
        """
        SELECT id
        FROM weather.source
        WHERE source_key = %s
        """,
        (SOURCE_KEY,),
    ).fetchone()

    if row is None:
        raise StationCatalogError(
            f"Source is not registered: {SOURCE_KEY}"
        )

    return int(row[0])


def _group_logical_stations(
    stations: Collection[AmedasStationRecord],
) -> dict[str, AmedasStationRecord]:
    result: dict[str, AmedasStationRecord] = {}

    for station in stations:
        existing = result.get(
            station.official_station_number
        )

        if existing is not None and (
            existing.name != station.name
            or existing.area_name != station.area_name
        ):
            raise StationCatalogError(
                "Conflicting rows for official station "
                f"{station.official_station_number}"
            )

        result[station.official_station_number] = station

    if not result:
        raise StationCatalogError(
            "No station records were supplied."
        )

    return result


def _resolve_existing_station_id(
    connection: psycopg.Connection,
    source_id: int,
    official_number: str,
) -> int | None:
    rows = connection.execute(
        """
        SELECT station_id
        FROM weather.station_source_id
        WHERE source_id = %s
          AND source_station_id = %s
          AND valid_from IS NULL
          AND valid_to IS NULL
        """,
        (
            source_id,
            official_number,
        ),
    ).fetchall()

    if len(rows) > 1:
        raise StationCatalogError(
            "Station mapping is not unique: "
            f"{official_number}"
        )

    if not rows:
        return None

    return int(rows[0][0])


def _create_station_mapping(
    connection: psycopg.Connection,
    source_id: int,
    station: AmedasStationRecord,
) -> int:
    station_key = STATION_KEY_OVERRIDES.get(
        station.official_station_number,
        f"amedas_{station.official_station_number}",
    )

    row = connection.execute(
        """
        INSERT INTO weather.station (
            station_key,
            name
        )
        VALUES (%s, %s)
        ON CONFLICT (station_key) DO UPDATE
        SET name = EXCLUDED.name
        RETURNING id
        """,
        (
            station_key,
            station.name,
        ),
    ).fetchone()

    if row is None:
        raise StationCatalogError(
            "Could not create logical station: "
            f"{station.official_station_number}"
        )

    station_id = int(row[0])

    connection.execute(
        """
        INSERT INTO weather.station_source_id (
            source_id,
            station_id,
            source_station_id
        )
        VALUES (%s, %s, %s)
        ON CONFLICT (
            source_id,
            source_station_id,
            valid_from
        ) DO UPDATE
        SET station_id = EXCLUDED.station_id
        """,
        (
            source_id,
            station_id,
            station.official_station_number,
        ),
    )

    return station_id
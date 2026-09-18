from __future__ import annotations

from dataclasses import dataclass

import psycopg

from collector.models import (
    ObsdlStationRecord,
    ParsedObsdlStationPage,
)

from collector.observation_area_repository import (
    assign_station_observation_area,
)
from collector.obsdl_station_match_repository import (
    match_active_station,
)

OBSERVATION_SOURCE_KEY = "jma_obsdl"


class ObsdlStationCatalogError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ObsdlStationCatalog:
    observation_source_id: int
    station_ids: dict[str, int | None]


def resolve_obsdl_station_catalog(
    connection: psycopg.Connection,
    page: ParsedObsdlStationPage,
) -> ObsdlStationCatalog:
    _require_observation_area(
        connection,
        page.area_code,
    )

    source_id = _resolve_observation_source_id(
        connection
    )
    station_ids: dict[str, int | None] = {}

    for station in page.stations:
        if station.observation_ended_on is not None:
            station_ids[station.source_station_id] = (
                _resolve_ended_station_id(
                    connection,
                    source_id,
                    station,
                )
            )
            continue

        station_id = match_active_station(
            connection,
            station,
        )
        assign_station_observation_area(
            connection,
            station_id=station_id,
            area_code=page.area_code,
        )
        _register_observation_mapping(
            connection,
            source_id,
            station_id,
            station.source_station_id,
        )
        station_ids[station.source_station_id] = station_id

    return ObsdlStationCatalog(
        observation_source_id=source_id,
        station_ids=station_ids,
    )


def _require_observation_area(
    connection: psycopg.Connection,
    area_code: str,
) -> None:
    row = connection.execute(
        """
        SELECT true
        FROM weather.observation_area
        WHERE area_code = %s
        """,
        (area_code,),
    ).fetchone()

    if row is None:
        raise ObsdlStationCatalogError(
            "Observation area is not registered: "
            f"{area_code}"
        )


def _resolve_observation_source_id(
    connection: psycopg.Connection,
) -> int:
    row = connection.execute(
        """
        SELECT id
        FROM weather.source
        WHERE source_key = %s
        """,
        (OBSERVATION_SOURCE_KEY,),
    ).fetchone()

    if row is None:
        raise ObsdlStationCatalogError(
            "Observation source is not registered: "
            f"{OBSERVATION_SOURCE_KEY}"
        )

    return int(row[0])


def _resolve_ended_station_id(
    connection: psycopg.Connection,
    source_id: int,
    station: ObsdlStationRecord,
) -> int | None:
    ended_on = station.observation_ended_on

    if ended_on is None:
        raise ObsdlStationCatalogError(
            "Ended station has no end date."
        )

    rows = connection.execute(
        """
        SELECT
            id,
            station_id
        FROM weather.station_source_id
        WHERE source_id = %s
          AND source_station_id = %s
          AND valid_from IS NULL
        """,
        (
            source_id,
            station.source_station_id,
        ),
    ).fetchall()

    if len(rows) > 1:
        raise ObsdlStationCatalogError(
            "Ended station mapping is not unique: "
            f"{station.source_station_id}"
        )

    if not rows:
        return None

    mapping_id, station_id = rows[0]

    connection.execute(
        """
        UPDATE weather.station_source_id
        SET valid_to = %s
        WHERE id = %s
          AND (
              valid_to IS NULL
              OR valid_to > %s
          )
        """,
        (
            ended_on,
            mapping_id,
            ended_on,
        ),
    )

    return int(station_id)


def _register_observation_mapping(
    connection: psycopg.Connection,
    source_id: int,
    station_id: int,
    source_station_id: str,
) -> None:
    row = connection.execute(
        """
        INSERT INTO weather.station_source_id AS mapping (
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
        SET
            station_id = EXCLUDED.station_id,
            valid_to = NULL
        WHERE mapping.station_id = EXCLUDED.station_id
        RETURNING id
        """,
        (
            source_id,
            station_id,
            source_station_id,
        ),
    ).fetchone()

    if row is None:
        raise ObsdlStationCatalogError(
            "Download station ID is already mapped to "
            "another logical station: "
            f"{source_station_id}"
        )

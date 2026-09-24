from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass

import psycopg

from collector.models import ObservationSourceFileRecord


class CatalogNotFoundError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class CatalogIds:
    source_id: int
    station_id: int
    station_name: str
    element_ids: dict[str, int]


def resolve_catalog_ids(
    connection: psycopg.Connection,
    source_file: ObservationSourceFileRecord,
    element_keys: Collection[str],
) -> CatalogIds:
    source_and_station = connection.execute(
        """
        SELECT
            source.id,
            station.id,
            station.name
        FROM weather.source
        JOIN weather.station_source_id
            ON station_source_id.source_id = source.id
        JOIN weather.station
            ON station.id = station_source_id.station_id
        WHERE source.source_key = %s
          AND station.station_key = %s
          AND station_source_id.source_station_id = %s
          AND (
              station_source_id.valid_from IS NULL
              OR %s IS NULL
              OR station_source_id.valid_from <= %s
          )
          AND (
              station_source_id.valid_to IS NULL
              OR %s IS NULL
              OR station_source_id.valid_to >= %s
          )
        """,
        (
            source_file.source_key,
            source_file.station_key,
            source_file.source_station_id,
            source_file.requested_start_date,
            source_file.requested_start_date,
            source_file.requested_end_date,
            source_file.requested_end_date,
        ),
    ).fetchall()

    if len(source_and_station) != 1:
        raise CatalogNotFoundError(
            "Source and station mapping was not uniquely resolved: "
            f"{source_file.source_key} / "
            f"{source_file.station_key} / "
            f"{source_file.source_station_id}"
        )

    requested_elements = sorted(set(element_keys))

    if not requested_elements:
        raise CatalogNotFoundError(
            "No observation elements were supplied."
        )

    element_rows = connection.execute(
        """
        SELECT
            element_key,
            id
        FROM weather.element
        WHERE element_key = ANY(%s)
        """,
        (requested_elements,),
    ).fetchall()

    element_ids = {
        str(element_key): int(element_id)
        for element_key, element_id in element_rows
    }

    missing_elements = set(requested_elements) - element_ids.keys()

    if missing_elements:
        raise CatalogNotFoundError(
            "Elements are not registered: "
            + ", ".join(sorted(missing_elements))
        )

    source_id, station_id, station_name = source_and_station[0]

    return CatalogIds(
        source_id=int(source_id),
        station_id=int(station_id),
        station_name=str(station_name),
        element_ids=element_ids,
    )


def resolve_station_id(
    connection: psycopg.Connection,
    *,
    station_key: str,
) -> int:
    row = connection.execute(
        """
        SELECT id
        FROM weather.station
        WHERE station_key = %s
        """,
        (station_key,),
    ).fetchone()

    if row is None:
        raise CatalogNotFoundError(
            f"Station was not found: {station_key}"
        )

    return int(row[0])

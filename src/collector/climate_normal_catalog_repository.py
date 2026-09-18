from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass

import psycopg


@dataclass(frozen=True, slots=True)
class ClimateNormalCatalog:
    release_id: int
    element_ids: dict[str, int]
    station_ids: dict[str, int]


def resolve_climate_normal_catalog(
    connection: psycopg.Connection,
    *,
    release_key: str,
    element_keys: Collection[str],
) -> ClimateNormalCatalog:
    release_row = connection.execute(
        """
        SELECT id
        FROM weather.climate_normal_release
        WHERE release_key = %s
        """,
        (release_key,),
    ).fetchone()

    if release_row is None:
        raise RuntimeError(
            f"Climate-normal release is not "
            f"registered: {release_key}"
        )

    element_rows = connection.execute(
        """
        SELECT
            element.element_key,
            element.id
        FROM weather.element
        WHERE element.element_key = ANY(%s)
        """,
        (list(element_keys),),
    ).fetchall()

    element_ids = {
        str(row[0]): int(row[1])
        for row in element_rows
    }
    missing_elements = set(element_keys) - set(
        element_ids
    )

    if missing_elements:
        missing_text = ", ".join(
            sorted(missing_elements)
        )
        raise RuntimeError(
            f"Climate-normal elements are not "
            f"registered: {missing_text}"
        )

    station_rows = connection.execute(
        """
        SELECT
            station_source_id.source_station_id,
            station_source_id.station_id
        FROM weather.station_source_id
        JOIN weather.source
          ON source.id = station_source_id.source_id
        WHERE source.source_key = 'jma_amedas_master'
        ORDER BY
            station_source_id.source_station_id,
            station_source_id.valid_from DESC
                NULLS LAST
        """
    ).fetchall()

    station_ids: dict[str, int] = {}

    for row in station_rows:
        source_station_id = str(row[0])
        station_id = int(row[1])
        existing_station_id = station_ids.get(
            source_station_id
        )

        if (
            existing_station_id is not None
            and existing_station_id != station_id
        ):
            raise RuntimeError(
                "Official station number maps to "
                "multiple logical stations: "
                f"{source_station_id}"
            )

        station_ids[source_station_id] = station_id

    return ClimateNormalCatalog(
        release_id=int(release_row[0]),
        element_ids=element_ids,
        station_ids=station_ids,
    )

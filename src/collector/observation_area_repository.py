from __future__ import annotations

from dataclasses import dataclass

import psycopg


class ObservationAreaError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ObservationAreaTarget:
    area_code: str
    area_name: str


def list_domestic_observation_areas(
    connection: psycopg.Connection,
) -> tuple[ObservationAreaTarget, ...]:
    rows = connection.execute(
        """
        SELECT
            area_code,
            area_name
        FROM weather.observation_area
        WHERE area_code <> '99'
        ORDER BY area_code
        """
    ).fetchall()

    if not rows:
        raise ObservationAreaError(
            "No domestic observation areas were found."
        )

    return tuple(
        ObservationAreaTarget(
            area_code=str(row[0]),
            area_name=str(row[1]),
        )
        for row in rows
    )


def register_observation_area(
    connection: psycopg.Connection,
    *,
    area_code: str,
    area_name: str,
) -> None:
    row = connection.execute(
        """
        INSERT INTO weather.observation_area (
            area_code,
            area_name
        )
        VALUES (%s, %s)
        ON CONFLICT (area_code) DO UPDATE
        SET area_name = EXCLUDED.area_name
        WHERE observation_area.area_name =
            EXCLUDED.area_name
        RETURNING area_code
        """,
        (
            area_code,
            area_name,
        ),
    ).fetchone()

    if row is None:
        raise ObservationAreaError(
            "Area code is already registered with "
            f"another name: {area_code}"
        )


def assign_station_observation_area(
    connection: psycopg.Connection,
    *,
    station_id: int,
    area_code: str,
) -> None:
    connection.execute(
        """
        INSERT INTO weather.station_observation_area (
            station_id,
            area_code
        )
        VALUES (%s, %s)
        ON CONFLICT (
            station_id,
            area_code
        ) DO NOTHING
        """,
        (
            station_id,
            area_code,
        ),
    )

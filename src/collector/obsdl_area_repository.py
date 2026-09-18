from __future__ import annotations

from dataclasses import dataclass

import psycopg

from collector.models import ParsedObsdlAreaPage
from collector.observation_area_repository import (
    register_observation_area,
)


@dataclass(frozen=True, slots=True)
class ObsdlAreaCounts:
    parsed: int
    inserted: int
    updated: int
    unchanged: int


def upsert_obsdl_areas(
    connection: psycopg.Connection,
    page: ParsedObsdlAreaPage,
) -> ObsdlAreaCounts:
    existing_by_code = {
        str(row[0]): str(row[1])
        for row in connection.execute(
            """
            SELECT
                area_code,
                area_name
            FROM weather.observation_area
            """
        ).fetchall()
    }

    inserted = 0
    unchanged = 0

    for area in page.areas:
        existing_name = existing_by_code.get(
            area.area_code
        )

        register_observation_area(
            connection,
            area_code=area.area_code,
            area_name=area.area_name,
        )

        if existing_name is None:
            inserted += 1
        else:
            unchanged += 1

    return ObsdlAreaCounts(
        parsed=len(page.areas),
        inserted=inserted,
        updated=0,
        unchanged=unchanged,
    )

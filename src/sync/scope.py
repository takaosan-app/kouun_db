from __future__ import annotations

import psycopg

# JMA observation-area codes for the initial app release:
# Tokyo, Kanagawa, Nagano, Yamanashi, Shizuoka, Aichi.
TARGET_AREA_CODES = ("44", "46", "48", "49", "50", "51")

TARGET_STATIONS_QUERY = """
    SELECT DISTINCT station_id
    FROM analysis.weather_station_area
    WHERE area_code = ANY(%s)
    ORDER BY station_id
"""


def fetch_target_station_ids(
    connection: psycopg.Connection,
) -> list[int]:
    rows = connection.execute(
        TARGET_STATIONS_QUERY,
        (list(TARGET_AREA_CODES),),
    ).fetchall()

    return [row[0] for row in rows]

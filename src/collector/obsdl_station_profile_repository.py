from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import psycopg
from psycopg.types.json import Jsonb

from collector.models import (
    ObsdlStationRecord,
    ParsedObsdlStationPage,
)
from collector.obsdl_station_catalog_repository import (
    ObsdlStationCatalog,
)

UpsertState = Literal[
    "inserted",
    "updated",
    "unchanged",
]


@dataclass(frozen=True, slots=True)
class ObsdlStationProfileCounts:
    parsed: int
    inserted: int
    updated: int
    unchanged: int
    matched: int
    unmatched: int


def upsert_obsdl_station_profiles(
    connection: psycopg.Connection,
    *,
    source_file_id: int,
    page: ParsedObsdlStationPage,
    catalog: ObsdlStationCatalog,
) -> ObsdlStationProfileCounts:
    source_ids = {
        station.source_station_id
        for station in page.stations
    }

    if source_ids != catalog.station_ids.keys():
        raise RuntimeError(
            "Station profile and catalog IDs do not match."
        )

    inserted = 0
    updated = 0
    unchanged = 0

    for station in page.stations:
        station_id = catalog.station_ids[
            station.source_station_id
        ]
        state = _upsert_station_profile(
            connection,
            source_file_id=source_file_id,
            station_id=station_id,
            station=station,
        )

        if state == "inserted":
            inserted += 1
        elif state == "updated":
            updated += 1
        else:
            unchanged += 1

    matched = sum(
        station_id is not None
        for station_id in catalog.station_ids.values()
    )

    return ObsdlStationProfileCounts(
        parsed=len(page.stations),
        inserted=inserted,
        updated=updated,
        unchanged=unchanged,
        matched=matched,
        unmatched=len(page.stations) - matched,
    )


def _upsert_station_profile(
    connection: psycopg.Connection,
    *,
    source_file_id: int,
    station_id: int | None,
    station: ObsdlStationRecord,
) -> UpsertState:
    existed = (
        connection.execute(
            """
            SELECT true
            FROM weather.jma_obsdl_station_profile
            WHERE source_file_id = %s
              AND source_station_id = %s
            """,
            (
                source_file_id,
                station.source_station_id,
            ),
        ).fetchone()
        is not None
    )

    cursor = connection.execute(
        """
        INSERT INTO weather.jma_obsdl_station_profile (
            source_file_id,
            station_id,
            source_station_id,
            area_code,
            name,
            kana_name,
            capability_code,
            location,
            elevation_m,
            observation_ended_on,
            raw_record
        )
        VALUES (
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            ST_SetSRID(
                ST_MakePoint(%s, %s),
                4326
            )::geography,
            %s,
            %s,
            %s
        )
        ON CONFLICT (
            source_file_id,
            source_station_id
        ) DO UPDATE
        SET
            station_id = EXCLUDED.station_id,
            area_code =
                EXCLUDED.area_code,
            name = EXCLUDED.name,
            kana_name = EXCLUDED.kana_name,
            capability_code =
                EXCLUDED.capability_code,
            location = EXCLUDED.location,
            elevation_m = EXCLUDED.elevation_m,
            observation_ended_on =
                EXCLUDED.observation_ended_on,
            raw_record = EXCLUDED.raw_record
        WHERE (
            jma_obsdl_station_profile.station_id,
            jma_obsdl_station_profile.area_code,
            jma_obsdl_station_profile.name,
            jma_obsdl_station_profile.kana_name,
            jma_obsdl_station_profile.capability_code,
            jma_obsdl_station_profile.location,
            jma_obsdl_station_profile.elevation_m,
            jma_obsdl_station_profile.observation_ended_on,
            jma_obsdl_station_profile.raw_record
        ) IS DISTINCT FROM (
            EXCLUDED.station_id,
            EXCLUDED.area_code,
            EXCLUDED.name,
            EXCLUDED.kana_name,
            EXCLUDED.capability_code,
            EXCLUDED.location,
            EXCLUDED.elevation_m,
            EXCLUDED.observation_ended_on,
            EXCLUDED.raw_record
        )
        RETURNING id
        """,
        (
            source_file_id,
            station_id,
            station.source_station_id,
            station.area_code,
            station.name,
            station.kana_name,
            station.capability_code,
            station.longitude,
            station.latitude,
            station.elevation_m,
            station.observation_ended_on,
            Jsonb(station.raw_record),
        ),
    )

    changed = cursor.fetchone() is not None

    if not existed:
        return "inserted"

    if changed:
        return "updated"

    return "unchanged"
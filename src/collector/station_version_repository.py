from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass
from datetime import date
from typing import Literal

import psycopg
from psycopg.types.json import Jsonb

from collector.models import AmedasStationRecord
from collector.station_catalog_repository import StationCatalogIds

UpsertState = Literal[
    "inserted",
    "updated",
    "unchanged",
]


@dataclass(frozen=True, slots=True)
class StationVersionCounts:
    parsed: int
    inserted: int
    updated: int
    unchanged: int
    closed: int


def upsert_station_versions(
    connection: psycopg.Connection,
    *,
    source_file_id: int,
    effective_on: date,
    stations: Collection[AmedasStationRecord],
    catalog: StationCatalogIds,
) -> StationVersionCounts:
    closed = _close_previous_versions(
        connection,
        catalog.source_id,
        effective_on,
    )
    inserted = 0
    updated = 0
    unchanged = 0

    for station in stations:
        station_id = catalog.station_ids.get(
            station.official_station_number
        )

        if station_id is None:
            raise RuntimeError(
                "Logical station was not resolved: "
                f"{station.official_station_number}"
            )

        state = _upsert_station_version(
            connection,
            source_file_id=source_file_id,
            station_id=station_id,
            effective_on=effective_on,
            station=station,
        )

        if state == "inserted":
            inserted += 1
        elif state == "updated":
            updated += 1
        else:
            unchanged += 1

    return StationVersionCounts(
        parsed=len(stations),
        inserted=inserted,
        updated=updated,
        unchanged=unchanged,
        closed=closed,
    )


def _close_previous_versions(
    connection: psycopg.Connection,
    source_id: int,
    effective_on: date,
) -> int:
    cursor = connection.execute(
        """
        UPDATE weather.station_version AS version
        SET effective_to = %s - 1
        FROM weather.station_source_id AS mapping
        WHERE mapping.station_id = version.station_id
          AND mapping.source_id = %s
          AND version.effective_from < %s
          AND (
              version.effective_to IS NULL
              OR version.effective_to >= %s
          )
        """,
        (
            effective_on,
            source_id,
            effective_on,
            effective_on,
        ),
    )

    return cursor.rowcount


def _upsert_station_version(
    connection: psycopg.Connection,
    *,
    source_file_id: int,
    station_id: int,
    effective_on: date,
    station: AmedasStationRecord,
) -> UpsertState:
    existed = (
        connection.execute(
            """
            SELECT true
            FROM weather.station_version
            WHERE station_id = %s
              AND effective_from = %s
              AND source_row_number = %s
            """,
            (
                station_id,
                effective_on,
                station.source_row_number,
            ),
        ).fetchone()
        is not None
    )

    cursor = connection.execute(
        """
        INSERT INTO weather.station_version (
            station_id,
            source_file_id,
            source_row_number,
            effective_from,
            station_type_code,
            name,
            kana_name,
            information_name,
            address,
            area_name,
            location,
            elevation_m,
            wind_sensor_height_m,
            temperature_sensor_height_m,
            observation_started_on,
            observation_start_raw,
            remarks_1,
            remarks_2,
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
            %s,
            %s,
            %s,
            ST_SetSRID(
                ST_MakePoint(%s, %s),
                4326
            )::geography,
            %s,
            %s,
            %s,
            NULL,
            %s,
            %s,
            %s,
            %s
        )
        ON CONFLICT (
            station_id,
            effective_from,
            source_row_number
        ) DO UPDATE
        SET
            source_file_id = EXCLUDED.source_file_id,
            station_type_code = EXCLUDED.station_type_code,
            name = EXCLUDED.name,
            kana_name = EXCLUDED.kana_name,
            information_name = EXCLUDED.information_name,
            address = EXCLUDED.address,
            area_name = EXCLUDED.area_name,
            location = EXCLUDED.location,
            elevation_m = EXCLUDED.elevation_m,
            wind_sensor_height_m =
                EXCLUDED.wind_sensor_height_m,
            temperature_sensor_height_m =
                EXCLUDED.temperature_sensor_height_m,
            observation_started_on =
                EXCLUDED.observation_started_on,
            observation_start_raw =
                EXCLUDED.observation_start_raw,
            remarks_1 = EXCLUDED.remarks_1,
            remarks_2 = EXCLUDED.remarks_2,
            raw_record = EXCLUDED.raw_record
        WHERE (
            station_version.source_file_id,
            station_version.station_type_code,
            station_version.name,
            station_version.kana_name,
            station_version.information_name,
            station_version.address,
            station_version.area_name,
            station_version.location,
            station_version.elevation_m,
            station_version.wind_sensor_height_m,
            station_version.temperature_sensor_height_m,
            station_version.observation_started_on,
            station_version.observation_start_raw,
            station_version.remarks_1,
            station_version.remarks_2,
            station_version.raw_record
        ) IS DISTINCT FROM (
            EXCLUDED.source_file_id,
            EXCLUDED.station_type_code,
            EXCLUDED.name,
            EXCLUDED.kana_name,
            EXCLUDED.information_name,
            EXCLUDED.address,
            EXCLUDED.area_name,
            EXCLUDED.location,
            EXCLUDED.elevation_m,
            EXCLUDED.wind_sensor_height_m,
            EXCLUDED.temperature_sensor_height_m,
            EXCLUDED.observation_started_on,
            EXCLUDED.observation_start_raw,
            EXCLUDED.remarks_1,
            EXCLUDED.remarks_2,
            EXCLUDED.raw_record
        )
        RETURNING id
        """,
        (
            station_id,
            source_file_id,
            station.source_row_number,
            effective_on,
            station.station_type_code,
            station.name,
            station.kana_name,
            station.information_name,
            station.address,
            station.area_name,
            station.longitude,
            station.latitude,
            station.elevation_m,
            station.wind_sensor_height_m,
            station.temperature_sensor_height_m,
            station.observation_start_raw,
            station.remarks_1,
            station.remarks_2,
            Jsonb(station.raw_record),
        ),
    )

    changed = cursor.fetchone() is not None

    if not existed:
        return "inserted"

    if changed:
        return "updated"

    return "unchanged"
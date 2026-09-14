from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass

import psycopg
from psycopg.types.json import Jsonb

from collector.catalog_repository import CatalogIds
from collector.models import ObservationRecord


@dataclass(frozen=True, slots=True)
class UpsertCounts:
    parsed: int
    inserted: int
    updated: int
    unchanged: int

    @property
    def revisions(self) -> int:
        return self.updated


def upsert_observations(
    connection: psycopg.Connection,
    source_file_id: int,
    catalog: CatalogIds,
    observations: Collection[ObservationRecord],
) -> UpsertCounts:
    inserted = 0
    updated = 0
    unchanged = 0

    for record in observations:
        element_id = catalog.element_ids[record.element_key]
        existing = _find_existing(
            connection,
            catalog,
            element_id,
            record,
        )

        if existing is None:
            _insert_observation(
                connection,
                source_file_id,
                catalog,
                element_id,
                record,
            )
            inserted += 1
            continue

        observation_id = int(existing[0])
        previous_source_file_id = int(existing[1])
        previous_values = tuple(existing[2:])
        replacement_values = _record_values(record)

        if previous_values == replacement_values:
            unchanged += 1
            continue

        _replace_observation(
            connection=connection,
            observation_id=observation_id,
            previous_source_file_id=previous_source_file_id,
            replacement_source_file_id=source_file_id,
            previous_values=previous_values,
            replacement_values=replacement_values,
        )
        updated += 1

    return UpsertCounts(
        parsed=len(observations),
        inserted=inserted,
        updated=updated,
        unchanged=unchanged,
    )


def _find_existing(
    connection: psycopg.Connection,
    catalog: CatalogIds,
    element_id: int,
    record: ObservationRecord,
) -> tuple[object, ...] | None:
    return connection.execute(
        """
        SELECT
            id,
            source_file_id,
            value,
            text_value,
            raw_value,
            value_state,
            quality_code,
            homogeneity_number,
            no_phenomenon
        FROM weather.observation
        WHERE source_id = %s
          AND station_id = %s
          AND element_id = %s
          AND granularity = 'daily'
          AND observed_on = %s
        FOR UPDATE
        """,
        (
            catalog.source_id,
            catalog.station_id,
            element_id,
            record.observed_on,
        ),
    ).fetchone()


def _insert_observation(
    connection: psycopg.Connection,
    source_file_id: int,
    catalog: CatalogIds,
    element_id: int,
    record: ObservationRecord,
) -> None:
    connection.execute(
        """
        INSERT INTO weather.observation (
            source_id,
            station_id,
            element_id,
            source_file_id,
            granularity,
            observed_on,
            value,
            text_value,
            raw_value,
            value_state,
            quality_code,
            homogeneity_number,
            no_phenomenon
        )
        VALUES (
            %s, %s, %s, %s, 'daily', %s,
            %s, %s, %s, %s, %s, %s, %s
        )
        """,
        (
            catalog.source_id,
            catalog.station_id,
            element_id,
            source_file_id,
            record.observed_on,
            *_record_values(record),
        ),
    )


def _replace_observation(
    *,
    connection: psycopg.Connection,
    observation_id: int,
    previous_source_file_id: int,
    replacement_source_file_id: int,
    previous_values: tuple[object, ...],
    replacement_values: tuple[object, ...],
) -> None:
    connection.execute(
        """
        INSERT INTO weather.observation_revision (
            observation_id,
            previous_source_file_id,
            replacement_source_file_id,
            previous_record,
            replacement_record
        )
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            observation_id,
            previous_source_file_id,
            replacement_source_file_id,
            Jsonb(_snapshot(previous_values)),
            Jsonb(_snapshot(replacement_values)),
        ),
    )

    connection.execute(
        """
        UPDATE weather.observation
        SET
            source_file_id = %s,
            value = %s,
            text_value = %s,
            raw_value = %s,
            value_state = %s,
            quality_code = %s,
            homogeneity_number = %s,
            no_phenomenon = %s,
            updated_at = now()
        WHERE id = %s
        """,
        (
            replacement_source_file_id,
            *replacement_values,
            observation_id,
        ),
    )


def _record_values(
    record: ObservationRecord,
) -> tuple[object, ...]:
    return (
        record.value,
        record.text_value,
        record.raw_value,
        record.value_state,
        record.quality_code,
        record.homogeneity_number,
        record.no_phenomenon,
    )


def _snapshot(
    values: tuple[object, ...],
) -> dict[str, object]:
    keys = (
        "value",
        "text_value",
        "raw_value",
        "value_state",
        "quality_code",
        "homogeneity_number",
        "no_phenomenon",
    )

    snapshot = dict(zip(keys, values, strict=True))
    value = snapshot["value"]

    if value is not None:
        snapshot["value"] = str(value)

    return snapshot
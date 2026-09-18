from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import psycopg

from collector.climate_normal_catalog_repository import (
    ClimateNormalCatalog,
)
from collector.models import ClimateNormalSeriesRecord


@dataclass(frozen=True, slots=True)
class ClimateNormalCounts:
    parsed: int
    inserted: int
    updated: int
    unchanged: int


def upsert_climate_normal_series(
    connection: psycopg.Connection,
    *,
    source_file_id: int,
    catalog: ClimateNormalCatalog,
    series: Iterable[ClimateNormalSeriesRecord],
) -> ClimateNormalCounts:
    connection.execute(
        """
        CREATE TEMPORARY TABLE climate_normal_stage (
            release_id bigint NOT NULL,
            source_file_id bigint NOT NULL,
            station_id bigint,
            element_id bigint NOT NULL,
            source_station_id text NOT NULL,
            source_element_code text NOT NULL,
            month smallint NOT NULL,
            material_years smallint NOT NULL,
            statistics_started_year smallint,
            statistics_ended_year smallint,
            daily_values numeric[] NOT NULL,
            daily_remarks smallint[] NOT NULL,

            PRIMARY KEY (
                release_id,
                source_station_id,
                source_element_code,
                month
            )
        ) ON COMMIT DROP
        """
    )

    parsed = 0

    with connection.cursor() as cursor:
        with cursor.copy(
            """
            COPY climate_normal_stage (
                release_id,
                source_file_id,
                station_id,
                element_id,
                source_station_id,
                source_element_code,
                month,
                material_years,
                statistics_started_year,
                statistics_ended_year,
                daily_values,
                daily_remarks
            )
            FROM STDIN
            """
        ) as copy:
            for record in series:
                copy.write_row(
                    (
                        catalog.release_id,
                        source_file_id,
                        catalog.station_ids.get(
                            record.source_station_id
                        ),
                        catalog.element_ids[
                            record.element_key
                        ],
                        record.source_station_id,
                        record.source_element_code,
                        record.month,
                        record.material_years,
                        record.statistics_started_year,
                        record.statistics_ended_year,
                        list(record.daily_values),
                        list(record.daily_remarks),
                    )
                )
                parsed += 1

    count_row = connection.execute(
        """
        SELECT
            count(*) FILTER (
                WHERE existing.id IS NULL
            ) AS inserted,
            count(*) FILTER (
                WHERE existing.id IS NOT NULL
                  AND ROW(
                      existing.station_id,
                      existing.element_id,
                      existing.material_years,
                      existing.statistics_started_year,
                      existing.statistics_ended_year,
                      existing.daily_values,
                      existing.daily_remarks
                  ) IS DISTINCT FROM ROW(
                      stage.station_id,
                      stage.element_id,
                      stage.material_years,
                      stage.statistics_started_year,
                      stage.statistics_ended_year,
                      stage.daily_values,
                      stage.daily_remarks
                  )
            ) AS updated,
            count(*) FILTER (
                WHERE existing.id IS NOT NULL
                  AND ROW(
                      existing.station_id,
                      existing.element_id,
                      existing.material_years,
                      existing.statistics_started_year,
                      existing.statistics_ended_year,
                      existing.daily_values,
                      existing.daily_remarks
                  ) IS NOT DISTINCT FROM ROW(
                      stage.station_id,
                      stage.element_id,
                      stage.material_years,
                      stage.statistics_started_year,
                      stage.statistics_ended_year,
                      stage.daily_values,
                      stage.daily_remarks
                  )
            ) AS unchanged
        FROM climate_normal_stage AS stage
        LEFT JOIN weather.climate_normal_series
            AS existing
          ON existing.release_id = stage.release_id
         AND existing.source_station_id
             = stage.source_station_id
         AND existing.source_element_code
             = stage.source_element_code
         AND existing.month = stage.month
        """
    ).fetchone()

    if count_row is None:
        raise RuntimeError(
            "Could not count climate-normal changes."
        )

    connection.execute(
        """
        INSERT INTO weather.climate_normal_series AS target (
            release_id,
            source_file_id,
            station_id,
            element_id,
            source_station_id,
            source_element_code,
            month,
            material_years,
            statistics_started_year,
            statistics_ended_year,
            daily_values,
            daily_remarks
        )
        SELECT
            release_id,
            source_file_id,
            station_id,
            element_id,
            source_station_id,
            source_element_code,
            month,
            material_years,
            statistics_started_year,
            statistics_ended_year,
            daily_values,
            daily_remarks
        FROM climate_normal_stage
        ON CONFLICT (
            release_id,
            source_station_id,
            source_element_code,
            month
        )
        DO UPDATE
        SET
            source_file_id = EXCLUDED.source_file_id,
            station_id = EXCLUDED.station_id,
            element_id = EXCLUDED.element_id,
            material_years = EXCLUDED.material_years,
            statistics_started_year =
                EXCLUDED.statistics_started_year,
            statistics_ended_year =
                EXCLUDED.statistics_ended_year,
            daily_values = EXCLUDED.daily_values,
            daily_remarks = EXCLUDED.daily_remarks,
            updated_at = now()
        WHERE ROW(
            target.station_id,
            target.element_id,
            target.material_years,
            target.statistics_started_year,
            target.statistics_ended_year,
            target.daily_values,
            target.daily_remarks
        ) IS DISTINCT FROM ROW(
            EXCLUDED.station_id,
            EXCLUDED.element_id,
            EXCLUDED.material_years,
            EXCLUDED.statistics_started_year,
            EXCLUDED.statistics_ended_year,
            EXCLUDED.daily_values,
            EXCLUDED.daily_remarks
        )
        """
    )

    return ClimateNormalCounts(
        parsed=parsed,
        inserted=int(count_row[0]),
        updated=int(count_row[1]),
        unchanged=int(count_row[2]),
    )

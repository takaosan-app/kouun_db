from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import streamlit as st

from viewer.database import connect_database

INGESTION_ROW_LIMIT = 1_000

INGESTION_RUNS_QUERY = """
    SELECT
        ingestion_run.id,
        ingestion_run.status,
        ingestion_run.started_at,
        ingestion_run.finished_at,
        CASE
            WHEN ingestion_run.finished_at IS NULL
                THEN NULL
            ELSE EXTRACT(
                EPOCH FROM (
                    ingestion_run.finished_at
                    - ingestion_run.started_at
                )
            )
        END AS duration_seconds,
        ingestion_run.parsed_count,
        ingestion_run.inserted_count,
        ingestion_run.updated_count,
        ingestion_run.unchanged_count,
        ingestion_run.revision_count,
        ingestion_run.error_message,

        source_file.id AS source_file_id,
        source.product_name,
        source_file.storage_path,
        source_file.requested_start_date,
        source_file.requested_end_date,
        source_file.retrieved_at,
        source_file.byte_size,
        source_file.source_row_count,
        source_file.collector_version,

        NULLIF(
            source_file.metadata ->> 'area_code',
            ''
        ) AS area_code,
        observation_area.area_name,

        NULLIF(
            source_file.metadata ->> 'capability_code',
            ''
        ) AS capability_code,

        CASE
            WHEN (
                source_file.metadata
                ->> 'station_count'
            ) ~ '^[0-9]+$'
            THEN (
                source_file.metadata
                ->> 'station_count'
            )::integer
            ELSE NULL
        END AS station_count,

        CASE
            WHEN (
                source_file.metadata
                ->> 'observation_count'
            ) ~ '^[0-9]+$'
            THEN (
                source_file.metadata
                ->> 'observation_count'
            )::integer
            ELSE NULL
        END AS observation_count

    FROM weather.ingestion_run AS ingestion_run

    JOIN weather.source_file AS source_file
        ON source_file.id
            = ingestion_run.source_file_id

    JOIN weather.source AS source
        ON source.id = source_file.source_id

    LEFT JOIN weather.observation_area
        AS observation_area
        ON observation_area.area_code
            = NULLIF(
                source_file.metadata ->> 'area_code',
                ''
            )

    WHERE (
        cardinality(%s::text[]) = 0
        OR ingestion_run.status
            = ANY(%s::text[])
    )
      AND (
        %s::text IS NULL
        OR source_file.metadata
            ->> 'area_code' = %s::text
      )
      AND (
        %s::date IS NULL
        OR ingestion_run.started_at
            >= %s::date
      )
      AND (
        %s::date IS NULL
        OR ingestion_run.started_at
            < %s::date + INTERVAL '1 day'
      )

    ORDER BY
        ingestion_run.started_at DESC,
        ingestion_run.id DESC

    LIMIT %s
"""


@st.cache_data(ttl=60)
def fetch_ingestion_runs(
    *,
    statuses: tuple[str, ...],
    area_code: str | None,
    started_from: date | None,
    started_to: date | None,
) -> pd.DataFrame:
    with connect_database() as connection:
        rows: list[dict[str, Any]] = (
            connection.execute(
                INGESTION_RUNS_QUERY,
                (
                    list(statuses),
                    list(statuses),
                    area_code,
                    area_code,
                    started_from,
                    started_from,
                    started_to,
                    started_to,
                    INGESTION_ROW_LIMIT,
                ),
            ).fetchall()
        )

    return pd.DataFrame(rows)

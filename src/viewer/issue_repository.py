from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from viewer.database import connect_database

ISSUE_ROW_LIMIT = 2_000

ISSUES_QUERY = """
    SELECT
        issue.id,
        issue.severity,
        issue.issue_code,
        issue.area_code,
        area.area_name,
        issue.capability_code,
        COALESCE(
            station.name,
            issue.details ->> 'station_name'
        ) AS station_name,
        issue.observed_on,
        COALESCE(
            element.element_key,
            issue.details ->> 'element_key'
        ) AS element_key,
        element.name AS element_name,
        issue.requested_start_date,
        issue.requested_end_date,
        issue.message,
        issue.details,
        issue.source_file_id,
        source_file.storage_path,
        issue.ingestion_run_id,
        issue.created_at,
        issue.resolved_at
    FROM weather.collection_issue AS issue
    LEFT JOIN weather.observation_area AS area
        ON area.area_code = issue.area_code
    LEFT JOIN weather.station AS station
        ON station.id = issue.station_id
    LEFT JOIN weather.element AS element
        ON element.id = issue.element_id
    LEFT JOIN weather.source_file AS source_file
        ON source_file.id = issue.source_file_id
    WHERE (
        NOT %s
        OR issue.resolved_at IS NULL
    )
      AND (
        cardinality(%s::text[]) = 0
        OR issue.severity = ANY(%s::text[])
      )
      AND (
        %s::text IS NULL
        OR issue.area_code = %s::text
      )
    ORDER BY
        issue.created_at DESC,
        issue.id DESC
    LIMIT %s
"""


@st.cache_data(ttl=60)
def fetch_collection_issues(
    *,
    unresolved_only: bool,
    severities: tuple[str, ...],
    area_code: str | None,
) -> pd.DataFrame:
    with connect_database() as connection:
        rows: list[dict[str, Any]] = connection.execute(
            ISSUES_QUERY,
            (
                unresolved_only,
                list(severities),
                list(severities),
                area_code,
                area_code,
                ISSUE_ROW_LIMIT,
            ),
        ).fetchall()

    return pd.DataFrame(rows)

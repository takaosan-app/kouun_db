from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal

import psycopg
from psycopg.types.json import Jsonb


IssueSeverity = Literal[
    "warning",
    "error",
    "fatal",
]


@dataclass(frozen=True, slots=True)
class CollectionIssue:
    severity: IssueSeverity
    issue_code: str
    message: str

    area_code: str | None = None
    capability_code: str | None = None

    requested_start_date: date | None = None
    requested_end_date: date | None = None

    station_id: int | None = None
    observed_on: date | None = None
    element_id: int | None = None

    source_file_id: int | None = None
    ingestion_run_id: int | None = None

    details: dict[str, object] = field(
        default_factory=dict
    )


def record_collection_issue(
    connection: psycopg.Connection,
    issue: CollectionIssue,
) -> int:
    row = connection.execute(
        """
        INSERT INTO weather.collection_issue (
            severity,
            issue_code,
            area_code,
            capability_code,
            requested_start_date,
            requested_end_date,
            station_id,
            observed_on,
            element_id,
            source_file_id,
            ingestion_run_id,
            message,
            details
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT DO NOTHING
        RETURNING id
        """,
        (
            issue.severity,
            issue.issue_code,
            issue.area_code,
            issue.capability_code,
            issue.requested_start_date,
            issue.requested_end_date,
            issue.station_id,
            issue.observed_on,
            issue.element_id,
            issue.source_file_id,
            issue.ingestion_run_id,
            issue.message,
            Jsonb(issue.details),
        ),
    ).fetchone()

    if row is not None:
        return int(row[0])

    existing = connection.execute(
        """
        SELECT id
        FROM weather.collection_issue
        WHERE resolved_at IS NULL
          AND issue_code = %s
          AND area_code IS NOT DISTINCT FROM %s
          AND capability_code IS NOT DISTINCT FROM %s
          AND requested_start_date
              IS NOT DISTINCT FROM %s
          AND requested_end_date
              IS NOT DISTINCT FROM %s
          AND station_id IS NOT DISTINCT FROM %s
          AND observed_on IS NOT DISTINCT FROM %s
          AND element_id IS NOT DISTINCT FROM %s
        ORDER BY id DESC
        LIMIT 1
        """,
        (
            issue.issue_code,
            issue.area_code,
            issue.capability_code,
            issue.requested_start_date,
            issue.requested_end_date,
            issue.station_id,
            issue.observed_on,
            issue.element_id,
        ),
    ).fetchone()

    if existing is None:
        raise RuntimeError(
            "Could not record or find collection issue."
        )

    issue_id = int(existing[0])

    connection.execute(
        """
        UPDATE weather.collection_issue
        SET
            severity = %s,
            message = %s,
            source_file_id = %s,
            ingestion_run_id = %s,
            details = %s
        WHERE id = %s
        """,
        (
            issue.severity,
            issue.message,
            issue.source_file_id,
            issue.ingestion_run_id,
            Jsonb(issue.details),
            issue_id,
        ),
    )

    return issue_id

def resolve_collection_issues(
    connection: psycopg.Connection,
    *,
    issue_code: str,
    area_code: str,
    capability_code: str,
    requested_start_date: date,
    requested_end_date: date,
    station_id: int | None = None,
) -> int:
    rows = connection.execute(
        """
        UPDATE weather.collection_issue
        SET resolved_at = CURRENT_TIMESTAMP
        WHERE resolved_at IS NULL
          AND issue_code = %s
          AND area_code = %s
          AND capability_code = %s
          AND requested_start_date = %s
          AND requested_end_date = %s
          AND station_id IS NOT DISTINCT FROM %s
          AND observed_on IS NULL
          AND element_id IS NULL
        RETURNING id
        """,
        (
            issue_code,
            area_code,
            capability_code,
            requested_start_date,
            requested_end_date,
            station_id,
        ),
    ).fetchall()

    return len(rows)
from __future__ import annotations

import json
from datetime import date

import psycopg

from collector.catalog_repository import CatalogIds
from collector.collection_issue_repository import (
    CollectionIssue,
    record_collection_issue,
)
from collector.models import (
    AreaObservationStation,
    ParsedJmaCsv,
)


def record_jma_parse_issues(
    connection: psycopg.Connection,
    *,
    parsed: ParsedJmaCsv,
    catalog: CatalogIds,
    area_code: str,
    capability_code: str,
    requested_start_date: date,
    requested_end_date: date,
    source_file_id: int,
    ingestion_run_id: int,
) -> int:
    recorded = 0

    for issue in parsed.issues:
        action = (
            "stored_as_missing"
            if issue.raw_value
            else "stored_as_not_observed"
        )
        issue_id = record_collection_issue(
            connection,
            CollectionIssue(
                severity="warning",
                issue_code=issue.issue_code,
                message=issue.message,
                area_code=area_code,
                capability_code=capability_code,
                requested_start_date=(
                    requested_start_date
                ),
                requested_end_date=requested_end_date,
                station_id=catalog.station_id,
                observed_on=issue.observed_on,
                element_id=catalog.element_ids[
                    issue.element_key
                ],
                source_file_id=source_file_id,
                ingestion_run_id=ingestion_run_id,
                details={
                    "station_name":
                        parsed.station_name,
                    "element_key":
                        issue.element_key,
                    "raw_value":
                        issue.raw_value,
                    "action":
                        action,
                },
            ),
        )

        print(
            json.dumps(
                {
                    "level": "warning",
                    "event": issue.issue_code,
                    "issue_id": issue_id,
                    "area_code": area_code,
                    "capability_code":
                        capability_code,
                    "station_name":
                        parsed.station_name,
                    "observed_on":
                        issue.observed_on.isoformat(),
                    "element":
                        issue.element_key,
                    "action": action,
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
        recorded += 1

    return recorded


def record_empty_station_issue(
    connection: psycopg.Connection,
    *,
    station: AreaObservationStation,
    area_code: str,
    capability_code: str,
    requested_start_date: date,
    requested_end_date: date,
    source_file_id: int,
    ingestion_run_id: int,
) -> int:
    message = (
        "No usable observation elements were "
        "available for the requested period."
    )
    issue_id = record_collection_issue(
        connection,
        CollectionIssue(
            severity="warning",
            issue_code=(
                "no_available_observations"
            ),
            message=message,
            area_code=area_code,
            capability_code=capability_code,
            requested_start_date=(
                requested_start_date
            ),
            requested_end_date=requested_end_date,
            source_file_id=source_file_id,
            ingestion_run_id=ingestion_run_id,
            details={
                "source_station_id":
                    station.source_station_id,
                "station_key":
                    station.station_key,
                "station_name":
                    station.station_name,
                "action":
                    "station_skipped",
            },
        ),
    )

    print(
        json.dumps(
            {
                "level": "warning",
                "event":
                    "no_available_observations",
                "issue_id": issue_id,
                "area_code": area_code,
                "capability_code":
                    capability_code,
                "station_name":
                    station.station_name,
                "start_date":
                    requested_start_date.isoformat(),
                "end_date":
                    requested_end_date.isoformat(),
                "action": "station_skipped",
            },
            ensure_ascii=False,
        ),
        flush=True,
    )

    return issue_id

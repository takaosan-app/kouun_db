from __future__ import annotations

import json
from datetime import date

from collector.collection_issue_repository import (
    CollectionIssue,
    record_collection_issue,
)
from collector.database import connect_database
from collector.settings import DatabaseSettings
from collector.station_collection_repository import (
    StationCollectionTarget,
)


def record_jma_job_failure(
    *,
    area_code: str,
    capability_code: str,
    start_date: date,
    end_date: date,
    error: Exception,
) -> int:
    connection = connect_database(
        DatabaseSettings()
    )

    try:
        issue_id = record_collection_issue(
            connection,
            CollectionIssue(
                severity="error",
                issue_code=(
                    "collection_job_failed"
                ),
                message=str(error),
                area_code=area_code,
                capability_code=capability_code,
                requested_start_date=start_date,
                requested_end_date=end_date,
                details={
                    "error_type":
                        type(error).__name__,
                    "action":
                        "continued_to_next_job",
                },
            ),
        )
        connection.commit()
    finally:
        connection.close()

    print(
        json.dumps(
            {
                "level": "error",
                "event": "collection_job_failed",
                "issue_id": issue_id,
                "area_code": area_code,
                "capability_code":
                    capability_code,
                "start_date":
                    start_date.isoformat(),
                "end_date":
                    end_date.isoformat(),
                "error_type":
                    type(error).__name__,
                "error": str(error),
                "action":
                    "continued_to_next_job",
            },
            ensure_ascii=False,
        ),
        flush=True,
    )

    return issue_id

def record_jma_station_failure(
    *,
    area_code: str,
    capability_code: str,
    start_date: date,
    end_date: date,
    station: StationCollectionTarget,
    error: Exception,
) -> int:
    connection = connect_database(
        DatabaseSettings()
    )

    try:
        issue_id = record_collection_issue(
            connection,
            CollectionIssue(
                severity="error",
                issue_code=(
                    "collection_station_failed"
                ),
                message=str(error),
                area_code=area_code,
                capability_code=capability_code,
                requested_start_date=start_date,
                requested_end_date=end_date,
                station_id=station.station_id,
                details={
                    "error_type":
                        type(error).__name__,
                    "action":
                        "station_skipped",
                    "source_station_id":
                        station.source_station_id,
                    "station_key":
                        station.station_key,
                    "station_name":
                        station.name,
                },
            ),
        )
        connection.commit()
    finally:
        connection.close()

    print(
        json.dumps(
            {
                "level": "error",
                "event":
                    "collection_station_failed",
                "issue_id": issue_id,
                "area_code": area_code,
                "capability_code":
                    capability_code,
                "station_id":
                    station.station_id,
                "source_station_id":
                    station.source_station_id,
                "station_name":
                    station.name,
                "start_date":
                    start_date.isoformat(),
                "end_date":
                    end_date.isoformat(),
                "error_type":
                    type(error).__name__,
                "error": str(error),
                "action": "station_skipped",
            },
            ensure_ascii=False,
        ),
        flush=True,
    )

    return issue_id

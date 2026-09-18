from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

import requests

from collector.collection_issue_repository import (
    resolve_collection_issues,
)
from collector.database import connect_database
from collector.date_ranges import DateRange
from collector.import_jma_area_csv import (
    import_jma_area_csv,
)
from collector.jma_area_fetcher import (
    collect_jma_area_data,
)
from collector.jma_area_source_files import (
    find_existing_area_files,
)
from collector.jma_elements import ElementRequest
from collector.jma_job_issues import (
    record_jma_station_failure,
)
from collector.observation_repository import UpsertCounts
from collector.settings import DatabaseSettings
from collector.station_collection_groups import (
    StationCollectionGroup,
)


@dataclass(frozen=True, slots=True)
class StationFallbackResult:
    attempted: int
    succeeded: int
    failed: int
    downloaded: int
    reused: int
    counts: UpsertCounts


def run_station_fallback(
    *,
    group: StationCollectionGroup,
    period: DateRange,
    output_dir: Path,
    elements: tuple[ElementRequest, ...],
    request_delay: float,
) -> StationFallbackResult:
    succeeded = 0
    failed = 0
    downloaded = 0
    reused_count = 0
    parsed = 0
    inserted = 0
    updated = 0
    unchanged = 0

    for index, station in enumerate(group.stations):
        station_group = StationCollectionGroup(
            area_code=group.area_code,
            capability_code=group.capability_code,
            stations=(station,),
        )

        try:
            existing = find_existing_area_files(
                output_dir=output_dir,
                group=station_group,
                period=period,
                elements=elements,
            )

            if existing is None:
                collected = collect_jma_area_data(
                    area_code=group.area_code,
                    capability_code=group.capability_code,
                    stations=(station,),
                    start_date=period.start,
                    end_date=period.end,
                    output_dir=output_dir,
                    elements=elements,
                )
                csv_path = collected.csv_path
                metadata_path = collected.metadata_path
                reused = False
                downloaded += 1
            else:
                csv_path, metadata_path = existing
                reused = True
                reused_count += 1

            ingestion_run_id, counts = (
                import_jma_area_csv(
                    csv_path=csv_path,
                    metadata_path=metadata_path,
                    raw_root=output_dir,
                )
            )

            _resolve_station_failure(
                group=group,
                period=period,
                station_id=station.station_id,
            )

            succeeded += 1
            parsed += counts.parsed
            inserted += counts.inserted
            updated += counts.updated
            unchanged += counts.unchanged

            print(
                json.dumps(
                    {
                        "event":
                            "station_fallback_succeeded",
                        "area_code":
                            group.area_code,
                        "capability_code":
                            group.capability_code,
                        "station_id":
                            station.station_id,
                        "source_station_id":
                            station.source_station_id,
                        "station_name":
                            station.name,
                        "start_date":
                            period.start.isoformat(),
                        "end_date":
                            period.end.isoformat(),
                        "reused": reused,
                        "ingestion_run_id":
                            ingestion_run_id,
                        "inserted":
                            counts.inserted,
                        "updated":
                            counts.updated,
                        "unchanged":
                            counts.unchanged,
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )

        except (
            ValueError,
            requests.RequestException,
        ) as error:
            failed += 1
            record_jma_station_failure(
                area_code=group.area_code,
                capability_code=group.capability_code,
                start_date=period.start,
                end_date=period.end,
                station=station,
                error=error,
            )

        if index < len(group.stations) - 1:
            time.sleep(request_delay)

    _resolve_group_failure(
        group=group,
        period=period,
    )

    return StationFallbackResult(
        attempted=len(group.stations),
        succeeded=succeeded,
        failed=failed,
        downloaded=downloaded,
        reused=reused_count,
        counts=UpsertCounts(
            parsed=parsed,
            inserted=inserted,
            updated=updated,
            unchanged=unchanged,
        ),
    )


def _resolve_station_failure(
    *,
    group: StationCollectionGroup,
    period: DateRange,
    station_id: int,
) -> None:
    _resolve_issue(
        issue_code="collection_station_failed",
        group=group,
        period=period,
        station_id=station_id,
    )


def _resolve_group_failure(
    *,
    group: StationCollectionGroup,
    period: DateRange,
) -> None:
    _resolve_issue(
        issue_code="collection_job_failed",
        group=group,
        period=period,
        station_id=None,
    )


def _resolve_issue(
    *,
    issue_code: str,
    group: StationCollectionGroup,
    period: DateRange,
    station_id: int | None,
) -> None:
    connection = connect_database(
        DatabaseSettings()
    )

    try:
        resolve_collection_issues(
            connection,
            issue_code=issue_code,
            area_code=group.area_code,
            capability_code=group.capability_code,
            requested_start_date=period.start,
            requested_end_date=period.end,
            station_id=station_id,
        )
        connection.commit()
    finally:
        connection.close()

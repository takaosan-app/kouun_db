from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import requests

from collector.database import connect_database
from collector.date_ranges import split_into_months
from collector.import_jma_area_csv import (
    import_jma_area_csv,
)
from collector.jma_area_fetcher import (
    collect_jma_area_data,
)
from collector.jma_area_source_files import (
    find_existing_area_files,
)
from collector.jma_csv_parser import JmaCsvError
from collector.jma_job_issues import (
    record_jma_job_failure,
)
from collector.jma_elements import ELEMENT_PROFILES
from collector.jma_station_fallback import (
    run_station_fallback,
)
from collector.observation_repository import UpsertCounts
from collector.settings import (
    SCRAPING_INTERVAL,
    DatabaseSettings,
)
from collector.station_collection_groups import (
    StationCollectionGroup,
    group_station_collection_targets,
)
from collector.station_collection_repository import (
    list_station_collection_targets,
)


@dataclass(frozen=True, slots=True)
class AreaTypeBatchConfig:
    area_code: str
    start_date: date
    end_date: date
    output_dir: Path
    request_delay: float = SCRAPING_INTERVAL
    element_profile: str = "extended"
    capability_code: str | None = None


def run_area_type_batch(
    config: AreaTypeBatchConfig,
) -> dict[str, int]:
    if config.request_delay < SCRAPING_INTERVAL:
        raise ValueError(
            f"request-delay must be at least {SCRAPING_INTERVAL} seconds."
        )

    if config.element_profile not in ELEMENT_PROFILES:
        raise ValueError(
            "Unknown element profile: "
            f"{config.element_profile}"
        )

    groups = _load_groups(
        area_code=config.area_code,
        capability_code=config.capability_code,
    )
    periods = split_into_months(
        config.start_date,
        config.end_date,
    )
    elements = ELEMENT_PROFILES[
        config.element_profile
    ]
    jobs = tuple(
        (period, group)
        for period in periods
        for group in groups
    )
    totals = {
        "groups": len(groups),
        "months": len(periods),
        "jobs": 0,
        "succeeded_jobs": 0,
        "failed_jobs": 0,
        "downloaded": 0,
        "reused": 0,
        "parsed": 0,
        "inserted": 0,
        "updated": 0,
        "unchanged": 0,
        "revisions": 0,
    }

    for index, (period, group) in enumerate(jobs):
        try:
            existing = find_existing_area_files(
                output_dir=config.output_dir,
                group=group,
                period=period,
                elements=elements,
            )

            if existing is None:
                collected = collect_jma_area_data(
                    area_code=group.area_code,
                    capability_code=(
                        group.capability_code
                    ),
                    stations=group.stations,
                    start_date=period.start,
                    end_date=period.end,
                    output_dir=config.output_dir,
                    elements=elements,
                )
                csv_path = collected.csv_path
                metadata_path = (
                    collected.metadata_path
                )
                reused = False
                totals["downloaded"] += 1
            else:
                csv_path, metadata_path = existing
                reused = True
                totals["reused"] += 1

            ingestion_run_id, counts = (
                import_jma_area_csv(
                    csv_path=csv_path,
                    metadata_path=metadata_path,
                    raw_root=config.output_dir,
                )
            )

        except JmaCsvError as error:
            totals["jobs"] += 1

            record_jma_job_failure(
                area_code=group.area_code,
                capability_code=(
                    group.capability_code
                ),
                start_date=period.start,
                end_date=period.end,
                error=error,
            )

            fallback = run_station_fallback(
                group=group,
                period=period,
                output_dir=config.output_dir,
                elements=elements,
                request_delay=config.request_delay,
            )

            totals["downloaded"] += (
                fallback.downloaded
            )
            totals["reused"] += fallback.reused
            totals["parsed"] += (
                fallback.counts.parsed
            )
            totals["inserted"] += (
                fallback.counts.inserted
            )
            totals["updated"] += (
                fallback.counts.updated
            )
            totals["unchanged"] += (
                fallback.counts.unchanged
            )
            totals["revisions"] += (
                fallback.counts.revisions
            )

            if fallback.failed:
                totals["failed_jobs"] += 1
            else:
                totals["succeeded_jobs"] += 1

            if index < len(jobs) - 1:
                time.sleep(config.request_delay)

            continue

        except (
            ValueError,
            requests.RequestException,
        ) as error:
            totals["jobs"] += 1
            totals["failed_jobs"] += 1

            record_jma_job_failure(
                area_code=group.area_code,
                capability_code=(
                    group.capability_code
                ),
                start_date=period.start,
                end_date=period.end,
                error=error,
            )

            if index < len(jobs) - 1:
                time.sleep(config.request_delay)

            continue

        totals["jobs"] += 1
        totals["succeeded_jobs"] += 1
        totals["parsed"] += counts.parsed
        totals["inserted"] += counts.inserted
        totals["updated"] += counts.updated
        totals["unchanged"] += counts.unchanged
        totals["revisions"] += counts.revisions

        _print_job_result(
            group=group,
            start_date=period.start,
            end_date=period.end,
            reused=reused,
            ingestion_run_id=ingestion_run_id,
            counts=counts,
        )

        if (
            not reused
            and index < len(jobs) - 1
        ):
            time.sleep(config.request_delay)

    return totals


def _load_groups(
    *,
    area_code: str,
    capability_code: str | None,
) -> tuple[StationCollectionGroup, ...]:
    connection = connect_database(
        DatabaseSettings()
    )

    try:
        targets = list_station_collection_targets(
            connection,
            area_code,
        )
    finally:
        connection.close()

    groups = group_station_collection_targets(
        area_code,
        targets,
    )

    if capability_code is not None:
        groups = tuple(
            group
            for group in groups
            if group.capability_code
            == capability_code
        )

        if not groups:
            raise ValueError(
                "Capability code was not found "
                f"in area {area_code}: "
                f"{capability_code}"
            )

    return groups


def _print_job_result(
    *,
    group: StationCollectionGroup,
    start_date: date,
    end_date: date,
    reused: bool,
    ingestion_run_id: int,
    counts: UpsertCounts,
) -> None:
    print(
        json.dumps(
            {
                "area_code": group.area_code,
                "capability_code":
                    group.capability_code,
                "station_count":
                    len(group.stations),
                "start_date":
                    start_date.isoformat(),
                "end_date":
                    end_date.isoformat(),
                "reused": reused,
                "ingestion_run_id":
                    ingestion_run_id,
                "inserted": counts.inserted,
                "updated": counts.updated,
                "unchanged": counts.unchanged,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )

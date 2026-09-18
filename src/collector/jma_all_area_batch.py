from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from collector.database import connect_database
from collector.jma_area_type_batch import (
    AreaTypeBatchConfig,
    run_area_type_batch,
)
from collector.jma_elements import ELEMENT_PROFILES
from collector.observation_area_repository import (
    ObservationAreaTarget,
    list_domestic_observation_areas,
)
from collector.settings import (
    SCRAPING_INTERVAL,
    DatabaseSettings,
)


@dataclass(frozen=True, slots=True)
class AllAreaBatchConfig:
    start_date: date
    end_date: date
    output_dir: Path
    request_delay: float = SCRAPING_INTERVAL
    element_profile: str = "extended"
    start_area_code: str | None = None
    limit: int | None = None


def run_all_area_batch(
    config: AllAreaBatchConfig,
) -> dict[str, int]:
    _validate_config(config)
    targets = _load_targets(config)

    totals = {
        "areas": 0,
        "groups": 0,
        "months": 0,
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

    for index, target in enumerate(targets):
        _print_area_result(
            target,
            status="starting",
        )

        area_totals = run_area_type_batch(
            AreaTypeBatchConfig(
                area_code=target.area_code,
                start_date=config.start_date,
                end_date=config.end_date,
                output_dir=config.output_dir,
                request_delay=config.request_delay,
                element_profile=config.element_profile,
            )
        )

        totals["areas"] += 1

        for key in (
            "groups",
            "months",
            "jobs",
            "succeeded_jobs",
            "failed_jobs",
            "downloaded",
            "reused",
            "parsed",
            "inserted",
            "updated",
            "unchanged",
            "revisions",
        ):
            totals[key] += area_totals[key]

        area_status = (
            "completed_with_errors"
            if area_totals["failed_jobs"]
            else "succeeded"
        )
        _print_area_result(
            target,
            status=area_status,
            details=area_totals,
        )

        if index < len(targets) - 1:
            time.sleep(config.request_delay)

    return totals


def _validate_config(
    config: AllAreaBatchConfig,
) -> None:
    if config.start_date > config.end_date:
        raise ValueError(
            "start-date must not be later than end-date."
        )

    if config.request_delay < SCRAPING_INTERVAL:
        raise ValueError(
            f"request-delay must be at least {SCRAPING_INTERVAL} seconds."
        )

    if config.element_profile not in ELEMENT_PROFILES:
        raise ValueError(
            "Unknown element profile: "
            f"{config.element_profile}"
        )

    if config.limit is not None and config.limit <= 0:
        raise ValueError(
            "limit must be a positive integer."
        )


def _load_targets(
    config: AllAreaBatchConfig,
) -> tuple[ObservationAreaTarget, ...]:
    connection = connect_database(DatabaseSettings())

    try:
        targets = list_domestic_observation_areas(
            connection
        )
    finally:
        connection.close()

    if config.start_area_code is not None:
        targets = tuple(
            target
            for target in targets
            if target.area_code >= config.start_area_code
        )

        if not targets:
            raise ValueError(
                "No areas were found at or after "
                f"{config.start_area_code}."
            )

    if config.limit is not None:
        targets = targets[: config.limit]

    return targets


def _print_area_result(
    target: ObservationAreaTarget,
    *,
    status: str,
    details: dict[str, int] | None = None,
) -> None:
    message: dict[str, object] = {
        "area_code": target.area_code,
        "area_name": target.area_name,
        "status": status,
    }

    if details is not None:
        message.update(details)

    print(
        json.dumps(
            message,
            ensure_ascii=False,
        ),
        flush=True,
    )

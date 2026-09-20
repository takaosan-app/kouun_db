from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import psycopg

from analyzer.l2_daily_weather_queries import (
    DELETE_FEATURES,
    INSERT_DAILY_FEATURES,
)


@dataclass(frozen=True, slots=True)
class DailyWeatherFeatureCounts:
    days: int
    inserted: int
    deleted: int


def rebuild_daily_weather_features(
    connection: psycopg.Connection,
    *,
    start_date: date,
    end_date: date,
    calculation_version: int = 1,
    station_id: int | None = None,
    area_code: str | None = None,
) -> DailyWeatherFeatureCounts:
    if end_date < start_date:
        raise ValueError(
            "end_date must not be before start_date."
        )

    deleted_row = connection.execute(
        DELETE_FEATURES,
        (
            start_date,
            end_date,
            station_id,
            station_id,
            area_code,
            area_code,
        ),
    ).fetchone()

    if deleted_row is None:
        raise RuntimeError(
            "Could not count deleted L2 rows."
        )

    inserted = 0
    processed_days = 0
    current_date = start_date

    while current_date <= end_date:
        inserted_row = connection.execute(
            INSERT_DAILY_FEATURES,
            (
                calculation_version,
                current_date,
                station_id,
                station_id,
                area_code,
                area_code,
            ),
        ).fetchone()

        if inserted_row is None:
            raise RuntimeError(
                "Could not count inserted L2 rows "
                f"for {current_date.isoformat()}."
            )

        inserted += int(inserted_row[0])
        processed_days += 1
        current_date += timedelta(days=1)

    return DailyWeatherFeatureCounts(
        days=processed_days,
        inserted=inserted,
        deleted=int(deleted_row[0]),
    )

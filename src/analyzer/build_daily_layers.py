from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from analyzer.daily_weather_repository import upsert_daily_weather
from analyzer.l1_capability_repository import (
    sync_station_element_capabilities,
)
from analyzer.l1_catalog_repository import (
    sync_weather_areas,
    sync_weather_stations,
)
from analyzer.l1_station_relation_repository import (
    sync_weather_station_areas,
)
from analyzer.l2_daily_weather_repository import (
    rebuild_daily_weather_features,
)
from collector.database import connect_database
from collector.settings import DatabaseSettings

JST = ZoneInfo("Asia/Tokyo")
DEFAULT_LOOKBACK_DAYS = 7


def main() -> None:
    args = _parse_args()
    end_date = args.end_date or _default_end_date()
    start_date = end_date - timedelta(
        days=args.lookback_days - 1
    )

    settings = DatabaseSettings()

    with connect_database(settings) as connection:
        changed_areas = sync_weather_areas(connection)
        changed_stations = sync_weather_stations(connection)
        inserted_station_areas, deleted_station_areas = (
            sync_weather_station_areas(connection)
        )
        (
            changed_station_capabilities,
            deleted_station_capabilities,
        ) = sync_station_element_capabilities(connection)

        l1_processed = upsert_daily_weather(
            connection,
            start_date=start_date,
            end_date=end_date,
            area_code=None,
        )

        l2_counts = rebuild_daily_weather_features(
            connection,
            start_date=start_date,
            end_date=end_date,
            calculation_version=args.calculation_version,
        )

        connection.commit()

    print(
        json.dumps(
            {
                "status": "succeeded",
                "mode": "daily_layers",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "lookback_days": args.lookback_days,
                "calculation_version":
                    args.calculation_version,
                "l1": {
                    "changed_areas": changed_areas,
                    "changed_stations": changed_stations,
                    "inserted_station_areas":
                        inserted_station_areas,
                    "deleted_station_areas":
                        deleted_station_areas,
                    "changed_station_capabilities":
                        changed_station_capabilities,
                    "deleted_station_capabilities":
                        deleted_station_capabilities,
                    "processed_daily_weather": l1_processed,
                },
                "l2": {
                    "days": l2_counts.days,
                    "inserted": l2_counts.inserted,
                    "deleted": l2_counts.deleted,
                },
            },
            ensure_ascii=False,
        )
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build recent L1 and L2 daily weather data "
            "after the daily JMA collection."
        )
    )
    parser.add_argument(
        "--end-date",
        type=date.fromisoformat,
        help=(
            "Last observation date. "
            "Defaults to yesterday in Japan."
        ),
    )
    parser.add_argument(
        "--lookback-days",
        type=_positive_integer,
        default=DEFAULT_LOOKBACK_DAYS,
    )
    parser.add_argument(
        "--calculation-version",
        type=_positive_integer,
        default=1,
    )
    return parser.parse_args()


def _positive_integer(value: str) -> int:
    parsed = int(value)

    if parsed <= 0:
        raise argparse.ArgumentTypeError(
            "value must be a positive integer"
        )

    return parsed


def _default_end_date() -> date:
    return datetime.now(JST).date() - timedelta(days=1)


if __name__ == "__main__":
    main()

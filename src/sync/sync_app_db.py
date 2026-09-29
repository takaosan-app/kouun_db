from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import psycopg

from collector.database import connect_database
from collector.settings import DatabaseSettings
from sync.copier import copy_table, purge_expired
from sync.scope import fetch_target_station_ids
from sync.settings import AppDatabaseSettings
from sync.tables import (
    CATALOG_TABLES,
    CLIMATE_NORMAL_RELEASE,
    DAILY_TABLES,
    STATION_DAILY_WEATHER_NORMAL,
)

JST = ZoneInfo("Asia/Tokyo")
DEFAULT_LOOKBACK_DAYS = 7


def main() -> None:
    args = _parse_args()
    since = None if args.full else _start_date(args.lookback_days)
    results: dict[str, dict[str, int]] = {}

    with (
        connect_database(DatabaseSettings()) as source,
        _connect_app_database(AppDatabaseSettings()) as target,
    ):
        station_ids = fetch_target_station_ids(source)

        for spec in CATALOG_TABLES:
            results[spec.name] = asdict(
                copy_table(source, target, spec, station_ids, None)
            )

        # Normals are copied only when their release changed or on --full.
        release_changed = results[CLIMATE_NORMAL_RELEASE.name]["changed"] > 0
        if args.full or release_changed:
            results[STATION_DAILY_WEATHER_NORMAL.name] = asdict(
                copy_table(
                    source, target, STATION_DAILY_WEATHER_NORMAL,
                    station_ids, None,
                )
            )

        for spec in DAILY_TABLES:
            result = asdict(copy_table(source, target, spec, station_ids, since))
            result["expired"] = purge_expired(target, spec)
            results[spec.name] = result

        target.commit()

    print(
        json.dumps(
            {
                "status": "succeeded",
                "mode": "app_db_sync",
                "full": args.full,
                "since": since.isoformat() if since else None,
                "stations": len(station_ids),
                "tables": results,
            },
            ensure_ascii=False,
        )
    )


def _connect_app_database(
    settings: AppDatabaseSettings,
) -> psycopg.Connection:
    return psycopg.connect(
        host=settings.host,
        port=settings.port,
        dbname=settings.name,
        user=settings.user,
        password=settings.password.get_secret_value(),
        sslmode=settings.sslmode,
        autocommit=False,
    )


def _start_date(lookback_days: int) -> date:
    yesterday = datetime.now(JST).date() - timedelta(days=1)
    return yesterday - timedelta(days=lookback_days - 1)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copy weather data for the app release area to the app database."
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Copy all rows within the retention periods.",
    )
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=DEFAULT_LOOKBACK_DAYS,
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()

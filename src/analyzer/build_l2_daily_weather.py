from __future__ import annotations

import argparse
import json
from datetime import date

from analyzer.l2_daily_weather_repository import (
    rebuild_daily_weather_features,
)
from collector.database import connect_database
from collector.settings import DatabaseSettings


def main() -> None:
    args = _parse_args()

    if args.end_date < args.start_date:
        raise SystemExit(
            "--end-date must not be before --start-date"
        )

    settings = DatabaseSettings()

    with connect_database(settings) as connection:
        counts = rebuild_daily_weather_features(
            connection,
            start_date=args.start_date,
            end_date=args.end_date,
            calculation_version=args.calculation_version,
            station_id=args.station_id,
            area_code=args.area_code,
        )
        connection.commit()

    print(
        json.dumps(
            {
                "status": "succeeded",
                "layer": "L2",
                "dataset": "daily_weather_features",
                "start_date": args.start_date.isoformat(),
                "end_date": args.end_date.isoformat(),
                "calculation_version":
                    args.calculation_version,
                "station_id": args.station_id,
                "area_code": args.area_code,
                "days": counts.days,
                "inserted": counts.inserted,
                "deleted": counts.deleted,
            },
            ensure_ascii=False,
        )
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build L2 cumulative daily weather features "
            "from L1 daily weather."
        )
    )
    parser.add_argument(
        "--start-date",
        required=True,
        type=date.fromisoformat,
    )
    parser.add_argument(
        "--end-date",
        required=True,
        type=date.fromisoformat,
    )
    parser.add_argument(
        "--calculation-version",
        type=int,
        default=1,
        help="Feature calculation version. Default: 1.",
    )

    target_group = parser.add_mutually_exclusive_group()
    target_group.add_argument(
        "--station-id",
        type=int,
        help="Build only the specified L1 station.",
    )
    target_group.add_argument(
        "--area-code",
        help="Build only stations in this observation area.",
    )

    return parser.parse_args()


if __name__ == "__main__":
    main()

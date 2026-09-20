from __future__ import annotations

import argparse
import json
from datetime import date

from analyzer.daily_weather_repository import upsert_daily_weather
from collector.database import connect_database
from collector.settings import DatabaseSettings


def main() -> None:
    args = _parse_args()

    if args.end_date < args.start_date:
        raise SystemExit("--end-date must not be before --start-date")

    settings = DatabaseSettings()
    with connect_database(settings) as connection:
        processed = upsert_daily_weather(
            connection,
            start_date=args.start_date,
            end_date=args.end_date,
            area_code=args.area_code,
        )
        connection.commit()

    print(
        json.dumps(
            {
                "status": "succeeded",
                "layer": "L1",
                "start_date": args.start_date.isoformat(),
                "end_date": args.end_date.isoformat(),
                "area_code": args.area_code,
                "processed": processed,
            },
            ensure_ascii=False,
        )
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build compact L1 daily weather rows from L0 observations."
    )
    parser.add_argument("--start-date", required=True, type=date.fromisoformat)
    parser.add_argument("--end-date", required=True, type=date.fromisoformat)
    parser.add_argument(
        "--area-code",
        help="Optional two-digit JMA observation area code.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()

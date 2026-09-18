from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg
import requests

from collector.jma_all_area_batch import (
    AllAreaBatchConfig,
    run_all_area_batch,
)
from collector.jma_elements import ELEMENT_PROFILES
from collector.settings import SCRAPING_INTERVAL

JST = ZoneInfo("Asia/Tokyo")
DEFAULT_LOOKBACK_DAYS = 7


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Collect recent daily JMA observations "
            "for all domestic observation areas."
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
        "--output-dir",
        type=Path,
        default=Path("/data/raw"),
    )
    parser.add_argument(
        "--request-delay",
        type=float,
        default=SCRAPING_INTERVAL,
    )
    parser.add_argument(
        "--element-profile",
        choices=tuple(ELEMENT_PROFILES),
        default="extended",
    )
    parser.add_argument(
        "--start-area-code",
    )
    parser.add_argument(
        "--limit",
        type=_positive_integer,
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
    return datetime.now(JST).date() - timedelta(
        days=1
    )


def main() -> int:
    args = parse_args()
    end_date = args.end_date or _default_end_date()
    start_date = end_date - timedelta(
        days=args.lookback_days - 1
    )

    config = AllAreaBatchConfig(
        start_date=start_date,
        end_date=end_date,
        output_dir=args.output_dir,
        request_delay=args.request_delay,
        element_profile=args.element_profile,
        start_area_code=args.start_area_code,
        limit=args.limit,
    )

    try:
        totals = run_all_area_batch(config)
    except (
        OSError,
        ValueError,
        RuntimeError,
        psycopg.Error,
        requests.RequestException,
    ) as error:
        print(
            f"Daily JMA batch failed: {error}",
            file=sys.stderr,
        )
        return 1

    status = (
        "completed_with_errors"
        if totals["failed_jobs"]
        else "succeeded"
    )

    print(
        json.dumps(
            {
                "status": status,
                "mode": "daily",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "lookback_days":
                    args.lookback_days,
                "element_profile":
                    args.element_profile,
                **totals,
            },
            ensure_ascii=False,
        )
    )

    return 1 if totals["failed_jobs"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

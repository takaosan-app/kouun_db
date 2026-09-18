from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import psycopg
import requests

from collector.jma_all_area_batch import (
    AllAreaBatchConfig,
    run_all_area_batch,
)
from collector.jma_elements import ELEMENT_PROFILES
from collector.settings import SCRAPING_INTERVAL


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Collect JMA observations for all "
            "domestic observation areas."
        )
    )
    parser.add_argument(
        "--start-date",
        type=date.fromisoformat,
        required=True,
    )
    parser.add_argument(
        "--end-date",
        type=date.fromisoformat,
        required=True,
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
        help="Resume from this area code.",
    )
    parser.add_argument(
        "--limit",
        type=_positive_int,
        help="Limit areas for an inspection run.",
    )
    return parser.parse_args()


def _positive_int(value: str) -> int:
    parsed = int(value)

    if parsed <= 0:
        raise argparse.ArgumentTypeError(
            "value must be a positive integer"
        )

    return parsed


def main() -> int:
    args = parse_args()
    config = AllAreaBatchConfig(
        start_date=args.start_date,
        end_date=args.end_date,
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
            f"All-area batch failed: {error}",
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
                "start_date":
                    args.start_date.isoformat(),
                "end_date":
                    args.end_date.isoformat(),
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

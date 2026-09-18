from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

import psycopg
import requests

from collector.jma_area_type_batch import (
    AreaTypeBatchConfig,
    run_area_type_batch,
)
from collector.jma_elements import ELEMENT_PROFILES
from collector.settings import SCRAPING_INTERVAL


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Collect monthly JMA observations grouped "
            "by area and station capability."
        )
    )
    parser.add_argument(
        "--area-code",
        required=True,
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
        "--capability-code",
        type=_capability_code,
        help="Limit an inspection run to one capability.",
    )
    return parser.parse_args()


def _capability_code(value: str) -> str:
    if not re.fullmatch(r"\d{6}", value):
        raise argparse.ArgumentTypeError(
            "capability code must contain six digits"
        )

    return value


def main() -> int:
    args = parse_args()
    config = AreaTypeBatchConfig(
        area_code=args.area_code,
        start_date=args.start_date,
        end_date=args.end_date,
        output_dir=args.output_dir,
        request_delay=args.request_delay,
        element_profile=args.element_profile,
        capability_code=args.capability_code,
    )

    try:
        totals = run_area_type_batch(config)
    except (
        OSError,
        ValueError,
        RuntimeError,
        psycopg.Error,
        requests.RequestException,
    ) as error:
        print(
            f"Area type batch failed: {error}",
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
                "area_code": args.area_code,
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
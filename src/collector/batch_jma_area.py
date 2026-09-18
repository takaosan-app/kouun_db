from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

import psycopg
import requests

from collector.batch_jma import run_batch
from collector.database import connect_database
from collector.jma_elements import ELEMENT_PROFILES
from collector.settings import DatabaseSettings
from collector.station_collection_repository import (
    StationCollectionTarget,
    list_station_collection_targets,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Collect JMA observations for all active "
            "stations in a area."
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
        default=5.0,
    )
    parser.add_argument(
        "--element-profile",
        choices=tuple(ELEMENT_PROFILES),
        default="extended",
    )
    parser.add_argument(
        "--limit",
        type=_positive_int,
        help="Limit stations for an inspection run.",
    )
    return parser.parse_args()


def run_area_batch(
    args: argparse.Namespace,
) -> dict[str, int]:
    connection = connect_database(DatabaseSettings())

    try:
        targets = list_station_collection_targets(
            connection,
            args.area_code,
        )
    finally:
        connection.close()

    if args.limit is not None:
        targets = targets[: args.limit]

    totals = {
        "stations": 0,
        "months": 0,
        "downloaded": 0,
        "reused": 0,
        "parsed": 0,
        "inserted": 0,
        "updated": 0,
        "unchanged": 0,
        "revisions": 0,
    }

    for index, target in enumerate(targets):
        _print_station_status(
            target,
            status="starting",
        )

        station_totals = run_batch(
            _make_station_args(args, target)
        )

        totals["stations"] += 1

        for key in (
            "months",
            "downloaded",
            "reused",
            "parsed",
            "inserted",
            "updated",
            "unchanged",
            "revisions",
        ):
            totals[key] += station_totals[key]

        _print_station_status(
            target,
            status="succeeded",
            totals=station_totals,
        )

        if (
            station_totals["downloaded"] > 0
            and index < len(targets) - 1
        ):
            time.sleep(args.request_delay)

    return totals


def _make_station_args(
    args: argparse.Namespace,
    target: StationCollectionTarget,
) -> argparse.Namespace:
    return argparse.Namespace(
        station_id=target.source_station_id,
        station_key=target.station_key,
        start_date=args.start_date,
        end_date=args.end_date,
        output_dir=args.output_dir,
        request_delay=args.request_delay,
        element_profile=args.element_profile,
    )


def _print_station_status(
    target: StationCollectionTarget,
    *,
    status: str,
    totals: dict[str, int] | None = None,
) -> None:
    message: dict[str, object] = {
        "station_id": target.source_station_id,
        "station_key": target.station_key,
        "station_name": target.name,
        "status": status,
    }

    if totals is not None:
        message.update(totals)

    print(
        json.dumps(
            message,
            ensure_ascii=False,
        ),
        flush=True,
    )


def _positive_int(value: str) -> int:
    parsed = int(value)

    if parsed <= 0:
        raise argparse.ArgumentTypeError(
            "value must be a positive integer"
        )

    return parsed


def main() -> int:
    args = parse_args()

    try:
        totals = run_area_batch(args)
    except (
        OSError,
        ValueError,
        RuntimeError,
        psycopg.Error,
        requests.RequestException,
    ) as error:
        print(
            f"Area batch failed: {error}",
            file=sys.stderr,
        )
        return 1

    print(
        json.dumps(
            {
                "status": "succeeded",
                "area_code": args.area_code,
                "element_profile": args.element_profile,
                **totals,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import psycopg
import requests

from collector.database import connect_database
from collector.import_obsdl_stations import (
    import_obsdl_stations,
)
from collector.jma_obsdl_station_fetcher import (
    collect_obsdl_station_page,
)
from collector.observation_area_repository import (
    ObservationAreaTarget,
    list_domestic_observation_areas,
)
from collector.settings import DatabaseSettings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Collect and import JMA obsdl station "
            "pages for domestic observation areas."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/data/raw"),
    )
    parser.add_argument(
        "--request-delay",
        type=_nonnegative_float,
        default=5.0,
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


def run_batch(
    args: argparse.Namespace,
) -> dict[str, int]:
    connection = connect_database(DatabaseSettings())

    try:
        targets = list_domestic_observation_areas(
            connection
        )
    finally:
        connection.close()

    if args.start_area_code is not None:
        targets = tuple(
            target
            for target in targets
            if target.area_code >= args.start_area_code
        )

        if not targets:
            raise ValueError(
                "No areas were found at or after "
                f"{args.start_area_code}."
            )

    if args.limit is not None:
        targets = targets[: args.limit]

    totals = {
        "areas": 0,
        "parsed": 0,
        "inserted": 0,
        "updated": 0,
        "unchanged": 0,
        "matched": 0,
        "unmatched": 0,
    }

    for index, target in enumerate(targets):
        _print_area_status(
            target,
            status="starting",
        )

        collection = collect_obsdl_station_page(
            area_code=target.area_code,
            output_dir=args.output_dir,
        )
        ingestion_run_id, counts = (
            import_obsdl_stations(
                html_path=collection.html_path,
                metadata_path=collection.metadata_path,
                raw_root=args.output_dir,
            )
        )

        totals["areas"] += 1

        for key in (
            "parsed",
            "inserted",
            "updated",
            "unchanged",
            "matched",
            "unmatched",
        ):
            totals[key] += getattr(counts, key)

        _print_area_status(
            target,
            status="succeeded",
            details={
                "ingestion_run_id": ingestion_run_id,
                "station_count":
                    collection.station_count,
                "active_count":
                    collection.active_count,
                "ended_count":
                    collection.ended_count,
                "inserted": counts.inserted,
                "updated": counts.updated,
                "unchanged": counts.unchanged,
                "matched": counts.matched,
                "unmatched": counts.unmatched,
            },
        )

        if index < len(targets) - 1:
            time.sleep(args.request_delay)

    return totals


def _print_area_status(
    target: ObservationAreaTarget,
    *,
    status: str,
    details: dict[str, object] | None = None,
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


def _positive_int(value: str) -> int:
    parsed = int(value)

    if parsed <= 0:
        raise argparse.ArgumentTypeError(
            "value must be a positive integer"
        )

    return parsed


def _nonnegative_float(value: str) -> float:
    parsed = float(value)

    if parsed < 0:
        raise argparse.ArgumentTypeError(
            "value must not be negative"
        )

    return parsed


def main() -> int:
    args = parse_args()

    try:
        totals = run_batch(args)
    except (
        OSError,
        ValueError,
        RuntimeError,
        psycopg.Error,
        requests.RequestException,
    ) as error:
        print(
            f"Station catalog batch failed: {error}",
            file=sys.stderr,
        )
        return 1

    print(
        json.dumps(
            {
                "status": "succeeded",
                **totals,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

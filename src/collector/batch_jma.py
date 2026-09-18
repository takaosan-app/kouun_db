from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

import psycopg
import requests

from collector.date_ranges import DateRange, split_into_months
from collector.import_jma_csv import import_jma_csv
from collector.jma_elements import (
    ELEMENT_PROFILES,
    ElementRequest,
)
from collector.jma_fetcher import collect_jma_data
from collector.jma_metadata import load_jma_source_file
from collector.models import ObservationSourceFileRecord


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect and import monthly JMA observations."
    )
    parser.add_argument("--station-id", required=True)
    parser.add_argument("--station-key", required=True)
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
        help="Seconds to wait after each new download.",
    )
    parser.add_argument(
        "--element-profile",
        choices=tuple(ELEMENT_PROFILES),
        default="core",
    )
    return parser.parse_args()


def run_batch(args: argparse.Namespace) -> dict[str, int]:
    if args.request_delay < 5:
        raise ValueError(
            "request-delay must be at least 5 seconds."
        )

    elements = ELEMENT_PROFILES[args.element_profile]
    periods = split_into_months(
        args.start_date,
        args.end_date,
    )
    totals = {
        "months": 0,
        "downloaded": 0,
        "reused": 0,
        "parsed": 0,
        "inserted": 0,
        "updated": 0,
        "unchanged": 0,
        "revisions": 0,
    }

    for index, period in enumerate(periods):
        existing = find_existing_files(
            output_dir=args.output_dir,
            station_id=args.station_id,
            station_key=args.station_key,
            period=period,
            elements=elements,
        )

        if existing is None:
            collected = collect_jma_data(
                station_id=args.station_id,
                station_key=args.station_key,
                start_date=period.start,
                end_date=period.end,
                output_dir=args.output_dir,
                elements=elements,
            )
            csv_path = collected.csv_path
            metadata_path = collected.metadata_path
            reused = False
            totals["downloaded"] += 1
        else:
            csv_path, metadata_path = existing
            reused = True
            totals["reused"] += 1

        ingestion_run_id, counts = import_jma_csv(
            csv_path=csv_path,
            metadata_path=metadata_path,
            raw_root=args.output_dir,
        )

        totals["months"] += 1
        totals["parsed"] += counts.parsed
        totals["inserted"] += counts.inserted
        totals["updated"] += counts.updated
        totals["unchanged"] += counts.unchanged
        totals["revisions"] += counts.revisions

        print(
            json.dumps(
                {
                    "start_date": period.start.isoformat(),
                    "end_date": period.end.isoformat(),
                    "reused": reused,
                    "ingestion_run_id": ingestion_run_id,
                    "inserted": counts.inserted,
                    "updated": counts.updated,
                    "unchanged": counts.unchanged,
                }
            ),
            flush=True,
        )

        if (
            not reused
            and index < len(periods) - 1
        ):
            time.sleep(args.request_delay)

    return totals


def find_existing_files(
    *,
    output_dir: Path,
    station_id: str,
    station_key: str,
    period: DateRange,
    elements: tuple[ElementRequest, ...],
) -> tuple[Path, Path] | None:
    directory = (
        output_dir
        / "jma"
        / "obsdl"
        / station_id
        / f"{period.start.year:04d}"
        / f"{period.start.month:02d}"
    )
    pattern = (
        f"{station_key}_{station_id}_daily_"
        f"{period.start:%Y%m%d}_{period.end:%Y%m%d}_*.json"
    )

    for metadata_path in sorted(
        directory.glob(pattern),
        reverse=True,
    ):
        csv_path = metadata_path.with_suffix(".csv")

        if not csv_path.is_file():
            continue

        source_file = load_jma_source_file(
            metadata_path,
            csv_path,
            output_dir,
        )

        if (
            source_file.station_key == station_key
            and source_file.source_station_id == station_id
            and source_file.requested_start_date == period.start
            and source_file.requested_end_date == period.end
            and _matches_element_request(source_file, elements)
        ):
            return csv_path, metadata_path

    return None


def _matches_element_request(
    source_file: ObservationSourceFileRecord,
    elements: tuple[ElementRequest, ...],
) -> bool:
    raw_elements = source_file.metadata.get("elements")

    if not isinstance(raw_elements, list):
        return False

    actual: list[tuple[str, str]] = []

    for item in raw_elements:
        if not isinstance(item, dict):
            return False

        code = item.get("code")
        option = item.get("option")

        if not isinstance(code, str):
            return False

        if not isinstance(option, str):
            return False

        actual.append((code, option))

    expected = [
        (element["code"], element["option"])
        for element in elements
    ]

    return actual == expected


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
        print(f"Batch failed: {error}", file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "status": "succeeded",
                "element_profile": args.element_profile,
                **totals,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import requests

from collector.jma_fetcher import collect_jma_data
from collector.jma_elements import ELEMENT_PROFILES


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download daily observations from JMA."
    )
    parser.add_argument(
        "--station-id",
        default="s47656",
    )
    parser.add_argument(
        "--station-key",
        default="shizuoka",
    )
    parser.add_argument(
        "--start-date",
        type=date.fromisoformat,
        default=date(2026, 8, 1),
    )
    parser.add_argument(
        "--end-date",
        type=date.fromisoformat,
        default=date(2026, 8, 31),
    )
    parser.add_argument(
        "--element-profile",
        choices=tuple(ELEMENT_PROFILES),
        default="core",
        help="Elements to request from JMA.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/data/raw"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    elements = ELEMENT_PROFILES[args.element_profile]

    try:
        result = collect_jma_data(
            station_id=args.station_id,
            station_key=args.station_key,
            start_date=args.start_date,
            end_date=args.end_date,
            output_dir=args.output_dir,
            elements=elements,
        )
    except (
        OSError,
        UnicodeError,
        ValueError,
        requests.RequestException,
    ) as error:
        print(
            f"Collection failed: {error}",
            file=sys.stderr,
        )
        return 1

    print(
        json.dumps(
            {
                "csv_path": str(result.csv_path),
                "metadata_path": str(result.metadata_path),
                "row_count": result.row_count,
                "sha256": result.sha256,
                "element_profile": args.element_profile,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
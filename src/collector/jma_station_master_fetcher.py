from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

import requests

from collector.jma_fetcher import (
    create_session,
    write_atomically,
)
from collector.jma_station_master_parser import (
    parse_amedas_master_zip,
)

SOURCE_URL = (
    "https://www.jma.go.jp/jma/kishou/know/"
    "amedas/ame_master.zip"
)


@dataclass(frozen=True, slots=True)
class StationMasterCollectionResult:
    zip_path: Path
    metadata_path: Path
    effective_on: date
    source_row_count: int
    logical_station_count: int
    sha256: str


def collect_amedas_master(
    output_dir: Path,
) -> StationMasterCollectionResult:
    with create_session() as session:
        response = session.get(
            SOURCE_URL,
            timeout=30,
        )
        response.raise_for_status()

    content = response.content
    parsed = parse_amedas_master_zip(content)
    retrieved_at = datetime.now(timezone.utc)
    digest = hashlib.sha256(content).hexdigest()

    destination = (
        output_dir
        / "jma"
        / "amedas_master"
        / f"{parsed.effective_on.year:04d}"
        / f"{parsed.effective_on.month:02d}"
    )
    destination.mkdir(parents=True, exist_ok=True)

    timestamp = retrieved_at.strftime(
        "%Y%m%dT%H%M%S%fZ"
    )
    basename = (
        f"ame_master_{parsed.effective_on:%Y%m%d}_"
        f"{timestamp}"
    )
    zip_path = destination / f"{basename}.zip"
    metadata_path = destination / f"{basename}.json"

    logical_station_count = len(
        {
            station.official_station_number
            for station in parsed.stations
        }
    )

    metadata: dict[str, object] = {
        "source_key": "jma_amedas_master",
        "source": "Japan Meteorological Agency",
        "source_url": SOURCE_URL,
        "effective_on": parsed.effective_on.isoformat(),
        "source_csv_name": parsed.source_csv_name,
        "retrieved_at_utc": retrieved_at.isoformat(),
        "encoding": "cp932",
        "source_row_count": len(parsed.stations),
        "logical_station_count": logical_station_count,
        "byte_size": len(content),
        "sha256": digest,
        "content_type": response.headers.get(
            "Content-Type"
        ),
        "collector_version": "0.1.0",
        "request_parameters": {},
    }

    write_atomically(zip_path, content)
    write_atomically(
        metadata_path,
        json.dumps(
            metadata,
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8"),
    )

    return StationMasterCollectionResult(
        zip_path=zip_path,
        metadata_path=metadata_path,
        effective_on=parsed.effective_on,
        source_row_count=len(parsed.stations),
        logical_station_count=logical_station_count,
        sha256=digest,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download the JMA AMeDAS station master."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/data/raw"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        result = collect_amedas_master(args.output_dir)
    except (
        OSError,
        ValueError,
        requests.RequestException,
    ) as error:
        print(
            f"Station master collection failed: {error}",
            file=sys.stderr,
        )
        return 1

    print(
        json.dumps(
            {
                "zip_path": str(result.zip_path),
                "metadata_path": str(result.metadata_path),
                "effective_on": result.effective_on.isoformat(),
                "source_row_count": result.source_row_count,
                "logical_station_count": (
                    result.logical_station_count
                ),
                "sha256": result.sha256,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

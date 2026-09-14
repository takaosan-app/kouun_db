from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import requests

from collector.jma_fetcher import (
    create_session,
    write_atomically,
)
from collector.jma_obsdl_station_parser import (
    parse_obsdl_station_page,
)

SOURCE_URL = (
    "https://www.data.jma.go.jp/"
    "risk/obsdl/top/station"
)


@dataclass(frozen=True, slots=True)
class StationPageCollectionResult:
    html_path: Path
    metadata_path: Path
    station_count: int
    active_count: int
    ended_count: int
    sha256: str


def collect_obsdl_station_page(
    *,
    prefecture_code: str,
    output_dir: Path,
) -> StationPageCollectionResult:
    with create_session() as session:
        response = session.post(
            SOURCE_URL,
            data={"pd": prefecture_code},
            timeout=30,
        )
        response.raise_for_status()

    content = response.content
    parsed = parse_obsdl_station_page(
        content,
        prefecture_code,
    )
    retrieved_at = datetime.now(timezone.utc)
    digest = hashlib.sha256(content).hexdigest()

    active_count = sum(
        station.observation_ended_on is None
        for station in parsed.stations
    )
    ended_count = len(parsed.stations) - active_count

    destination = (
        output_dir
        / "jma"
        / "obsdl_station"
        / prefecture_code
        / f"{retrieved_at.year:04d}"
        / f"{retrieved_at.month:02d}"
    )
    destination.mkdir(parents=True, exist_ok=True)

    timestamp = retrieved_at.strftime(
        "%Y%m%dT%H%M%S%fZ"
    )
    basename = (
        f"station_{prefecture_code}_{timestamp}"
    )
    html_path = destination / f"{basename}.html"
    metadata_path = destination / f"{basename}.json"

    metadata: dict[str, object] = {
        "source_key": "jma_obsdl_station",
        "source": "Japan Meteorological Agency",
        "source_url": SOURCE_URL,
        "prefecture_code": prefecture_code,
        "retrieved_at_utc": retrieved_at.isoformat(),
        "encoding": "utf-8",
        "source_row_count": len(parsed.stations),
        "active_count": active_count,
        "ended_count": ended_count,
        "byte_size": len(content),
        "sha256": digest,
        "content_type": response.headers.get(
            "Content-Type"
        ),
        "collector_version": "0.1.0",
        "request_parameters": {
            "pd": prefecture_code,
        },
    }

    write_atomically(html_path, content)
    write_atomically(
        metadata_path,
        json.dumps(
            metadata,
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8"),
    )

    return StationPageCollectionResult(
        html_path=html_path,
        metadata_path=metadata_path,
        station_count=len(parsed.stations),
        active_count=active_count,
        ended_count=ended_count,
        sha256=digest,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download a JMA obsdl station page."
    )
    parser.add_argument(
        "--prefecture-code",
        required=True,
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
        result = collect_obsdl_station_page(
            prefecture_code=args.prefecture_code,
            output_dir=args.output_dir,
        )
    except (
        OSError,
        ValueError,
        requests.RequestException,
    ) as error:
        print(
            f"Station page collection failed: {error}",
            file=sys.stderr,
        )
        return 1

    print(
        json.dumps(
            {
                "html_path": str(result.html_path),
                "metadata_path": str(
                    result.metadata_path
                ),
                "station_count": result.station_count,
                "active_count": result.active_count,
                "ended_count": result.ended_count,
                "sha256": result.sha256,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

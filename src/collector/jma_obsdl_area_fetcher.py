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
from collector.jma_obsdl_area_parser import (
    parse_obsdl_area_page,
)

SOURCE_URL = (
    "https://www.data.jma.go.jp/"
    "risk/obsdl/top/station"
)


@dataclass(frozen=True, slots=True)
class AreaPageCollectionResult:
    html_path: Path
    metadata_path: Path
    area_count: int
    domestic_area_count: int
    sha256: str


def collect_obsdl_area_page(
    *,
    output_dir: Path,
) -> AreaPageCollectionResult:
    with create_session() as session:
        response = session.post(
            SOURCE_URL,
            data={"pd": "00"},
            timeout=30,
        )
        response.raise_for_status()

    content = response.content
    parsed = parse_obsdl_area_page(content)
    retrieved_at = datetime.now(timezone.utc)
    digest = hashlib.sha256(content).hexdigest()

    domestic_area_count = sum(
        area.area_code != "99"
        for area in parsed.areas
    )

    destination = (
        output_dir
        / "jma"
        / "obsdl_area"
        / f"{retrieved_at.year:04d}"
        / f"{retrieved_at.month:02d}"
    )
    destination.mkdir(parents=True, exist_ok=True)

    timestamp = retrieved_at.strftime(
        "%Y%m%dT%H%M%S%fZ"
    )
    basename = f"area_index_{timestamp}"
    html_path = destination / f"{basename}.html"
    metadata_path = destination / f"{basename}.json"

    metadata: dict[str, object] = {
        "source_key": "jma_obsdl_station",
        "source": "Japan Meteorological Agency",
        "source_url": SOURCE_URL,
        "retrieved_at_utc": retrieved_at.isoformat(),
        "encoding": "utf-8",
        "source_row_count": len(parsed.areas),
        "area_count": len(parsed.areas),
        "domestic_area_count": domestic_area_count,
        "byte_size": len(content),
        "sha256": digest,
        "content_type": response.headers.get(
            "Content-Type"
        ),
        "collector_version": "0.1.0",
        "request_parameters": {
            "pd": "00",
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

    return AreaPageCollectionResult(
        html_path=html_path,
        metadata_path=metadata_path,
        area_count=len(parsed.areas),
        domestic_area_count=domestic_area_count,
        sha256=digest,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download the JMA obsdl observation-area page."
        )
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
        result = collect_obsdl_area_page(
            output_dir=args.output_dir,
        )
    except (
        OSError,
        ValueError,
        requests.RequestException,
    ) as error:
        print(
            f"Area page collection failed: {error}",
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
                "area_count": result.area_count,
                "domestic_area_count":
                    result.domestic_area_count,
                "sha256": result.sha256,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

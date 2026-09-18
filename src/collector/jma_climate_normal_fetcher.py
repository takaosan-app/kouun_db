from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import requests

from collector.jma_fetcher import (
    create_session,
    write_atomically,
)

SOURCE_URL = (
    "https://www.data.jma.go.jp/stats/data/mdrr/"
    "normal/2020/data/normal_amedas_daily.zip"
)
RELEASE_KEY = "jma_amedas_2020_v5"

CSV_PATH_PATTERN = re.compile(
    r"^daily/area[0-9]{2}/"
    r"nml_amd_d_([0-9]{5})\.csv$"
)


@dataclass(frozen=True, slots=True)
class ClimateNormalCollectionResult:
    zip_path: Path
    metadata_path: Path
    station_file_count: int
    source_row_count: int
    sha256: str


def inspect_archive(
    content: bytes,
) -> tuple[int, int]:
    station_numbers: set[str] = set()
    source_row_count = 0

    try:
        with zipfile.ZipFile(
            io.BytesIO(content)
        ) as archive:
            for member in archive.infolist():
                match = CSV_PATH_PATTERN.fullmatch(
                    member.filename
                )
                if match is None:
                    continue

                station_number = match.group(1)

                if station_number in station_numbers:
                    raise ValueError(
                        "Duplicate station file in "
                        f"archive: {station_number}"
                    )

                station_numbers.add(station_number)

                with archive.open(member) as csv_file:
                    source_row_count += sum(
                        1 for line in csv_file if line.strip()
                    )
    except zipfile.BadZipFile as error:
        raise ValueError(
            "Downloaded climate-normal file is not "
            "a valid ZIP archive."
        ) from error

    if not station_numbers:
        raise ValueError(
            "No daily normal station files were found."
        )

    if source_row_count <= 0:
        raise ValueError(
            "Climate-normal archive contains no records."
        )

    return len(station_numbers), source_row_count


def collect_climate_normals(
    output_dir: Path,
) -> ClimateNormalCollectionResult:
    with create_session() as session:
        response = session.get(
            SOURCE_URL,
            timeout=120,
        )
        response.raise_for_status()

    content = response.content
    station_file_count, source_row_count = (
        inspect_archive(content)
    )
    retrieved_at = datetime.now(timezone.utc)
    digest = hashlib.sha256(content).hexdigest()

    destination = (
        output_dir
        / "jma"
        / "amedas_normals"
        / "2020"
        / "v5"
    )
    destination.mkdir(parents=True, exist_ok=True)

    timestamp = retrieved_at.strftime(
        "%Y%m%dT%H%M%S%fZ"
    )
    basename = (
        f"normal_amedas_daily_2020_v5_{timestamp}"
    )
    zip_path = destination / f"{basename}.zip"
    metadata_path = destination / f"{basename}.json"

    metadata: dict[str, object] = {
        "source_key": "jma_amedas_normals",
        "source": "Japan Meteorological Agency",
        "source_url": SOURCE_URL,
        "release_key": RELEASE_KEY,
        "normal_kind": "daily",
        "statistics_started_on": "1991-01-01",
        "statistics_ended_on": "2020-12-31",
        "version": "5",
        "retrieved_at_utc": retrieved_at.isoformat(),
        "encoding": "ascii",
        "station_file_count": station_file_count,
        "source_row_count": source_row_count,
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

    return ClimateNormalCollectionResult(
        zip_path=zip_path,
        metadata_path=metadata_path,
        station_file_count=station_file_count,
        source_row_count=source_row_count,
        sha256=digest,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download the official JMA daily "
            "AMeDAS climatological normals."
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
        result = collect_climate_normals(
            args.output_dir
        )
    except (
        OSError,
        ValueError,
        requests.RequestException,
    ) as error:
        print(
            f"Climate normal collection failed: {error}",
            file=sys.stderr,
        )
        return 1

    print(
        json.dumps(
            {
                "zip_path": str(result.zip_path),
                "metadata_path": str(
                    result.metadata_path
                ),
                "station_file_count": (
                    result.station_file_count
                ),
                "source_row_count": (
                    result.source_row_count
                ),
                "sha256": result.sha256,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

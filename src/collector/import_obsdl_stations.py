from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import psycopg

from collector.database import connect_database
from collector.jma_obsdl_station_metadata import (
    load_obsdl_station_source_file,
)
from collector.jma_obsdl_station_parser import (
    parse_obsdl_station_page,
)
from collector.models import (
    ObsdlStationPageSourceFileRecord,
    ParsedObsdlStationPage,
)
from collector.obsdl_station_catalog_repository import (
    resolve_obsdl_station_catalog,
)
from collector.obsdl_station_profile_repository import (
    ObsdlStationProfileCounts,
    upsert_obsdl_station_profiles,
)
from collector.settings import DatabaseSettings
from collector.source_file_repository import (
    fail_ingestion_run,
    finish_ingestion_run,
    register_source_file,
    start_ingestion_run,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import a JMA obsdl station page."
    )
    parser.add_argument(
        "html_path",
        type=Path,
        help="Downloaded station-selection HTML.",
    )
    parser.add_argument(
        "--metadata-path",
        type=Path,
        help="Metadata JSON; defaults to the HTML basename.",
    )
    parser.add_argument(
        "--raw-root",
        type=Path,
        default=Path("/data/raw"),
    )
    return parser.parse_args()


def import_obsdl_stations(
    html_path: Path,
    metadata_path: Path,
    raw_root: Path,
) -> tuple[int, ObsdlStationProfileCounts]:
    source_file = load_obsdl_station_source_file(
        metadata_path,
        html_path,
        raw_root,
    )
    page = parse_obsdl_station_page(
        html_path.read_bytes(),
        source_file.prefecture_code,
    )
    _validate_page(source_file, page)

    connection = connect_database(DatabaseSettings())
    ingestion_run_id: int | None = None

    try:
        source_file_id = register_source_file(
            connection,
            source_file,
        )
        ingestion_run_id = start_ingestion_run(
            connection,
            source_file_id,
        )
        connection.commit()

        try:
            catalog = resolve_obsdl_station_catalog(
                connection,
                page,
            )
            counts = upsert_obsdl_station_profiles(
                connection,
                source_file_id=source_file_id,
                page=page,
                catalog=catalog,
            )
            finish_ingestion_run(
                connection,
                ingestion_run_id,
                parsed=counts.parsed,
                inserted=counts.inserted,
                updated=counts.updated,
                unchanged=counts.unchanged,
                revisions=0,
            )
            connection.commit()
            return ingestion_run_id, counts

        except Exception as error:
            connection.rollback()
            fail_ingestion_run(
                connection,
                ingestion_run_id,
                str(error),
            )
            connection.commit()
            raise

    finally:
        connection.close()


def _validate_page(
    source_file: ObsdlStationPageSourceFileRecord,
    page: ParsedObsdlStationPage,
) -> None:
    if page.prefecture_code != source_file.prefecture_code:
        raise ValueError(
            "Parsed prefecture code does not match metadata."
        )

    if len(page.stations) != source_file.source_row_count:
        raise ValueError(
            "Station count does not match metadata."
        )

    active_count = sum(
        station.observation_ended_on is None
        for station in page.stations
    )
    ended_count = len(page.stations) - active_count

    if active_count != source_file.active_count:
        raise ValueError(
            "Active station count does not match metadata."
        )

    if ended_count != source_file.ended_count:
        raise ValueError(
            "Ended station count does not match metadata."
        )


def main() -> int:
    args = parse_args()
    metadata_path = (
        args.metadata_path
        if args.metadata_path is not None
        else args.html_path.with_suffix(".json")
    )

    try:
        ingestion_run_id, counts = import_obsdl_stations(
            html_path=args.html_path,
            metadata_path=metadata_path,
            raw_root=args.raw_root,
        )
    except (
        OSError,
        ValueError,
        RuntimeError,
        psycopg.Error,
    ) as error:
        print(
            f"Station page import failed: {error}",
            file=sys.stderr,
        )
        return 1

    print(
        json.dumps(
            {
                "ingestion_run_id": ingestion_run_id,
                "parsed": counts.parsed,
                "inserted": counts.inserted,
                "updated": counts.updated,
                "unchanged": counts.unchanged,
                "matched": counts.matched,
                "unmatched": counts.unmatched,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

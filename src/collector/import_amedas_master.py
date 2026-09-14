from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import psycopg

from collector.database import connect_database
from collector.jma_station_master_metadata import (
    load_amedas_master_source_file,
)
from collector.jma_station_master_parser import (
    parse_amedas_master_zip,
)
from collector.models import (
    AmedasMasterSourceFileRecord,
    ParsedAmedasMaster,
)
from collector.settings import DatabaseSettings
from collector.source_file_repository import (
    fail_ingestion_run,
    finish_ingestion_run,
    register_source_file,
    start_ingestion_run,
)
from collector.station_catalog_repository import (
    resolve_station_catalog,
)
from collector.station_version_repository import (
    StationVersionCounts,
    upsert_station_versions,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import a JMA AMeDAS station master."
    )
    parser.add_argument(
        "zip_path",
        type=Path,
        help="Path to the downloaded station master ZIP.",
    )
    parser.add_argument(
        "--metadata-path",
        type=Path,
        help="Metadata JSON; defaults to the ZIP basename.",
    )
    parser.add_argument(
        "--raw-root",
        type=Path,
        default=Path("/data/raw"),
    )
    return parser.parse_args()


def import_amedas_master(
    zip_path: Path,
    metadata_path: Path,
    raw_root: Path,
) -> tuple[int, StationVersionCounts]:
    source_file = load_amedas_master_source_file(
        metadata_path,
        zip_path,
        raw_root,
    )
    parsed = parse_amedas_master_zip(
        zip_path.read_bytes()
    )
    _validate_master(source_file, parsed)

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
            catalog = resolve_station_catalog(
                connection,
                parsed.stations,
            )
            counts = upsert_station_versions(
                connection,
                source_file_id=source_file_id,
                effective_on=parsed.effective_on,
                stations=parsed.stations,
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


def _validate_master(
    source_file: AmedasMasterSourceFileRecord,
    parsed: ParsedAmedasMaster,
) -> None:
    if parsed.effective_on != source_file.effective_on:
        raise ValueError(
            "Master effective date does not match metadata."
        )

    if (
        parsed.source_csv_name
        != source_file.source_csv_name
    ):
        raise ValueError(
            "Master CSV name does not match metadata."
        )

    if (
        len(parsed.stations)
        != source_file.source_row_count
    ):
        raise ValueError(
            "Master row count does not match metadata."
        )

    logical_station_count = len(
        {
            station.official_station_number
            for station in parsed.stations
        }
    )

    if (
        logical_station_count
        != source_file.logical_station_count
    ):
        raise ValueError(
            "Logical station count does not match metadata."
        )


def main() -> int:
    args = parse_args()
    metadata_path = (
        args.metadata_path
        if args.metadata_path is not None
        else args.zip_path.with_suffix(".json")
    )

    try:
        ingestion_run_id, counts = import_amedas_master(
            zip_path=args.zip_path,
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
            f"Station master import failed: {error}",
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
                "closed": counts.closed,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

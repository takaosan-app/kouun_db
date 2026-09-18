from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Collection
from datetime import date
from pathlib import Path

import psycopg

from collector.catalog_repository import resolve_catalog_ids
from collector.database import connect_database
from collector.jma_csv_parser import parse_jma_csv
from collector.jma_metadata import load_jma_source_file
from collector.models import (
    ObservationSourceFileRecord,
)
from collector.observation_repository import (
    UpsertCounts,
    upsert_observations,
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
        description="Import a downloaded JMA CSV into PostgreSQL."
    )
    parser.add_argument(
        "csv_path",
        type=Path,
        help="Path to the downloaded JMA CSV file.",
    )
    parser.add_argument(
        "--metadata-path",
        type=Path,
        help="Path to metadata JSON; defaults to the CSV basename.",
    )
    parser.add_argument(
        "--raw-root",
        type=Path,
        default=Path("/data/raw"),
        help="Root directory used for stored relative paths.",
    )
    return parser.parse_args()


def import_jma_csv(
    csv_path: Path,
    metadata_path: Path,
    raw_root: Path,
) -> tuple[int, UpsertCounts]:
    source_file = load_jma_source_file(
        metadata_path,
        csv_path,
        raw_root,
    )
    parsed = parse_jma_csv(csv_path.read_bytes())
    _validate_parsed_period(
        source_file,
        parsed.source_dates,
    )

    settings = DatabaseSettings()
    connection = connect_database(settings)
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
            element_keys = {record.element_key for record in parsed.observations}
            catalog = resolve_catalog_ids(
                connection,
                source_file,
                element_keys,
            )

            if catalog.station_name != parsed.station_name:
                raise ValueError(
                    "CSV station name does not match catalog: "
                    f"{parsed.station_name!r} != "
                    f"{catalog.station_name!r}"
                )

            counts = upsert_observations(
                connection,
                source_file_id,
                catalog,
                parsed.observations,
            )
            finish_ingestion_run(
                connection,
                ingestion_run_id,
                parsed=counts.parsed,
                inserted=counts.inserted,
                updated=counts.updated,
                unchanged=counts.unchanged,
                revisions=counts.revisions,
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


def _validate_parsed_period(
    source_file: ObservationSourceFileRecord,
    source_dates: Collection[date],
) -> None:
    observed_dates = set(source_dates)

    if len(observed_dates) != source_file.source_row_count:
        raise ValueError(
            "Parsed day count does not match metadata: "
            f"{len(observed_dates)} != "
            f"{source_file.source_row_count}"
        )

    if (
        source_file.requested_start_date is not None
        and min(observed_dates)
        != source_file.requested_start_date
    ):
        raise ValueError(
            "First CSV date does not match metadata."
        )

    if (
        source_file.requested_end_date is not None
        and max(observed_dates)
        != source_file.requested_end_date
    ):
        raise ValueError(
            "Last CSV date does not match metadata."
        )


def main() -> int:
    args = parse_args()
    metadata_path = (
        args.metadata_path
        if args.metadata_path is not None
        else args.csv_path.with_suffix(".json")
    )

    try:
        ingestion_run_id, counts = import_jma_csv(
            csv_path=args.csv_path,
            metadata_path=metadata_path,
            raw_root=args.raw_root,
        )
    except (OSError, ValueError, RuntimeError, psycopg.Error) as error:
        print(f"Import failed: {error}", file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "ingestion_run_id": ingestion_run_id,
                "parsed": counts.parsed,
                "inserted": counts.inserted,
                "updated": counts.updated,
                "unchanged": counts.unchanged,
                "revisions": counts.revisions,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

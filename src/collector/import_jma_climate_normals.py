from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import psycopg

from collector.climate_normal_catalog_repository import (
    resolve_climate_normal_catalog,
)
from collector.climate_normal_repository import (
    ClimateNormalCounts,
    upsert_climate_normal_series,
)
from collector.database import connect_database
from collector.jma_climate_normal_metadata import (
    load_climate_normal_source_file,
)
from collector.jma_climate_normal_parser import (
    ELEMENT_SPECS,
    iter_climate_normal_series,
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
        description=(
            "Import official JMA daily AMeDAS "
            "climatological normals."
        )
    )
    parser.add_argument(
        "zip_path",
        type=Path,
        help="Path to the downloaded normals ZIP.",
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


def import_climate_normals(
    zip_path: Path,
    metadata_path: Path,
    raw_root: Path,
) -> tuple[int, ClimateNormalCounts]:
    source_file = load_climate_normal_source_file(
        metadata_path,
        zip_path,
        raw_root,
    )
    content = zip_path.read_bytes()

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
            catalog = resolve_climate_normal_catalog(
                connection,
                release_key=source_file.release_key,
                element_keys={
                    element_key
                    for element_key, _divisor
                    in ELEMENT_SPECS.values()
                },
            )
            counts = upsert_climate_normal_series(
                connection,
                source_file_id=source_file_id,
                catalog=catalog,
                series=iter_climate_normal_series(
                    content
                ),
            )

            expected_count = (
                source_file.station_file_count
                * len(ELEMENT_SPECS)
                * 12
            )
            if counts.parsed != expected_count:
                raise ValueError(
                    "Parsed climate-normal series count "
                    f"does not match metadata: "
                    f"{counts.parsed} != {expected_count}"
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


def main() -> int:
    args = parse_args()
    metadata_path = (
        args.metadata_path
        if args.metadata_path is not None
        else args.zip_path.with_suffix(".json")
    )

    try:
        ingestion_run_id, counts = (
            import_climate_normals(
                zip_path=args.zip_path,
                metadata_path=metadata_path,
                raw_root=args.raw_root,
            )
        )
    except (
        OSError,
        ValueError,
        RuntimeError,
        psycopg.Error,
    ) as error:
        print(
            f"Climate normal import failed: {error}",
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
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

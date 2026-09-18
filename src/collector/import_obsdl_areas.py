from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import psycopg

from collector.database import connect_database
from collector.jma_obsdl_area_metadata import (
    load_obsdl_area_source_file,
)
from collector.jma_obsdl_area_parser import (
    parse_obsdl_area_page,
)
from collector.models import (
    ObsdlAreaPageSourceFileRecord,
    ParsedObsdlAreaPage,
)
from collector.obsdl_area_repository import (
    ObsdlAreaCounts,
    upsert_obsdl_areas,
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
        description="Import the JMA obsdl area page."
    )
    parser.add_argument(
        "html_path",
        type=Path,
        help="Downloaded observation-area HTML.",
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


def import_obsdl_areas(
    html_path: Path,
    metadata_path: Path,
    raw_root: Path,
) -> tuple[int, ObsdlAreaCounts]:
    source_file = load_obsdl_area_source_file(
        metadata_path,
        html_path,
        raw_root,
    )
    page = parse_obsdl_area_page(
        html_path.read_bytes()
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
            counts = upsert_obsdl_areas(
                connection,
                page,
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
    source_file: ObsdlAreaPageSourceFileRecord,
    page: ParsedObsdlAreaPage,
) -> None:
    area_count = len(page.areas)

    if area_count != source_file.area_count:
        raise ValueError(
            "Area count does not match metadata."
        )

    domestic_area_count = sum(
        area.area_code != "99"
        for area in page.areas
    )

    if (
        domestic_area_count
        != source_file.domestic_area_count
    ):
        raise ValueError(
            "Domestic area count does not match "
            "metadata."
        )


def main() -> int:
    args = parse_args()
    metadata_path = (
        args.metadata_path
        if args.metadata_path is not None
        else args.html_path.with_suffix(".json")
    )

    try:
        ingestion_run_id, counts = import_obsdl_areas(
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
            f"Area page import failed: {error}",
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

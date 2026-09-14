from __future__ import annotations

from pathlib import Path

from collector.models import ObservationSourceFileRecord
from collector.source_metadata import (
    optional_str,
    parse_date,
    parse_datetime,
    require_dict,
    require_int,
    require_str,
    validate_source_artifact,
)


def load_jma_source_file(
    metadata_path: Path,
    csv_path: Path,
    raw_root: Path,
) -> ObservationSourceFileRecord:
    artifact = validate_source_artifact(
        metadata_path=metadata_path,
        content_path=csv_path,
        raw_root=raw_root,
        content_label="CSV",
    )
    metadata = artifact.metadata

    return ObservationSourceFileRecord(
        source_key="jma_obsdl",
        station_key=require_str(
            metadata,
            "station_key",
        ),
        source_station_id=require_str(
            metadata,
            "station_id",
        ),
        storage_path=artifact.storage_path,
        sha256=artifact.sha256,
        retrieved_at=parse_datetime(
            require_str(metadata, "retrieved_at_utc"),
            "retrieved_at_utc",
        ),
        requested_start_date=parse_date(
            require_str(metadata, "start_date"),
            "start_date",
        ),
        requested_end_date=parse_date(
            require_str(metadata, "end_date"),
            "end_date",
        ),
        encoding=require_str(
            metadata,
            "encoding",
        ),
        content_type=optional_str(
            metadata,
            "content_type",
        ),
        byte_size=artifact.byte_size,
        source_row_count=require_int(
            metadata,
            "row_count",
        ),
        collector_version=require_str(
            metadata,
            "collector_version",
        ),
        request_parameters=require_dict(
            metadata,
            "request_parameters",
        ),
        metadata=metadata,
    )
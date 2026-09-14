from __future__ import annotations

from pathlib import Path

from collector.models import AmedasMasterSourceFileRecord
from collector.source_metadata import (
    SourceMetadataError,
    optional_str,
    parse_date,
    parse_datetime,
    require_dict,
    require_int,
    require_str,
    validate_source_artifact,
)


def load_amedas_master_source_file(
    metadata_path: Path,
    zip_path: Path,
    raw_root: Path,
) -> AmedasMasterSourceFileRecord:
    artifact = validate_source_artifact(
        metadata_path=metadata_path,
        content_path=zip_path,
        raw_root=raw_root,
        content_label="ZIP",
    )
    metadata = artifact.metadata
    source_key = require_str(
        metadata,
        "source_key",
    )

    if source_key != "jma_amedas_master":
        raise SourceMetadataError(
            f"Unexpected source key: {source_key}"
        )

    source_row_count = require_int(
        metadata,
        "source_row_count",
    )
    logical_station_count = require_int(
        metadata,
        "logical_station_count",
    )

    if source_row_count <= 0:
        raise SourceMetadataError(
            "Source row count must be positive."
        )

    if not 0 < logical_station_count <= source_row_count:
        raise SourceMetadataError(
            "Logical station count is invalid."
        )

    return AmedasMasterSourceFileRecord(
        source_key=source_key,
        storage_path=artifact.storage_path,
        sha256=artifact.sha256,
        retrieved_at=parse_datetime(
            require_str(metadata, "retrieved_at_utc"),
            "retrieved_at_utc",
        ),
        requested_start_date=None,
        requested_end_date=None,
        encoding=require_str(
            metadata,
            "encoding",
        ),
        content_type=optional_str(
            metadata,
            "content_type",
        ),
        byte_size=artifact.byte_size,
        source_row_count=source_row_count,
        collector_version=require_str(
            metadata,
            "collector_version",
        ),
        request_parameters=require_dict(
            metadata,
            "request_parameters",
        ),
        metadata=metadata,
        effective_on=parse_date(
            require_str(metadata, "effective_on"),
            "effective_on",
        ),
        source_csv_name=require_str(
            metadata,
            "source_csv_name",
        ),
        logical_station_count=logical_station_count,
    )
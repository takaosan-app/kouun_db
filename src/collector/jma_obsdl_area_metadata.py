from __future__ import annotations

from pathlib import Path

from collector.models import (
    ObsdlAreaPageSourceFileRecord,
)
from collector.source_metadata import (
    SourceMetadataError,
    optional_str,
    parse_datetime,
    require_dict,
    require_int,
    require_str,
    validate_source_artifact,
)


def load_obsdl_area_source_file(
    metadata_path: Path,
    html_path: Path,
    raw_root: Path,
) -> ObsdlAreaPageSourceFileRecord:
    artifact = validate_source_artifact(
        metadata_path=metadata_path,
        content_path=html_path,
        raw_root=raw_root,
        content_label="HTML",
    )
    metadata = artifact.metadata
    source_key = require_str(
        metadata,
        "source_key",
    )

    if source_key != "jma_obsdl_station":
        raise SourceMetadataError(
            f"Unexpected source key: {source_key}"
        )

    source_row_count = require_int(
        metadata,
        "source_row_count",
    )
    area_count = require_int(
        metadata,
        "area_count",
    )
    domestic_area_count = require_int(
        metadata,
        "domestic_area_count",
    )

    if source_row_count <= 0:
        raise SourceMetadataError(
            "Source row count must be positive."
        )

    if area_count != source_row_count:
        raise SourceMetadataError(
            "Area count does not match source row count."
        )

    if not 0 <= domestic_area_count <= area_count:
        raise SourceMetadataError(
            "Domestic area count is outside the "
            "valid range."
        )

    request_parameters = require_dict(
        metadata,
        "request_parameters",
    )

    if request_parameters.get("pd") != "00":
        raise SourceMetadataError(
            "Area page request parameter pd must be 00."
        )

    return ObsdlAreaPageSourceFileRecord(
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
        request_parameters=request_parameters,
        metadata=metadata,
        area_count=area_count,
        domestic_area_count=domestic_area_count,
    )

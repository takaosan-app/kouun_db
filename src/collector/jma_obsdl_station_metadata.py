from __future__ import annotations

import re
from pathlib import Path

from collector.models import (
    ObsdlStationPageSourceFileRecord,
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

PREFECTURE_CODE_PATTERN = re.compile(r"\d{2}")


def load_obsdl_station_source_file(
    metadata_path: Path,
    html_path: Path,
    raw_root: Path,
) -> ObsdlStationPageSourceFileRecord:
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

    prefecture_code = require_str(
        metadata,
        "prefecture_code",
    )

    if not PREFECTURE_CODE_PATTERN.fullmatch(
        prefecture_code
    ):
        raise SourceMetadataError(
            "Prefecture code must contain two digits."
        )

    source_row_count = require_int(
        metadata,
        "source_row_count",
    )
    active_count = require_int(
        metadata,
        "active_count",
    )
    ended_count = require_int(
        metadata,
        "ended_count",
    )

    if source_row_count <= 0:
        raise SourceMetadataError(
            "Source row count must be positive."
        )

    if active_count < 0 or ended_count < 0:
        raise SourceMetadataError(
            "Station counts must not be negative."
        )

    if active_count + ended_count != source_row_count:
        raise SourceMetadataError(
            "Active and ended station counts do not "
            "match the total."
        )

    request_parameters = require_dict(
        metadata,
        "request_parameters",
    )

    if request_parameters.get("pd") != prefecture_code:
        raise SourceMetadataError(
            "Requested prefecture code does not match "
            "metadata."
        )

    return ObsdlStationPageSourceFileRecord(
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
        prefecture_code=prefecture_code,
        active_count=active_count,
        ended_count=ended_count,
    )

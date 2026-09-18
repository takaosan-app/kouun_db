from __future__ import annotations

from pathlib import Path

from collector.models import (
    ClimateNormalSourceFileRecord,
)
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


def load_climate_normal_source_file(
    metadata_path: Path,
    zip_path: Path,
    raw_root: Path,
) -> ClimateNormalSourceFileRecord:
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
    if source_key != "jma_amedas_normals":
        raise SourceMetadataError(
            f"Unexpected source key: {source_key}"
        )

    release_key = require_str(
        metadata,
        "release_key",
    )
    if release_key != "jma_amedas_2020_v5":
        raise SourceMetadataError(
            f"Unexpected release key: {release_key}"
        )

    normal_kind = require_str(
        metadata,
        "normal_kind",
    )
    if normal_kind != "daily":
        raise SourceMetadataError(
            f"Unexpected normal kind: {normal_kind}"
        )

    statistics_started_on = parse_date(
        require_str(
            metadata,
            "statistics_started_on",
        ),
        "statistics_started_on",
    )
    statistics_ended_on = parse_date(
        require_str(
            metadata,
            "statistics_ended_on",
        ),
        "statistics_ended_on",
    )

    if (
        statistics_started_on.isoformat()
        != "1991-01-01"
        or statistics_ended_on.isoformat()
        != "2020-12-31"
    ):
        raise SourceMetadataError(
            "Unexpected climate-normal statistics period."
        )

    if require_str(metadata, "version") != "5":
        raise SourceMetadataError(
            "Unexpected climate-normal version."
        )

    station_file_count = require_int(
        metadata,
        "station_file_count",
    )
    source_row_count = require_int(
        metadata,
        "source_row_count",
    )

    if station_file_count <= 0:
        raise SourceMetadataError(
            "Station file count must be positive."
        )

    if source_row_count != station_file_count * 912:
        raise SourceMetadataError(
            "Source row count does not match the "
            "station file count."
        )

    return ClimateNormalSourceFileRecord(
        source_key=source_key,
        storage_path=artifact.storage_path,
        sha256=artifact.sha256,
        retrieved_at=parse_datetime(
            require_str(
                metadata,
                "retrieved_at_utc",
            ),
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
        release_key=release_key,
        normal_kind=normal_kind,
        station_file_count=station_file_count,
    )

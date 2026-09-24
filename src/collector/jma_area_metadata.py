from __future__ import annotations

import json
import re
from pathlib import Path

from collector.models import (
    AreaObservationSourceFileRecord,
    AreaObservationStation,
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


def load_jma_area_source_file(
    metadata_path: Path,
    csv_path: Path,
    raw_root: Path,
) -> AreaObservationSourceFileRecord:
    artifact = validate_source_artifact(
        metadata_path=metadata_path,
        content_path=csv_path,
        raw_root=raw_root,
        content_label="CSV",
    )
    metadata = artifact.metadata

    source_key = require_str(
        metadata,
        "source_key",
    )

    if source_key != "jma_obsdl":
        raise SourceMetadataError(
            f"Unexpected source key: {source_key}"
        )

    if require_str(
        metadata,
        "collection_scope",
    ) != "area":
        raise SourceMetadataError(
            "Collection scope must be area."
        )

    area_code = require_str(
        metadata,
        "area_code",
    )

    if not re.fullmatch(r"\d{2}", area_code):
        raise SourceMetadataError(
            "Area code must contain two digits."
        )

    capability_code = require_str(
        metadata,
        "capability_code",
    )

    if not re.fullmatch(
        r"\d{6}",
        capability_code,
    ):
        raise SourceMetadataError(
            "Capability code must contain six digits."
        )

    start_date = parse_date(
        require_str(metadata, "start_date"),
        "start_date",
    )
    end_date = parse_date(
        require_str(metadata, "end_date"),
        "end_date",
    )

    if start_date > end_date:
        raise SourceMetadataError(
            "Start date must not be later than end date."
        )

    row_count = require_int(
        metadata,
        "row_count",
    )
    expected_row_count = (
        end_date - start_date
    ).days + 1

    if row_count != expected_row_count:
        raise SourceMetadataError(
            "Row count does not match the date range."
        )

    stations = _read_stations(metadata)
    station_count = require_int(
        metadata,
        "station_count",
    )

    if station_count != len(stations):
        raise SourceMetadataError(
            "Station count does not match "
            "the station list."
        )

    observation_count = require_int(
        metadata,
        "observation_count",
    )

    if observation_count < 0:
        raise SourceMetadataError(
            "Observation count must not be negative."
        )

    request_parameters = require_dict(
        metadata,
        "request_parameters",
    )
    _validate_requested_station_ids(
        request_parameters,
        stations,
    )

    return AreaObservationSourceFileRecord(
        source_key=source_key,
        storage_path=artifact.storage_path,
        sha256=artifact.sha256,
        retrieved_at=parse_datetime(
            require_str(metadata, "retrieved_at_utc"),
            "retrieved_at_utc",
        ),
        requested_start_date=start_date,
        requested_end_date=end_date,
        encoding=require_str(
            metadata,
            "encoding",
        ),
        content_type=optional_str(
            metadata,
            "content_type",
        ),
        byte_size=artifact.byte_size,
        source_row_count=row_count,
        collector_version=require_str(
            metadata,
            "collector_version",
        ),
        request_parameters=request_parameters,
        metadata=metadata,
        area_code=area_code,
        capability_code=capability_code,
        stations=stations,
        observation_count=observation_count,
    )


def _read_stations(
    metadata: dict[str, object],
) -> tuple[AreaObservationStation, ...]:
    value = metadata.get("stations")

    if not isinstance(value, list) or not value:
        raise SourceMetadataError(
            "Metadata field 'stations' must be "
            "a non-empty list."
        )

    stations: list[AreaObservationStation] = []

    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise SourceMetadataError(
                "Station metadata must be an object "
                f"at index {index}."
            )

        stations.append(
            AreaObservationStation(
                source_station_id=require_str(
                    item,
                    "station_id",
                ),
                station_key=require_str(
                    item,
                    "station_key",
                ),
                station_name=require_str(
                    item,
                    "station_name",
                ),
            )
        )

    source_station_ids = [
        station.source_station_id
        for station in stations
    ]
    station_keys = [
        station.station_key
        for station in stations
    ]

    if len(source_station_ids) != len(
        set(source_station_ids)
    ):
        raise SourceMetadataError(
            "Source station IDs must be unique."
        )

    if len(station_keys) != len(set(station_keys)):
        raise SourceMetadataError(
            "Station keys must be unique."
        )

    return tuple(stations)


def _validate_requested_station_ids(
    request_parameters: dict[str, object],
    stations: tuple[
        AreaObservationStation,
        ...,
    ],
) -> None:
    raw_station_ids = request_parameters.get(
        "stationNumList"
    )

    if not isinstance(raw_station_ids, str):
        raise SourceMetadataError(
            "Request stationNumList must be "
            "a JSON string."
        )

    try:
        requested_station_ids = json.loads(
            raw_station_ids
        )
    except json.JSONDecodeError as error:
        raise SourceMetadataError(
            "Request stationNumList is not valid JSON."
        ) from error

    expected_station_ids = [
        station.source_station_id
        for station in stations
    ]

    if requested_station_ids != expected_station_ids:
        raise SourceMetadataError(
            "Requested station IDs do not match "
            "the station metadata."
        )

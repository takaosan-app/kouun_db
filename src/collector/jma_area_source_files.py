from __future__ import annotations

from pathlib import Path

from collector.date_ranges import DateRange
from collector.jma_area_metadata import (
    load_jma_area_source_file,
)
from collector.jma_elements import ElementRequest
from collector.models import (
    AreaObservationSourceFileRecord,
)
from collector.station_collection_groups import (
    StationCollectionGroup,
)


def find_existing_area_files(
    *,
    output_dir: Path,
    group: StationCollectionGroup,
    period: DateRange,
    elements: tuple[ElementRequest, ...],
) -> tuple[Path, Path] | None:
    directory = (
        output_dir
        / "jma"
        / "obsdl_multi"
        / group.area_code
        / group.capability_code
        / f"{period.start.year:04d}"
        / f"{period.start.month:02d}"
    )
    pattern = (
        f"area_{group.area_code}_"
        f"type_{group.capability_code}_daily_"
        f"{period.start:%Y%m%d}_"
        f"{period.end:%Y%m%d}_*.json"
    )

    for metadata_path in sorted(
        directory.glob(pattern),
        reverse=True,
    ):
        csv_path = metadata_path.with_suffix(".csv")

        if not csv_path.is_file():
            continue

        source_file = load_jma_area_source_file(
            metadata_path,
            csv_path,
            output_dir,
        )

        if (
            source_file.area_code
            == group.area_code
            and source_file.capability_code
            == group.capability_code
            and source_file.requested_start_date
            == period.start
            and source_file.requested_end_date
            == period.end
            and _matches_stations(
                source_file,
                group,
            )
            and _matches_elements(
                source_file.metadata,
                elements,
            )
        ):
            return csv_path, metadata_path

    return None


def _matches_stations(
    source_file: AreaObservationSourceFileRecord,
    group: StationCollectionGroup,
) -> bool:
    actual = [
        (
            station.source_station_id,
            station.station_key,
            station.station_name,
        )
        for station in source_file.stations
    ]
    expected = [
        (
            station.source_station_id,
            station.station_key,
            station.name,
        )
        for station in group.stations
    ]

    return actual == expected


def _matches_elements(
    metadata: dict[str, object],
    elements: tuple[ElementRequest, ...],
) -> bool:
    raw_elements = metadata.get("elements")

    if not isinstance(raw_elements, list):
        return False

    actual: list[tuple[str, str]] = []

    for item in raw_elements:
        if not isinstance(item, dict):
            return False

        code = item.get("code")
        option = item.get("option")

        if not isinstance(code, str):
            return False

        if not isinstance(option, str):
            return False

        actual.append((code, option))

    expected = [
        (
            element["code"],
            element["option"],
        )
        for element in elements
    ]

    return actual == expected

from __future__ import annotations

from datetime import date
from pathlib import Path

from collector.catalog_repository import (
    resolve_catalog_ids,
)
from collector.database import connect_database
from collector.jma_area_metadata import (
    load_jma_area_source_file,
)
from collector.jma_multi_csv_parser import (
    parse_jma_multi_csv,
)
from collector.jma_parse_issues import (
    record_empty_station_issue,
    record_jma_parse_issues,
)
from collector.models import (
    AreaObservationSourceFileRecord,
    AreaObservationStation,
    ObservationSourceFileRecord,
    ParsedJmaCsv,
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


def import_jma_area_csv(
    csv_path: Path,
    metadata_path: Path,
    raw_root: Path,
) -> tuple[int, UpsertCounts]:
    source_file = load_jma_area_source_file(
        metadata_path,
        csv_path,
        raw_root,
    )
    parsed_stations = parse_jma_multi_csv(
        csv_path.read_bytes()
    )
    _validate_parsed(
        source_file,
        parsed_stations,
    )

    connection = connect_database(
        DatabaseSettings()
    )
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
            inserted = 0
            updated = 0
            unchanged = 0

            start_date = (
                source_file.requested_start_date
            )
            end_date = (
                source_file.requested_end_date
            )

            if (
                start_date is None
                or end_date is None
            ):
                raise RuntimeError(
                    "Validated date range is missing."
                )

            for station, parsed in zip(
                source_file.stations,
                parsed_stations,
                strict=True,
            ):
                if not parsed.observations:
                    record_empty_station_issue(
                        connection,
                        station=station,
                        area_code=(
                            source_file.area_code
                        ),
                        capability_code=(
                            source_file.capability_code
                        ),
                        requested_start_date=(
                            start_date
                        ),
                        requested_end_date=end_date,
                        source_file_id=source_file_id,
                        ingestion_run_id=(
                            ingestion_run_id
                        ),
                    )
                    continue

                station_source_file = (
                    _make_station_source_file(
                        source_file,
                        station,
                    )
                )
                element_keys = {
                    record.element_key
                    for record in parsed.observations
                }
                catalog = resolve_catalog_ids(
                    connection,
                    station_source_file,
                    element_keys,
                )

                record_jma_parse_issues(
                    connection,
                    parsed=parsed,
                    catalog=catalog,
                    area_code=source_file.area_code,
                    capability_code=(
                        source_file.capability_code
                    ),
                    requested_start_date=start_date,
                    requested_end_date=end_date,
                    source_file_id=source_file_id,
                    ingestion_run_id=ingestion_run_id,
                )

                counts = upsert_observations(
                    connection,
                    source_file_id,
                    catalog,
                    parsed.observations,
                )
                inserted += counts.inserted
                updated += counts.updated
                unchanged += counts.unchanged

            totals = UpsertCounts(
                parsed=source_file.observation_count,
                inserted=inserted,
                updated=updated,
                unchanged=unchanged,
            )
            finish_ingestion_run(
                connection,
                ingestion_run_id,
                parsed=totals.parsed,
                inserted=totals.inserted,
                updated=totals.updated,
                unchanged=totals.unchanged,
                revisions=totals.revisions,
            )
            connection.commit()
            return ingestion_run_id, totals

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


def _validate_parsed(
    source_file: AreaObservationSourceFileRecord,
    parsed_stations: tuple[ParsedJmaCsv, ...],
) -> None:
    if len(parsed_stations) != len(
        source_file.stations
    ):
        raise ValueError(
            "Parsed station count does not match "
            "metadata."
        )

    parsed_observation_count = sum(
        len(parsed.observations)
        for parsed in parsed_stations
    )

    if (
        parsed_observation_count
        != source_file.observation_count
    ):
        raise ValueError(
            "Parsed observation count does not match "
            "metadata."
        )

    start_date = source_file.requested_start_date
    end_date = source_file.requested_end_date

    if start_date is None or end_date is None:
        raise ValueError(
            "Requested date range is missing."
        )

    expected_dates = _date_set(
        start_date,
        end_date,
    )

    for station, parsed in zip(
        source_file.stations,
        parsed_stations,
        strict=True,
    ):
        if parsed.station_name != station.station_name:
            raise ValueError(
                "Parsed station name does not match "
                f"metadata: {parsed.station_name!r} "
                f"!= {station.station_name!r}"
            )

        observed_dates = set(
            parsed.source_dates
        )

        if observed_dates != expected_dates:
            raise ValueError(
                "Parsed date range does not match "
                f"metadata for {station.station_name}."
            )


def _date_set(
    start_date: date,
    end_date: date,
) -> set[date]:
    return {
        date.fromordinal(ordinal)
        for ordinal in range(
            start_date.toordinal(),
            end_date.toordinal() + 1,
        )
    }


def _make_station_source_file(
    source_file: AreaObservationSourceFileRecord,
    station: AreaObservationStation,
) -> ObservationSourceFileRecord:
    return ObservationSourceFileRecord(
        source_key=source_file.source_key,
        storage_path=source_file.storage_path,
        sha256=source_file.sha256,
        retrieved_at=source_file.retrieved_at,
        requested_start_date=(
            source_file.requested_start_date
        ),
        requested_end_date=(
            source_file.requested_end_date
        ),
        encoding=source_file.encoding,
        content_type=source_file.content_type,
        byte_size=source_file.byte_size,
        source_row_count=source_file.source_row_count,
        collector_version=(
            source_file.collector_version
        ),
        request_parameters=(
            source_file.request_parameters
        ),
        metadata=source_file.metadata,
        station_key=station.station_key,
        source_station_id=(
            station.source_station_id
        ),
    )

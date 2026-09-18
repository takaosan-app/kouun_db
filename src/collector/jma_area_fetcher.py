from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from collector.jma_elements import (
    CORE_ELEMENTS,
    ElementRequest,
)
from collector.jma_fetcher import (
    ENCODING,
    SOURCE_URL,
    create_session,
    write_atomically,
)
from collector.jma_multi_csv_parser import (
    parse_jma_multi_csv,
)
from collector.jma_request import build_jma_payload
from collector.models import ParsedJmaCsv
from collector.station_collection_repository import (
    StationCollectionTarget,
)


@dataclass(frozen=True, slots=True)
class AreaCollectionResult:
    csv_path: Path
    metadata_path: Path
    row_count: int
    station_count: int
    observation_count: int
    sha256: str


def collect_jma_area_data(
    *,
    area_code: str,
    capability_code: str,
    stations: tuple[
        StationCollectionTarget,
        ...,
    ],
    start_date: date,
    end_date: date,
    output_dir: Path,
    elements: tuple[
        ElementRequest,
        ...,
    ] = CORE_ELEMENTS,
) -> AreaCollectionResult:
    _validate_parameters(
        area_code=area_code,
        capability_code=capability_code,
        stations=stations,
    )
    payload = build_jma_payload(
        start_date=start_date,
        end_date=end_date,
        station_ids=tuple(
            station.source_station_id
            for station in stations
        ),
        elements=elements,
    )

    with create_session() as session:
        response = session.post(
            SOURCE_URL,
            data=payload,
            timeout=60,
        )
        response.raise_for_status()

    parsed_stations = parse_jma_multi_csv(
        response.content
    )
    row_count = _validate_response(
        stations=stations,
        parsed_stations=parsed_stations,
        start_date=start_date,
        end_date=end_date,
    )
    retrieved_at = datetime.now(timezone.utc)
    digest = hashlib.sha256(
        response.content
    ).hexdigest()

    destination = (
        output_dir
        / "jma"
        / "obsdl_multi"
        / area_code
        / capability_code
        / f"{start_date.year:04d}"
        / f"{start_date.month:02d}"
    )
    destination.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = retrieved_at.strftime(
        "%Y%m%dT%H%M%S%fZ"
    )
    basename = (
        f"area_{area_code}_type_{capability_code}_daily_"
        f"{start_date:%Y%m%d}_"
        f"{end_date:%Y%m%d}_{timestamp}"
    )
    csv_path = destination / f"{basename}.csv"
    metadata_path = destination / f"{basename}.json"

    metadata: dict[str, object] = {
        "source_key": "jma_obsdl",
        "source": "Japan Meteorological Agency",
        "source_url": SOURCE_URL,
        "collection_scope": "area",
        "area_code": area_code,
        "capability_code": capability_code,
        "stations": [
            {
                "station_id":
                    station.source_station_id,
                "station_key":
                    station.station_key,
                "station_name":
                    station.name,
            }
            for station in stations
        ],
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "elements": elements,
        "request_parameters": payload,
        "retrieved_at_utc":
            retrieved_at.isoformat(),
        "encoding": ENCODING,
        "row_count": row_count,
        "station_count": len(stations),
        "observation_count": sum(
            len(parsed.observations)
            for parsed in parsed_stations
        ),
        "byte_size": len(response.content),
        "sha256": digest,
        "content_type": response.headers.get(
            "Content-Type"
        ),
        "collector_version": "0.1.0",
    }

    write_atomically(
        csv_path,
        response.content,
    )
    write_atomically(
        metadata_path,
        json.dumps(
            metadata,
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8"),
    )

    return AreaCollectionResult(
        csv_path=csv_path,
        metadata_path=metadata_path,
        row_count=row_count,
        station_count=len(stations),
        observation_count=sum(
            len(parsed.observations)
            for parsed in parsed_stations
        ),
        sha256=digest,
    )


def _validate_parameters(
    *,
    area_code: str,
    capability_code: str,
    stations: tuple[
        StationCollectionTarget,
        ...,
    ],
) -> None:
    if not re.fullmatch(r"\d{2}", area_code):
        raise ValueError(
            "Area code must contain two digits."
        )

    if not re.fullmatch(
        r"\d{6}",
        capability_code,
    ):
        raise ValueError(
            "Capability code must contain six digits."
        )

    if not stations:
        raise ValueError(
            "At least one station is required."
        )

    if any(
        station.capability_code != capability_code
        for station in stations
    ):
        raise ValueError(
            "Stations must have the requested "
            "capability code."
        )


def _validate_response(
    *,
    stations: tuple[
        StationCollectionTarget,
        ...,
    ],
    parsed_stations: tuple[ParsedJmaCsv, ...],
    start_date: date,
    end_date: date,
) -> int:
    if len(parsed_stations) != len(stations):
        raise ValueError(
            "Parsed station count does not match "
            "the request."
        )

    expected_dates = {
        date.fromordinal(ordinal)
        for ordinal in range(
            start_date.toordinal(),
            end_date.toordinal() + 1,
        )
    }

    for target, parsed in zip(
        stations,
        parsed_stations,
        strict=True,
    ):
        if parsed.station_name != target.name:
            raise ValueError(
                "CSV station name does not match "
                f"the request: {parsed.station_name!r} "
                f"!= {target.name!r}"
            )

        observed_dates = set(
            parsed.source_dates
        )

        if observed_dates != expected_dates:
            raise ValueError(
                "CSV date range does not match "
                f"the request for {target.name}."
            )

    return len(expected_dates)

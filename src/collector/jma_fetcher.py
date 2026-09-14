from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from collector.jma_elements import CORE_ELEMENTS, ElementRequest

SOURCE_URL = "https://www.data.jma.go.jp/risk/obsdl/show/table"
ENCODING = "cp932"


@dataclass(frozen=True, slots=True)
class CollectionResult:
    csv_path: Path
    metadata_path: Path
    row_count: int
    sha256: str


def collect_jma_data(
    *,
    station_id: str,
    station_key: str,
    start_date: date,
    end_date: date,
    output_dir: Path,
    elements: tuple[ElementRequest, ...] = CORE_ELEMENTS,
) -> CollectionResult:
    _validate_parameters(
        station_id,
        station_key,
        start_date,
        end_date,
    )
    payload = build_payload(
        start_date,
        end_date,
        station_id,
        elements,
    )

    with create_session() as session:
        response = session.post(
            SOURCE_URL,
            data=payload,
            timeout=30,
        )
        response.raise_for_status()

    row_count = _validate_csv_period(
        response.content,
        start_date,
        end_date,
    )
    retrieved_at = datetime.now(timezone.utc)
    digest = hashlib.sha256(response.content).hexdigest()

    destination = (
        output_dir
        / "jma"
        / "obsdl"
        / station_id
        / f"{start_date.year:04d}"
        / f"{start_date.month:02d}"
    )
    destination.mkdir(parents=True, exist_ok=True)

    timestamp = retrieved_at.strftime("%Y%m%dT%H%M%S%fZ")
    basename = (
        f"{station_key}_{station_id}_daily_"
        f"{start_date:%Y%m%d}_{end_date:%Y%m%d}_{timestamp}"
    )
    csv_path = destination / f"{basename}.csv"
    metadata_path = destination / f"{basename}.json"

    write_atomically(csv_path, response.content)

    metadata: dict[str, object] = {
        "source": "Japan Meteorological Agency",
        "source_url": SOURCE_URL,
        "station_id": station_id,
        "station_key": station_key,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "elements": elements,
        "request_parameters": payload,
        "retrieved_at_utc": retrieved_at.isoformat(),
        "encoding": ENCODING,
        "row_count": row_count,
        "byte_size": len(response.content),
        "sha256": digest,
        "content_type": response.headers.get("Content-Type"),
        "collector_version": "0.1.0",
    }

    write_atomically(
        metadata_path,
        json.dumps(
            metadata,
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8"),
    )

    return CollectionResult(
        csv_path=csv_path,
        metadata_path=metadata_path,
        row_count=row_count,
        sha256=digest,
    )


def build_payload(
    start_date: date,
    end_date: date,
    station_id: str,
    elements: tuple[ElementRequest, ...] = CORE_ELEMENTS,
) -> dict[str, str]:
    return {
        "stationNumList": json.dumps([station_id]),
        "aggrgPeriod": "1",
        "elementNumList": json.dumps(
            [
                [element["code"], element["option"]]
                for element in elements
            ]
        ),
        "interAnnualType": "1",
        "ymdList": json.dumps(
            [
                str(start_date.year),
                str(end_date.year),
                str(start_date.month),
                str(end_date.month),
                str(start_date.day),
                str(end_date.day),
            ]
        ),
        "optionNumList": "[]",
        "downloadFlag": "true",
        "rmkFlag": "1",
        "disconnectFlag": "1",
        "youbiFlag": "0",
        "fukenFlag": "0",
        "kijiFlag": "0",
        "csvFlag": "1",
        "jikantaiFlag": "0",
        "jikantaiList": "[]",
        "ymdLiteral": "1",
    }


def create_session() -> requests.Session:
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "POST"}),
        respect_retry_after_header=True,
    )
    session = requests.Session()
    session.headers["User-Agent"] = (
        "kouun-db/0.1 "
        "(+https://github.com/takaosan-app/kouun_db)"
    )
    session.mount(
        "https://",
        HTTPAdapter(max_retries=retry),
    )
    return session


def _validate_parameters(
    station_id: str,
    station_key: str,
    start_date: date,
    end_date: date,
) -> None:
    if start_date > end_date:
        raise ValueError(
            "start_date must not be later than end_date."
        )

    if not re.fullmatch(r"[as]\d+", station_id):
        raise ValueError("Invalid station_id.")

    if not re.fullmatch(r"[a-z0-9_-]+", station_key):
        raise ValueError("Invalid station_key.")


def _validate_csv_period(
    content: bytes,
    start_date: date,
    end_date: date,
) -> int:
    if not content:
        raise ValueError("JMA returned an empty response.")

    if b"<html" in content[:1024].lower():
        raise ValueError("JMA returned HTML instead of CSV.")

    try:
        text = content.decode(ENCODING)
    except UnicodeDecodeError as error:
        raise ValueError(
            f"JMA response is not valid {ENCODING} text."
        ) from error

    observed_dates: list[date] = []

    for line in text.splitlines():
        match = re.match(
            r"^(\d{4})/(\d{1,2})/(\d{1,2}),",
            line,
        )
        if match is None:
            continue

        year, month, day = (
            int(value)
            for value in match.groups()
        )
        observed_dates.append(date(year, month, day))

    expected_count = (end_date - start_date).days + 1

    if len(observed_dates) != expected_count:
        raise ValueError(
            f"Expected {expected_count} daily rows, "
            f"received {len(observed_dates)}."
        )

    if (
        observed_dates[0] != start_date
        or observed_dates[-1] != end_date
    ):
        raise ValueError(
            "CSV date range does not match the request."
        )

    return len(observed_dates)


def write_atomically(
    path: Path,
    content: bytes,
) -> None:
    temporary_path = path.with_suffix(path.suffix + ".part")
    temporary_path.write_bytes(content)
    temporary_path.replace(path)

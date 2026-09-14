from __future__ import annotations

import csv
import io
import re
import zipfile
from datetime import date
from pathlib import Path

from collector.jma_station_record_parser import (
    AmedasMasterError,
    EXPECTED_HEADERS,
    normalize_row,
    parse_station,
)
from collector.models import (
    AmedasStationRecord,
    ParsedAmedasMaster,
)

ENCODING = "cp932"
MAX_CSV_SIZE = 10_000_000


def parse_amedas_master_zip(
    content: bytes,
) -> ParsedAmedasMaster:
    if not content:
        raise AmedasMasterError("ZIP content is empty.")

    try:
        archive = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile as error:
        raise AmedasMasterError(
            "Content is not a valid ZIP archive."
        ) from error

    with archive:
        members = [
            member
            for member in archive.infolist()
            if not member.is_dir()
        ]

        if len(members) != 1:
            raise AmedasMasterError(
                "ZIP must contain exactly one CSV file."
            )

        member = members[0]
        source_csv_name = Path(member.filename).name
        effective_on = _parse_effective_on(source_csv_name)

        if member.file_size > MAX_CSV_SIZE:
            raise AmedasMasterError(
                "CSV file exceeds the allowed size."
            )

        try:
            csv_content = archive.read(member)
        except (OSError, RuntimeError, zipfile.BadZipFile) as error:
            raise AmedasMasterError(
                "Could not read CSV from ZIP."
            ) from error

    try:
        text = csv_content.decode(ENCODING)
    except UnicodeDecodeError as error:
        raise AmedasMasterError(
            f"CSV is not valid {ENCODING} text."
        ) from error

    reader = csv.DictReader(
        io.StringIO(text, newline="")
    )

    if tuple(reader.fieldnames or ()) != EXPECTED_HEADERS:
        raise AmedasMasterError(
            "CSV header does not match the expected layout."
        )

    stations: list[AmedasStationRecord] = []

    for row_number, row in enumerate(reader, start=2):
        raw_record = normalize_row(row, row_number)

        if not any(raw_record.values()):
            continue

        station = parse_station(
            raw_record,
            row_number,
        )

        stations.append(station)

    if not stations:
        raise AmedasMasterError(
            "CSV contains no station records."
        )

    return ParsedAmedasMaster(
        effective_on=effective_on,
        source_csv_name=source_csv_name,
        stations=tuple(stations),
    )


def _parse_effective_on(filename: str) -> date:
    match = re.fullmatch(
        r"ame_master_(\d{4})(\d{2})(\d{2})\.csv",
        filename,
    )

    if match is None:
        raise AmedasMasterError(
            f"Unexpected CSV filename: {filename!r}"
        )

    try:
        return date(
            int(match.group(1)),
            int(match.group(2)),
            int(match.group(3)),
        )
    except ValueError as error:
        raise AmedasMasterError(
            f"Invalid effective date in {filename!r}."
        ) from error

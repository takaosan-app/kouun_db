from __future__ import annotations

import json
import re
from collections.abc import Collection
from datetime import date

from collector.jma_elements import (
    CORE_ELEMENTS,
    ElementRequest,
)


def build_jma_payload(
    *,
    start_date: date,
    end_date: date,
    station_ids: Collection[str],
    elements: tuple[
        ElementRequest,
        ...,
    ] = CORE_ELEMENTS,
) -> dict[str, str]:
    normalized_station_ids = tuple(station_ids)

    if start_date > end_date:
        raise ValueError(
            "start_date must not be later than end_date."
        )

    if not normalized_station_ids:
        raise ValueError(
            "At least one station ID is required."
        )

    invalid_station_ids = [
        station_id
        for station_id in normalized_station_ids
        if not re.fullmatch(
            r"[as]\d+",
            station_id,
        )
    ]

    if invalid_station_ids:
        raise ValueError(
            "Invalid station IDs: "
            + ", ".join(invalid_station_ids)
        )

    if len(set(normalized_station_ids)) != len(
        normalized_station_ids
    ):
        raise ValueError(
            "Station IDs must be unique."
        )

    return {
        "stationNumList": json.dumps(
            normalized_station_ids
        ),
        "aggrgPeriod": "1",
        "elementNumList": json.dumps(
            [
                [
                    element["code"],
                    element["option"],
                ]
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

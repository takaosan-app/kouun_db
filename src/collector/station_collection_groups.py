from __future__ import annotations

import re
from dataclasses import dataclass

from collector.station_collection_repository import (
    StationCollectionTarget,
)


@dataclass(frozen=True, slots=True)
class StationCollectionGroup:
    area_code: str
    capability_code: str
    stations: tuple[
        StationCollectionTarget,
        ...,
    ]


def group_station_collection_targets(
    area_code: str,
    targets: tuple[
        StationCollectionTarget,
        ...,
    ],
) -> tuple[StationCollectionGroup, ...]:
    if not re.fullmatch(r"\d{2}", area_code):
        raise ValueError(
            "Area code must contain two digits."
        )

    if not targets:
        raise ValueError(
            "At least one station target is required."
        )

    grouped: dict[
        str,
        list[StationCollectionTarget],
    ] = {}

    for target in targets:
        if not re.fullmatch(
            r"\d{6}",
            target.capability_code,
        ):
            raise ValueError(
                "Capability code must contain "
                "six digits: "
                f"{target.capability_code!r}"
            )

        grouped.setdefault(
            target.capability_code,
            [],
        ).append(target)

    return tuple(
        StationCollectionGroup(
            area_code=area_code,
            capability_code=capability_code,
            stations=tuple(
                sorted(
                    stations,
                    key=lambda station:
                        station.source_station_id,
                )
            ),
        )
        for capability_code, stations in sorted(
            grouped.items()
        )
    )

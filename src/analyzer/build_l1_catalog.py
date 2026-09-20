from __future__ import annotations

import json

from analyzer.l1_capability_repository import (
    sync_station_element_capabilities,
)
from analyzer.l1_catalog_repository import (
    sync_weather_areas,
    sync_weather_stations,
)
from analyzer.l1_station_relation_repository import (
    sync_weather_station_areas,
)
from collector.database import connect_database
from collector.settings import DatabaseSettings


def main() -> None:
    settings = DatabaseSettings()

    with connect_database(settings) as connection:
        changed_areas = sync_weather_areas(
            connection
        )
        changed_stations = sync_weather_stations(
            connection
        )
        inserted_station_areas, deleted_station_areas = (
            sync_weather_station_areas(
                connection
            )
        )
        (
            changed_station_capabilities,
            deleted_station_capabilities,
        ) = sync_station_element_capabilities(
            connection
        )
        connection.commit()

    print(
        json.dumps(
            {
                "status": "succeeded",
                "layer": "L1",
                "changed_areas": changed_areas,
                "changed_stations": changed_stations,
                "inserted_station_areas": inserted_station_areas,
                "deleted_station_areas": deleted_station_areas,
                "changed_station_capabilities":
                    changed_station_capabilities,
                "deleted_station_capabilities":
                    deleted_station_capabilities,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()

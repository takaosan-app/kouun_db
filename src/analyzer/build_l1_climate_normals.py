from __future__ import annotations

import json

from analyzer.l1_climate_normal_release_repository import (
    sync_climate_normal_releases,
)
from analyzer.l1_climate_normal_repository import (
    sync_daily_climate_normals,
)
from collector.database import connect_database
from collector.settings import DatabaseSettings


def main() -> None:
    settings = DatabaseSettings()

    with connect_database(settings) as connection:
        changed_releases = (
            sync_climate_normal_releases(
                connection
            )
        )
        normal_counts = sync_daily_climate_normals(
            connection
        )
        connection.commit()

    print(
        json.dumps(
            {
                "status": "succeeded",
                "layer": "L1",
                "dataset": "climate_normals",
                "changed_releases":
                    changed_releases,
                "staged": normal_counts.staged,
                "changed": normal_counts.changed,
                "deleted": normal_counts.deleted,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()

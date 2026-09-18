from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from viewer.database import connect_database

AREAS_QUERY = """
    SELECT
        area.area_code,
        area.area_name,
        COUNT(membership.station_id) AS station_count
    FROM weather.observation_area AS area
    JOIN weather.station_observation_area AS membership
        ON membership.area_code = area.area_code
    GROUP BY
        area.area_code,
        area.area_name
    ORDER BY
        area.area_code
"""


@st.cache_data(ttl=300)
def fetch_observation_areas() -> pd.DataFrame:
    with connect_database() as connection:
        rows: list[dict[str, Any]] = connection.execute(
            AREAS_QUERY
        ).fetchall()

    return pd.DataFrame(rows)


def select_observation_area(
    *,
    key: str,
) -> str | None:
    areas = fetch_observation_areas()

    if areas.empty:
        st.info(
            "選択できる都府県・地方がありません。"
        )
        return None

    labels = {
        str(row["area_code"]): (
            f'{row["area_name"]}'
            f'（{int(row["station_count"]):,}地点）'
        )
        for _, row in areas.iterrows()
    }

    selected = st.selectbox(
        "都府県・地方",
        options=list(labels),
        format_func=lambda value: labels[value],
        key=key,
    )

    return str(selected)

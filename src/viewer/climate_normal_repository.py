from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import streamlit as st

from viewer.database import connect_database

CLIMATE_NORMALS_QUERY = """
    WITH selected_series AS (
        SELECT
            series.month,
            series.material_years,
            series.statistics_started_year,
            series.statistics_ended_year,
            series.daily_values,
            series.daily_remarks,
            release.name AS release_name,
            release.release_key
        FROM weather.climate_normal_series AS series
        JOIN weather.climate_normal_release AS release
            ON release.id = series.release_id
        JOIN weather.station
            ON station.id = series.station_id
        JOIN weather.element
            ON element.id = series.element_id
        WHERE station.station_key = %s
          AND element.element_key = %s
          AND release.release_key = 'jma_amedas_2020_v5'
    ),
    requested_dates AS (
        SELECT
            generate_series(
                %s::date,
                %s::date,
                interval '1 day'
            )::date AS observed_on
    )
    SELECT
        requested_dates.observed_on,
        selected_series.daily_values[
            EXTRACT(
                DAY FROM requested_dates.observed_on
            )::integer
        ]::double precision AS normal_value,
        selected_series.daily_remarks[
            EXTRACT(
                DAY FROM requested_dates.observed_on
            )::integer
        ] AS normal_remark,
        selected_series.material_years,
        selected_series.statistics_started_year,
        selected_series.statistics_ended_year,
        selected_series.release_name,
        selected_series.release_key
    FROM requested_dates
    LEFT JOIN selected_series
        ON selected_series.month = EXTRACT(
            MONTH FROM requested_dates.observed_on
        )::integer
    ORDER BY requested_dates.observed_on
"""


@st.cache_data(ttl=300)
def fetch_climate_normals(
    station_key: str,
    element_key: str,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    with connect_database() as connection:
        rows: list[dict[str, Any]] = connection.execute(
            CLIMATE_NORMALS_QUERY,
            (
                station_key,
                element_key,
                start_date,
                end_date,
            ),
        ).fetchall()

    return pd.DataFrame(rows)

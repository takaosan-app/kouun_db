from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import streamlit as st

from viewer.database import connect_database

OBSERVATION_ROW_LIMIT = 10_001

OBSERVATION_CATALOG_QUERY = """
    WITH official_station AS (
        SELECT DISTINCT ON (mapping.station_id)
            mapping.station_id,
            mapping.source_station_id
                AS official_station_number
        FROM weather.station_source_id AS mapping
        JOIN weather.source
            ON source.id = mapping.source_id
        WHERE source.source_key = 'jma_amedas_master'
        ORDER BY
            mapping.station_id,
            mapping.valid_to DESC NULLS FIRST,
            mapping.id DESC
    )
    SELECT
        station.observation_area_code AS area_code,
        station.station_key,
        station.name AS station_name,
        official_station.official_station_number,
        element.element_key,
        element.name AS element_name,
        element.unit,
        element.value_kind,
        MIN(observation.observed_on) AS first_observed_on,
        MAX(observation.observed_on) AS last_observed_on,
        COUNT(*) AS observation_count
    FROM weather.observation
    JOIN weather.station
        ON station.id = observation.station_id
    JOIN weather.element
        ON element.id = observation.element_id
    LEFT JOIN official_station
        ON official_station.station_id = station.id
    WHERE station.observation_area_code = %s
    GROUP BY
        station.observation_area_code,
        station.station_key,
        station.name,
        official_station.official_station_number,
        element.element_key,
        element.name,
        element.unit,
        element.value_kind
    ORDER BY
        station.observation_area_code,
        official_station.official_station_number NULLS LAST,
        station.station_key,
        element.name,
        element.element_key
"""

OBSERVATIONS_QUERY = """
    SELECT
        observation.observed_on,
        element.name AS element_name,
        element.unit,
        element.value_kind,
        observation.value::double precision AS numeric_value,
        observation.text_value,
        observation.raw_value,
        observation.value_state,
        observation.quality_code,
        observation.no_phenomenon,
        observation.homogeneity_number,
        source_file.storage_path AS source_path,
        source_file.retrieved_at,
        observation.updated_at
    FROM weather.observation
    JOIN weather.station
        ON station.id = observation.station_id
    JOIN weather.element
        ON element.id = observation.element_id
    JOIN weather.source_file
        ON source_file.id = observation.source_file_id
    WHERE station.station_key = %s
      AND element.element_key = %s
      AND observation.observed_on BETWEEN %s AND %s
      AND observation.value_state = ANY(%s)
    ORDER BY observation.observed_on DESC
    LIMIT %s
"""


@st.cache_data(ttl=300)
def fetch_observation_catalog(
    area_code: str,
) -> pd.DataFrame:
    with connect_database() as connection:
        rows: list[dict[str, Any]] = connection.execute(
            OBSERVATION_CATALOG_QUERY,
            (area_code,)
        ).fetchall()

    return pd.DataFrame(rows)


@st.cache_data(ttl=60)
def fetch_observations(
    station_key: str,
    element_key: str,
    start_date: date,
    end_date: date,
    value_states: tuple[str, ...],
) -> pd.DataFrame:
    with connect_database() as connection:
        rows: list[dict[str, Any]] = connection.execute(
            OBSERVATIONS_QUERY,
            (
                station_key,
                element_key,
                start_date,
                end_date,
                list(value_states),
                OBSERVATION_ROW_LIMIT,
            ),
        ).fetchall()

    return pd.DataFrame(rows)

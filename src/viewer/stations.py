from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from viewer.areas import select_observation_area
from viewer.database import connect_database

CAPABILITY_NAMES = (
    "降水量",
    "風",
    "気温",
    "日照",
    "雪",
    "その他",
)

STATIONS_QUERY = """
    WITH latest_source_file AS (
        SELECT
            source_file.id,
            source_file.retrieved_at
        FROM weather.source_file
        JOIN weather.source
            ON source.id = source_file.source_id
        WHERE source.source_key = 'jma_obsdl_station'
          AND EXISTS (
              SELECT 1
              FROM weather.jma_obsdl_station_profile AS profile
              WHERE profile.source_file_id = source_file.id
                AND profile.area_code = %s
          )
        ORDER BY
            source_file.retrieved_at DESC,
            source_file.id DESC
        LIMIT 1
    )
    SELECT
        profile.name,
        profile.kana_name,
        station.station_key,
        official_id.source_station_id AS official_station_number,
        profile.source_station_id AS download_station_id,
        CASE
            WHEN profile.source_station_id LIKE 's%%'
                THEN '気象官署等'
            ELSE 'アメダス'
        END AS station_type,
        profile.capability_code,
        ST_Y(profile.location::geometry)::double precision
            AS latitude,
        ST_X(profile.location::geometry)::double precision
            AS longitude,
        profile.elevation_m::double precision AS elevation_m,
        profile.observation_ended_on,
        latest_source_file.retrieved_at
    FROM latest_source_file
    JOIN weather.jma_obsdl_station_profile AS profile
        ON profile.source_file_id = latest_source_file.id
    LEFT JOIN weather.station
        ON station.id = profile.station_id
    LEFT JOIN LATERAL (
        SELECT mapping.source_station_id
        FROM weather.station_source_id AS mapping
        JOIN weather.source
            ON source.id = mapping.source_id
        WHERE mapping.station_id = profile.station_id
          AND source.source_key = 'jma_amedas_master'
        ORDER BY
            mapping.valid_to DESC NULLS FIRST,
            mapping.id DESC
        LIMIT 1
    ) AS official_id
        ON true
    WHERE profile.area_code = %s
    ORDER BY
        official_id.source_station_id NULLS LAST,
        profile.source_station_id
"""


@st.cache_data(ttl=300)
def fetch_stations(
    area_code: str,
) -> pd.DataFrame:
    with connect_database() as connection:
        rows: list[dict[str, Any]] = connection.execute(
            STATIONS_QUERY,
            (area_code, area_code),
        ).fetchall()

    return pd.DataFrame(rows)


def format_capabilities(capability_code: str) -> str:
    available = [
        name
        for name, state in zip(
            CAPABILITY_NAMES,
            capability_code,
            strict=True,
        )
        if state != "0"
    ]

    return "、".join(available) if available else "なし"


def format_station_status(ended_on: object) -> str:
    if pd.isna(ended_on):
        return "現行"

    return f"終了（{ended_on}）"


def render_stations() -> None:
    st.header("観測所")

    area_code = select_observation_area(
        key="stations_area",
    )

    if area_code is None:
        return

    stations = fetch_stations(area_code)

    if stations.empty:
        st.info(
            "選択した地域の地点情報はまだ登録されていません。"
        )
        return

    current_count = int(
        stations["observation_ended_on"].isna().sum()
    )
    ended_count = len(stations) - current_count

    st.write(
        f"現行 {current_count:,}地点／"
        f"終了済み {ended_count:,}地点"
    )

    include_ended = st.checkbox(
        "終了済み観測所も表示する",
        value=False,
    )

    displayed = stations.copy()

    if not include_ended:
        displayed = displayed[
            displayed["observation_ended_on"].isna()
        ].copy()

    displayed["status"] = displayed[
        "observation_ended_on"
    ].map(format_station_status)
    displayed["available_categories"] = displayed[
        "capability_code"
    ].map(format_capabilities)

    st.subheader("地図")

    map_data = displayed[
        ["latitude", "longitude"]
    ].dropna()

    if map_data.empty:
        st.info("地図へ表示できる位置情報がありません。")
    else:
        st.map(
            map_data,
            latitude="latitude",
            longitude="longitude",
        )

    st.subheader("観測所一覧")

    table = displayed[
        [
            "name",
            "kana_name",
            "station_key",
            "official_station_number",
            "download_station_id",
            "station_type",
            "status",
            "capability_code",
            "available_categories",
            "latitude",
            "longitude",
            "elevation_m",
            "retrieved_at",
        ]
    ].rename(
        columns={
            "name": "観測所名",
            "kana_name": "カナ",
            "station_key": "station_key",
            "official_station_number": "公式観測所番号",
            "download_station_id": "ダウンロードID",
            "station_type": "種別",
            "status": "状態",
            "capability_code": "取得可能項目コード",
            "available_categories": "取得可能カテゴリ",
            "latitude": "緯度",
            "longitude": "経度",
            "elevation_m": "標高m",
            "retrieved_at": "情報取得日時",
        }
    )

    st.dataframe(
        table,
        hide_index=True,
        use_container_width=True,
    )

    st.caption(
        "取得可能カテゴリはコードの0以外を表示しています。"
        "コード1と2の意味は変換せず、元コードも併記しています。"
    )

from __future__ import annotations

from datetime import timedelta

import streamlit as st

from viewer.areas import select_observation_area
from viewer.climate_normal_repository import (
    fetch_climate_normals,
)
from viewer.observation_repository import (
    OBSERVATION_ROW_LIMIT,
    fetch_observation_catalog,
    fetch_observations,
)
from viewer.observation_views import (
    VALUE_STATE_LABELS,
    render_numeric_chart,
    render_observation_table,
)

MAX_PERIOD_DAYS = 3_660


def format_station_label(
    station_key: str,
    labels: dict[str, str],
) -> str:
    return labels.get(station_key, station_key)


def format_element_label(
    element_key: str,
    labels: dict[str, str],
) -> str:
    return labels.get(element_key, element_key)


def render_observations() -> None:
    st.header("観測データ")

    area_code = select_observation_area(
        key="observations_area",
    )

    if area_code is None:
        return

    catalog = fetch_observation_catalog(
        area_code,
    )

    if catalog.empty:
        st.info(
            "選択した地域の観測データは"
            "まだ登録されていません。"
        )
        return

    station_rows = catalog[
        [
            "station_key",
            "station_name",
            "official_station_number",
        ]
    ].drop_duplicates()

    station_labels: dict[str, str] = {}

    for _, row in station_rows.iterrows():
        station_key_value = str(row["station_key"])
        official_number = row["official_station_number"]

        if isinstance(official_number, str):
            label = (
                f'{official_number}：{row["station_name"]} '
                f'（{station_key_value}）'
            )
        else:
            label = (
                f'{row["station_name"]} '
                f'（{station_key_value}）'
            )

        station_labels[station_key_value] = label

    station_key = st.selectbox(
        "観測所",
        options=list(station_labels),
        format_func=lambda value: format_station_label(
            value,
            station_labels,
        ),
    )

    if station_key is None:
        st.info("選択できる観測所がありません。")
        return

    elements = catalog[
        catalog["station_key"] == station_key
    ].copy()
    element_labels: dict[str, str] = {
        str(row["element_key"]): (
            f'{row["element_name"]}（{row["unit"]}）'
        )
        for _, row in elements.iterrows()
    }

    element_key = st.selectbox(
        "観測項目",
        options=list(element_labels),
        format_func=lambda value: format_element_label(
            value,
            element_labels,
        ),
    )

    if element_key is None:
        st.info("選択できる観測項目がありません。")
        return

    selected = elements[
        elements["element_key"] == element_key
    ].iloc[0]

    first_date = selected["first_observed_on"]
    last_date = selected["last_observed_on"]
    default_start_date = max(
        first_date,
        last_date - timedelta(days=89),
    )

    date_columns = st.columns(2)
    start_date = date_columns[0].date_input(
        "開始日",
        value=default_start_date,
        min_value=first_date,
        max_value=last_date,
    )
    end_date = date_columns[1].date_input(
        "終了日",
        value=last_date,
        min_value=first_date,
        max_value=last_date,
    )

    selected_states: list[str] = st.multiselect(
        "品質状態",
        options=list(VALUE_STATE_LABELS),
        default=list(VALUE_STATE_LABELS),
        format_func=lambda value: (
            VALUE_STATE_LABELS[value]
        ),
    )

    if start_date > end_date:
        st.error("開始日は終了日以前にしてください。")
        return

    if (end_date - start_date).days > MAX_PERIOD_DAYS:
        st.error("一度に表示できる期間は10年以内です。")
        return

    if not selected_states:
        st.info("品質状態を1つ以上選択してください。")
        return

    observations = fetch_observations(
        station_key=station_key,
        element_key=element_key,
        start_date=start_date,
        end_date=end_date,
        value_states=tuple(selected_states),
    )

    if observations.empty:
        st.info("選択条件に該当する観測値はありません。")
        return

    if len(observations) >= OBSERVATION_ROW_LIMIT:
        st.warning(
            "検索結果が10,000件を超えたため、"
            "先頭10,000件だけを表示します。"
        )
        observations = observations.iloc[:10_000].copy()

    st.write(f"表示件数：{len(observations):,}件")

    if selected["value_kind"] == "numeric":
        normals = fetch_climate_normals(
            station_key=station_key,
            element_key=element_key,
            start_date=start_date,
            end_date=end_date,
        )

        st.subheader("時系列グラフ")
        render_numeric_chart(
            observations,
            start_date=start_date,
            end_date=end_date,
            element_name=str(selected["element_name"]),
            unit=str(selected["unit"]),
            normals=normals,
        )
    else:
        st.info(
            "風向・天気概況は数値グラフへ変換せず、"
            "表で表示します。"
        )

    st.subheader("観測値一覧")
    render_observation_table(observations)

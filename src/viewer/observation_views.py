from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

VALUE_STATE_LABELS = {
    "observed": "正常値",
    "questionable": "利用上注意",
    "missing": "欠測",
    "not_observed": "未観測",
}


def format_display_value(row: pd.Series) -> object:
    if pd.notna(row["numeric_value"]):
        return row["numeric_value"]

    if pd.notna(row["text_value"]):
        return row["text_value"]

    return ""


def format_no_phenomenon(value: object) -> str:
    if pd.isna(value):
        return "対象外"

    return "あり" if bool(value) else "なし"


def render_numeric_chart(
    observations: pd.DataFrame,
    *,
    start_date: date,
    end_date: date,
    element_name: str,
    unit: str,
) -> None:
    chart = observations[
        ["observed_on", "numeric_value"]
    ].copy()
    chart["observed_on"] = pd.to_datetime(
        chart["observed_on"]
    )
    chart = chart.set_index("observed_on")
    chart = chart.reindex(
        pd.date_range(start_date, end_date, freq="D")
    )

    if chart["numeric_value"].notna().sum() == 0:
        st.info("グラフへ表示できる数値がありません。")
        return

    chart = chart.rename(
        columns={
            "numeric_value": f"{element_name}（{unit}）",
        }
    )

    st.line_chart(chart)

    st.caption(
        "欠測・未観測・未取得の日はゼロに変換せず、"
        "グラフ上の空白として扱います。"
    )


def render_observation_table(
    observations: pd.DataFrame,
) -> None:
    table = observations.copy()
    table["display_value"] = table.apply(
        format_display_value,
        axis=1,
    )
    table["quality"] = (
        table["value_state"]
        .map(VALUE_STATE_LABELS)
        .fillna(table["value_state"])
    )
    table["no_phenomenon_display"] = table[
        "no_phenomenon"
    ].map(format_no_phenomenon)

    table = table[
        [
            "observed_on",
            "element_name",
            "display_value",
            "unit",
            "quality",
            "quality_code",
            "no_phenomenon_display",
            "homogeneity_number",
            "raw_value",
            "source_path",
            "retrieved_at",
            "updated_at",
        ]
    ].rename(
        columns={
            "observed_on": "対象日",
            "element_name": "観測項目",
            "display_value": "値",
            "unit": "単位",
            "quality": "品質状態",
            "quality_code": "気象庁品質コード",
            "no_phenomenon_display": "現象なしフラグ",
            "homogeneity_number": "均質番号",
            "raw_value": "原文値",
            "source_path": "原本ファイル",
            "retrieved_at": "取得日時",
            "updated_at": "DB更新日時",
        }
    )

    st.dataframe(
        table,
        hide_index=True,
        use_container_width=True,
    )
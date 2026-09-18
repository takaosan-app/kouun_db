from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from viewer.areas import fetch_observation_areas
from viewer.issue_repository import (
    ISSUE_ROW_LIMIT,
    fetch_collection_issues,
)

SEVERITY_LABELS = {
    "warning": "警告",
    "error": "エラー",
    "fatal": "致命的",
}


def render_collection_issues() -> None:
    st.header("収集警告・エラー")

    filter_columns = st.columns(3)

    unresolved_only = filter_columns[0].checkbox(
        "未解決だけ表示",
        value=True,
    )
    severities = filter_columns[1].multiselect(
        "重要度",
        options=list(SEVERITY_LABELS),
        default=list(SEVERITY_LABELS),
        format_func=SEVERITY_LABELS.get,
    )

    areas = fetch_observation_areas()
    area_labels = {
        "": "すべての地域",
    }

    for _, row in areas.iterrows():
        area_code = str(row["area_code"])
        area_labels[area_code] = (
            f'{area_code}：{row["area_name"]}'
        )

    selected_area = filter_columns[2].selectbox(
        "地域",
        options=list(area_labels),
        format_func=area_labels.get,
    )
    area_code = (
        selected_area
        if selected_area
        else None
    )

    if not severities:
        st.info(
            "重要度を1つ以上選択してください。"
        )
        return

    issues = fetch_collection_issues(
        unresolved_only=unresolved_only,
        severities=tuple(severities),
        area_code=area_code,
    )

    if issues.empty:
        st.success(
            "条件に該当する警告・エラーはありません。"
        )
        return

    metric_columns = st.columns(4)
    metric_columns[0].metric(
        "表示件数",
        f"{len(issues):,}",
    )

    for column, severity in zip(
        metric_columns[1:],
        ("warning", "error", "fatal"),
        strict=True,
    ):
        count = int(
            (issues["severity"] == severity).sum()
        )
        column.metric(
            SEVERITY_LABELS[severity],
            f"{count:,}",
        )

    if len(issues) >= ISSUE_ROW_LIMIT:
        st.warning(
            f"最大{ISSUE_ROW_LIMIT:,}件まで表示しています。"
        )

    displayed = issues.copy()
    displayed["severity"] = displayed[
        "severity"
    ].map(SEVERITY_LABELS)
    displayed["status"] = displayed[
        "resolved_at"
    ].map(
        lambda value: (
            "未解決"
            if pd.isna(value)
            else "解決済み"
        )
    )
    displayed["details"] = displayed[
        "details"
    ].map(
        lambda value: json.dumps(
            value,
            ensure_ascii=False,
        )
    )

    table = displayed[
        [
            "id",
            "severity",
            "status",
            "issue_code",
            "area_code",
            "area_name",
            "capability_code",
            "station_name",
            "observed_on",
            "element_key",
            "requested_start_date",
            "requested_end_date",
            "message",
            "ingestion_run_id",
            "source_file_id",
            "created_at",
            "resolved_at",
            "details",
        ]
    ].rename(
        columns={
            "id": "ID",
            "severity": "重要度",
            "status": "状態",
            "issue_code": "問題コード",
            "area_code": "地域コード",
            "area_name": "地域名",
            "capability_code": "観測所タイプ",
            "station_name": "観測所",
            "observed_on": "観測日",
            "element_key": "観測項目",
            "requested_start_date": "対象開始日",
            "requested_end_date": "対象終了日",
            "message": "内容",
            "ingestion_run_id": "取込ID",
            "source_file_id": "原本ID",
            "created_at": "記録日時",
            "resolved_at": "解決日時",
            "details": "詳細",
        }
    )

    st.dataframe(
        table,
        hide_index=True,
        use_container_width=True,
    )

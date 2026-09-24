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
    st.header("収集上の問題")

    action_tab, warning_tab = st.tabs(
        (
            "要対応",
            "警告履歴",
        )
    )

    area_labels = _build_area_labels()

    with action_tab:
        _render_action_required(area_labels)

    with warning_tab:
        _render_warning_history(area_labels)


def _render_action_required(
    area_labels: dict[str, str],
) -> None:
    st.caption(
        "再取得やプログラム修正など、"
        "対応が必要な未解決エラーを表示します。"
    )

    selected_area = st.selectbox(
        "地域",
        options=list(area_labels),
        format_func=area_labels.get,
        key="action_required_area",
    )
    area_code = selected_area or None

    issues = fetch_collection_issues(
        unresolved_only=True,
        severities=("error", "fatal"),
        area_code=area_code,
    )

    if issues.empty:
        st.success("対応が必要なエラーはありません。")
        return

    metric_columns = st.columns(3)
    metric_columns[0].metric(
        "要対応",
        f"{len(issues):,}",
    )
    metric_columns[1].metric(
        "エラー",
        f"{_severity_count(issues, 'error'):,}",
    )
    metric_columns[2].metric(
        "致命的",
        f"{_severity_count(issues, 'fatal'):,}",
    )

    _render_issue_table(issues)


def _render_warning_history(
    area_labels: dict[str, str],
) -> None:
    st.caption(
        "欠測や元データの不整合など、"
        "収集処理が安全に対処した事象の履歴です。"
        "原則として再処理は不要です。"
    )

    filter_columns = st.columns(2)

    selected_area = filter_columns[0].selectbox(
        "地域",
        options=list(area_labels),
        format_func=area_labels.get,
        key="warning_history_area",
    )
    area_code = selected_area or None

    unresolved_only = filter_columns[1].checkbox(
        "未処理だけ表示",
        value=False,
        key="warning_history_unresolved_only",
    )

    issues = fetch_collection_issues(
        unresolved_only=unresolved_only,
        severities=("warning",),
        area_code=area_code,
    )

    if issues.empty:
        st.info("条件に該当する警告はありません。")
        return

    metric_columns = st.columns(2)
    metric_columns[0].metric(
        "表示中の警告",
        f"{len(issues):,}",
    )
    metric_columns[1].metric(
        "未処理",
        f"{int(issues['resolved_at'].isna().sum()):,}",
    )

    _render_issue_table(issues)


def _build_area_labels() -> dict[str, str]:
    areas = fetch_observation_areas()
    area_labels = {
        "": "すべての地域",
    }

    for _, row in areas.iterrows():
        area_code = str(row["area_code"])
        area_labels[area_code] = (
            f'{area_code}：{row["area_name"]}'
        )

    return area_labels


def _severity_count(
    issues: pd.DataFrame,
    severity: str,
) -> int:
    return int(
        (issues["severity"] == severity).sum()
    )


def _render_issue_table(
    issues: pd.DataFrame,
) -> None:
    if len(issues) >= ISSUE_ROW_LIMIT:
        st.warning(
            f"新しいものから最大"
            f"{ISSUE_ROW_LIMIT:,}件まで表示しています。"
        )

    displayed = issues.copy()

    displayed["severity"] = displayed[
        "severity"
    ].map(SEVERITY_LABELS)

    displayed["status"] = displayed[
        "resolved_at"
    ].map(
        lambda value: (
            "未処理"
            if pd.isna(value)
            else "処理済み"
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
            "resolved_at": "処理日時",
            "details": "詳細",
        }
    )

    st.dataframe(
        table,
        hide_index=True,
        use_container_width=True,
    )

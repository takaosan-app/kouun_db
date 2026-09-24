from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from viewer.areas import fetch_observation_areas
from viewer.ingestion_repository import (
    INGESTION_ROW_LIMIT,
    fetch_ingestion_runs,
)

JAPAN_TIME_ZONE = ZoneInfo("Asia/Tokyo")

STATUS_LABELS = {
    "running": "実行中",
    "succeeded": "成功",
    "failed": "失敗",
}


def render_ingestion_runs() -> None:
    st.header("取込・実行履歴")
    st.caption(
        "DBに記録された取込処理の履歴です。"
        "Dockerおよびsystemdの標準出力は含みません。"
    )

    area_labels = _build_area_labels()
    today = date.today()

    first_row = st.columns(2)

    statuses = first_row[0].multiselect(
        "状態",
        options=list(STATUS_LABELS),
        default=list(STATUS_LABELS),
        format_func=STATUS_LABELS.get,
    )

    selected_area = first_row[1].selectbox(
        "地域",
        options=list(area_labels),
        format_func=area_labels.get,
    )
    area_code = selected_area or None

    second_row = st.columns(2)

    started_from = second_row[0].date_input(
        "実行日（開始）",
        value=today - timedelta(days=7),
    )
    started_to = second_row[1].date_input(
        "実行日（終了）",
        value=today,
    )

    if not statuses:
        st.info("状態を1つ以上選択してください。")
        return

    if started_from > started_to:
        st.error(
            "実行日の開始は終了以前にしてください。"
        )
        return

    runs = fetch_ingestion_runs(
        statuses=tuple(statuses),
        area_code=area_code,
        started_from=started_from,
        started_to=started_to,
    )

    if runs.empty:
        st.info("条件に該当する取込履歴はありません。")
        return

    metric_columns = st.columns(4)
    metric_columns[0].metric(
        "表示件数",
        f"{len(runs):,}",
    )
    metric_columns[1].metric(
        "成功",
        f"{_status_count(runs, 'succeeded'):,}",
    )
    metric_columns[2].metric(
        "失敗",
        f"{_status_count(runs, 'failed'):,}",
    )
    metric_columns[3].metric(
        "実行中",
        f"{_status_count(runs, 'running'):,}",
    )

    if len(runs) >= INGESTION_ROW_LIMIT:
        st.warning(
            f"新しいものから最大"
            f"{INGESTION_ROW_LIMIT:,}件まで表示しています。"
        )

    displayed = runs.copy()

    displayed["status"] = displayed[
        "status"
    ].map(STATUS_LABELS)

    displayed["started_at"] = displayed[
        "started_at"
    ].map(_format_datetime)

    displayed["finished_at"] = displayed[
        "finished_at"
    ].map(_format_datetime)

    displayed["duration_seconds"] = displayed[
        "duration_seconds"
    ].map(_format_duration)

    displayed["byte_size"] = displayed[
        "byte_size"
    ].map(_format_bytes)

    table = displayed[
        [
            "id",
            "status",
            "started_at",
            "finished_at",
            "duration_seconds",
            "area_code",
            "area_name",
            "capability_code",
            "requested_start_date",
            "requested_end_date",
            "station_count",
            "parsed_count",
            "inserted_count",
            "updated_count",
            "unchanged_count",
            "revision_count",
            "product_name",
            "source_file_id",
            "byte_size",
            "collector_version",
            "storage_path",
            "error_message",
        ]
    ].rename(
        columns={
            "id": "取込ID",
            "status": "状態",
            "started_at": "開始日時",
            "finished_at": "終了日時",
            "duration_seconds": "処理時間",
            "area_code": "地域コード",
            "area_name": "地域名",
            "capability_code": "観測所タイプ",
            "requested_start_date": "対象開始日",
            "requested_end_date": "対象終了日",
            "station_count": "観測所数",
            "parsed_count": "解析",
            "inserted_count": "追加",
            "updated_count": "更新",
            "unchanged_count": "未変更",
            "revision_count": "訂正",
            "product_name": "対象",
            "source_file_id": "原本ID",
            "byte_size": "原本サイズ",
            "collector_version": "collector版",
            "storage_path": "保存パス",
            "error_message": "エラー",
        }
    )

    st.dataframe(
        table,
        hide_index=True,
        use_container_width=True,
    )


def _build_area_labels() -> dict[str, str]:
    areas = fetch_observation_areas()
    labels = {
        "": "すべての地域",
    }

    for _, row in areas.iterrows():
        area_code = str(row["area_code"])
        labels[area_code] = (
            f'{area_code}：{row["area_name"]}'
        )

    return labels


def _status_count(
    runs: pd.DataFrame,
    status: str,
) -> int:
    return int(
        (runs["status"] == status).sum()
    )


def _format_datetime(
    value: datetime | None,
) -> str:
    if value is None or pd.isna(value):
        return "未完了"

    return value.astimezone(
        JAPAN_TIME_ZONE
    ).strftime("%Y-%m-%d %H:%M:%S")


def _format_duration(
    value: object,
) -> str:
    if value is None or pd.isna(value):
        return "実行中"

    seconds = float(value)

    if seconds < 60:
        return f"{seconds:.2f}秒"

    minutes, remaining_seconds = divmod(
        int(seconds),
        60,
    )

    if minutes < 60:
        return (
            f"{minutes}分"
            f"{remaining_seconds}秒"
        )

    hours, remaining_minutes = divmod(
        minutes,
        60,
    )
    return (
        f"{hours}時間"
        f"{remaining_minutes}分"
    )


def _format_bytes(
    value: object,
) -> str:
    if value is None or pd.isna(value):
        return "-"

    size = float(value)

    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:,.1f} {unit}"
        size /= 1024

    return "-"

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import streamlit as st

from viewer.database import connect_database

JAPAN_TIME_ZONE = ZoneInfo("Asia/Tokyo")

OVERVIEW_QUERY = """
    SELECT
        pg_database_size(current_database()) AS database_size_bytes,
        (
            SELECT COALESCE(
                SUM(pg_total_relation_size(class.oid)),
                0
            )::bigint
            FROM pg_class AS class
            JOIN pg_namespace AS namespace
                ON namespace.oid = class.relnamespace
            WHERE namespace.nspname = 'weather'
              AND class.relkind IN ('r', 'p', 'm')
        ) AS weather_size_bytes,
        (SELECT COUNT(*) FROM weather.station) AS station_count,
        (SELECT COUNT(*) FROM weather.station_version) AS station_version_count,
        (SELECT COUNT(*) FROM weather.observation) AS observation_count,
        (SELECT COUNT(*) FROM weather.source_file) AS source_file_count,
        (SELECT COUNT(*) FROM weather.ingestion_run) AS ingestion_run_count,
        (
            SELECT MAX(started_at)
            FROM weather.ingestion_run
        ) AS last_ingestion_started_at,
        (
            SELECT MAX(finished_at)
            FROM weather.ingestion_run
            WHERE status = 'succeeded'
        ) AS last_success_finished_at
"""

LATEST_RUN_QUERY = """
    SELECT
        ingestion_run.id,
        ingestion_run.status,
        ingestion_run.started_at,
        ingestion_run.finished_at,
        ingestion_run.parsed_count,
        ingestion_run.inserted_count,
        ingestion_run.updated_count,
        ingestion_run.unchanged_count,
        ingestion_run.revision_count,
        ingestion_run.error_message,
        source.product_name,
        source_file.storage_path
    FROM weather.ingestion_run
    JOIN weather.source_file
        ON source_file.id = ingestion_run.source_file_id
    JOIN weather.source
        ON source.id = source_file.source_id
    ORDER BY ingestion_run.started_at DESC, ingestion_run.id DESC
    LIMIT 1
"""


@st.cache_data(ttl=60)
def fetch_overview() -> tuple[dict[str, Any], dict[str, Any] | None]:
    with connect_database() as connection:
        metrics = connection.execute(OVERVIEW_QUERY).fetchone()
        latest_run = connection.execute(LATEST_RUN_QUERY).fetchone()

    if metrics is None:
        raise RuntimeError("DB概要を取得できませんでした。")

    return metrics, latest_run


def format_bytes(byte_size: int) -> str:
    value = float(byte_size)

    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:,.1f} {unit}"
        value /= 1024

    raise RuntimeError("容量の単位変換に失敗しました。")


def format_datetime(value: datetime | None) -> str:
    if value is None:
        return "未記録"

    return value.astimezone(JAPAN_TIME_ZONE).strftime(
        "%Y-%m-%d %H:%M:%S JST"
    )


def render_overview() -> None:
    metrics, latest_run = fetch_overview()

    st.header("DB概要")

    size_columns = st.columns(4)
    size_columns[0].metric(
        "DB全体",
        format_bytes(metrics["database_size_bytes"]),
    )
    size_columns[1].metric(
        "weatherスキーマ",
        format_bytes(metrics["weather_size_bytes"]),
    )
    size_columns[2].metric(
        "論理観測所",
        f'{metrics["station_count"]:,}',
    )
    size_columns[3].metric(
        "観測値",
        f'{metrics["observation_count"]:,}',
    )

    count_columns = st.columns(3)
    count_columns[0].metric(
        "観測所履歴",
        f'{metrics["station_version_count"]:,}',
    )
    count_columns[1].metric(
        "原本ファイル",
        f'{metrics["source_file_count"]:,}',
    )
    count_columns[2].metric(
        "取込実行",
        f'{metrics["ingestion_run_count"]:,}',
    )

    st.subheader("取込日時")
    st.write(
        "最終開始日時："
        f'{format_datetime(metrics["last_ingestion_started_at"])}'
    )
    st.write(
        "最終成功日時："
        f'{format_datetime(metrics["last_success_finished_at"])}'
    )

    st.subheader("最新の取込")

    if latest_run is None:
        st.info("取込履歴はまだありません。")
        return

    status = str(latest_run["status"])

    if status == "succeeded":
        st.success(f'取込ID {latest_run["id"]}：成功')
    elif status == "running":
        st.warning(f'取込ID {latest_run["id"]}：実行中')
    else:
        st.error(f'取込ID {latest_run["id"]}：失敗')

    st.write(f'対象：{latest_run["product_name"]}')
    st.write(f'開始：{format_datetime(latest_run["started_at"])}')
    st.write(f'終了：{format_datetime(latest_run["finished_at"])}')
    st.write(
        "件数："
        f'解析 {latest_run["parsed_count"]:,}／'
        f'追加 {latest_run["inserted_count"]:,}／'
        f'更新 {latest_run["updated_count"]:,}／'
        f'未変更 {latest_run["unchanged_count"]:,}／'
        f'訂正 {latest_run["revision_count"]:,}'
    )

    if latest_run["error_message"]:
        st.code(str(latest_run["error_message"]))

from __future__ import annotations

import psycopg
import streamlit as st
from pydantic import ValidationError

from viewer.database import get_database_status
from viewer.issues import render_collection_issues
from viewer.observations import render_observations
from viewer.overview import render_overview
from viewer.stations import render_stations


def main() -> None:
    st.set_page_config(
        page_title="kouun_db Viewer",
        page_icon="🌦️",
        layout="wide",
    )

    st.title("kouun_db データ確認Viewer")
    st.caption("収集した気象観測データを確認するための開発・管理用画面です。")

    try:
        status = get_database_status()
    except (psycopg.Error, ValidationError, RuntimeError) as error:
        st.error("データベースへ接続できませんでした。")
        st.code(str(error))
        return

    if status["read_only"]:
        st.success("読み取り専用でデータベースへ接続しました。")
    else:
        st.error("接続が読み取り専用になっていません。")
        return

    database_column, user_column, version_column = st.columns(3)

    database_column.metric(
        "データベース",
        str(status["database_name"]),
    )
    user_column.metric(
        "接続ユーザー",
        str(status["database_user"]),
    )
    version_column.metric(
        "PostgreSQL",
        str(status["server_version"]),
    )

    page = st.sidebar.radio(
        "表示する画面",
        (
            "DB概要",
            "観測所",
            "観測データ",
            "収集警告・エラー",
        ),
    )

    st.divider()

    try:
        if page == "DB概要":
            render_overview()
        elif page == "観測所":
            render_stations()
        elif page == "観測データ":
            render_observations()
        elif page == "収集警告・エラー":
            render_collection_issues()
    except (psycopg.Error, RuntimeError) as error:
        st.error("画面のデータを取得できませんでした。")
        st.code(str(error))


if __name__ == "__main__":
    main()

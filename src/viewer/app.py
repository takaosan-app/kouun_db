from __future__ import annotations

import psycopg
import streamlit as st
from pydantic import ValidationError

from viewer.database import get_database_status


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

    st.info("現在はV0です。次の段階でDB概要、観測所、観測値を追加します。")


if __name__ == "__main__":
    main()

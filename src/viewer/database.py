from __future__ import annotations

from typing import Any

import psycopg
from psycopg.rows import dict_row
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class ViewerDatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DB_",
        extra="ignore",
    )

    host: str
    port: int = 5432
    name: str
    user: str
    password: SecretStr


def connect_database(
    settings: ViewerDatabaseSettings | None = None,
) -> psycopg.Connection[dict[str, Any]]:
    database_settings = settings or ViewerDatabaseSettings()

    return psycopg.connect(
        host=database_settings.host,
        port=database_settings.port,
        dbname=database_settings.name,
        user=database_settings.user,
        password=database_settings.password.get_secret_value(),
        autocommit=True,
        row_factory=dict_row,
        connect_timeout=5,
        options="-c default_transaction_read_only=on",
    )


def get_database_status() -> dict[str, Any]:
    query = """
        SELECT
            current_database() AS database_name,
            current_user AS database_user,
            current_setting('transaction_read_only')::boolean AS read_only,
            current_setting('server_version') AS server_version
    """

    with connect_database() as connection:
        row = connection.execute(query).fetchone()

    if row is None:
        raise RuntimeError("データベースの接続情報を取得できませんでした。")

    return row

from __future__ import annotations

import psycopg

from collector.settings import DatabaseSettings


def connect_database(
    settings: DatabaseSettings,
) -> psycopg.Connection:
    return psycopg.connect(
        host=settings.host,
        port=settings.port,
        dbname=settings.name,
        user=settings.user,
        password=settings.password.get_secret_value(),
        autocommit=False,
    )

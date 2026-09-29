from __future__ import annotations

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppDatabaseSettings(BaseSettings):
    """Connection to the app database (Supabase)."""

    model_config = SettingsConfigDict(
        env_prefix="APP_DB_",
        extra="ignore",
    )

    host: str
    port: int = 5432
    name: str
    user: str
    password: SecretStr
    sslmode: str = "require"

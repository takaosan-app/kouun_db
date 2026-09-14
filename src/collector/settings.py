from __future__ import annotations

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DB_",
        extra="ignore",
    )

    host: str
    port: int = 5432
    name: str
    user: str
    password: SecretStr
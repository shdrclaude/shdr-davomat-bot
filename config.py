"""Loyiha konfiguratsiyasi. Barcha sozlamalar .env dan olinadi."""
from __future__ import annotations

from zoneinfo import ZoneInfo

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    bot_token: str
    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    super_admins: str = ""
    supervisor_usernames: str = ""
    log_chat_id: int | None = None
    tz_name: str = "Asia/Tashkent"

    @field_validator("log_chat_id", mode="before")
    @classmethod
    def _empty_to_none(cls, v):
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return None
        return v

    @property
    def async_database_url(self) -> str:
        url = self.database_url
        url = url.replace("postgres://", "postgresql://", 1) if url.startswith("postgres://") else url
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1) if url.startswith("postgresql://") else url
        return url

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.tz_name)

    @property
    def super_admin_ids(self) -> list[int]:
        return [int(x) for x in self.super_admins.replace(" ", "").split(",") if x]

    @property
    def supervisor_username_set(self) -> set[str]:
        return {u.strip().lstrip("@").lower() for u in self.supervisor_usernames.split(",") if u.strip()}


settings = Settings()  # type: ignore[call-arg]

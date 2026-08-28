from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Aiven Postgres connection strings (postgresql+asyncpg://...)
    DIV_AIVEN_ADMIN: str
    DIV_AIVEN_RLS: str | None = None

    GEMINI_API_KEY: str | None = None

    # Polygon.io API key — used to fetch the previous trading day's close for
    # the whole US stock universe in one grouped-daily call (market cap enrich).
    POLYGON_API_KEY: str | None = None

    # App database URL used at runtime (admin: needs DDL via migrations + writes).
    @property
    def database_url(self) -> str:
        return self.DIV_AIVEN_ADMIN


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

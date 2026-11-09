"""Einstellungen kommen ausschliesslich aus Umgebungsvariablen bzw. .env."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="LOIPEN_")

    database_url: str = "postgresql+psycopg://loipen:loipen@db:5432/loipen"
    sources_file: str = "config/sources.yaml"
    timezone: str = "Europe/Berlin"
    user_agent: str = "LoipenBot/0.1 (privat; Kontakt: siehe .env)"
    request_delay_s: float = 5.0

    # Zeitplan: in der Saison stuendlich von saison_start_h bis saison_end_h
    season_months: list[int] = [11, 12, 1, 2, 3, 4]
    season_start_h: int = 6
    season_end_h: int = 22

    # Ein Zustand aelter als stale_days gilt als unbekannt
    stale_days: int = 7

    ntfy_url: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()

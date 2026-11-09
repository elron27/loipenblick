"""Einstellungen aus Umgebungsvariablen bzw. .env (B4). Secrets stehen nie im Repository."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="LOIPEN_", extra="ignore")

    database_url: str = "postgresql+psycopg://loipen:loipen@db:5432/loipen"
    config_dir: str = "config"
    # Ausgabe des Generators; der Container "vorschau" liefert genau diesen Ordner aus (B12)
    site_dir: str = "site"
    backup_dir: str = "backup"
    timezone: str = "Europe/Berlin"
    user_agent: str = "LoipenBot/0.1 (privat; Kontakt: siehe .env)"
    request_delay_s: float = 5.0
    # Ein Zustand aelter als stale_days gilt als unbekannt
    stale_days: int = 7
    ntfy_url: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()

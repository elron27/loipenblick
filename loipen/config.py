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
    # Livegang (docs/livegang.md). Alles leer = nur lokale Vorschau, kein Upload.
    # B8/B21: Ziel des Uploads, z. B. sftp://benutzer@host:22/pfad oder ftps://benutzer@host/pfad
    upload_url: str | None = None
    upload_passwort: str | None = None
    upload_schluessel: str | None = None  # Pfad zum privaten SSH-Schluessel (statt Passwort)
    upload_known_hosts: str = "/app/geheim/known_hosts"  # Fingerabdruck des Servers (Pflicht bei SFTP)
    oeffentliche_url: str | None = None  # https://<domain>, zum Pruefen nach dem Upload
    upload_wartezeiten_s: str = "30,120,600"  # Pausen zwischen den drei Versuchen
    heartbeat_url: str | None = None  # B22, z. B. https://hc-ping.com/<uuid>
    oeffentlich: bool = False  # True erst nach Stefans Freigabe: Suchmaschinen erlaubt
    # B6: Impressum und Datenschutz. Anschrift mit "|" fuer Zeilenumbrueche.
    impressum_name: str | None = None
    impressum_anschrift: str | None = None
    impressum_email: str | None = None
    hoster: str | None = None  # Name und Anschrift des Webhosters fuer die Datenschutzerklaerung
    log_tage: int = 7
    datenschutz_datei: str | None = None  # eigener Text (HTML-Ausschnitt) statt der Vorlage
    # Nur Testbetrieb (tests/stack): alle Abrufe an diesen Server statt ins Netz, siehe fetcher.py
    umleitung: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()

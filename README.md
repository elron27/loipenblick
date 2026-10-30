# Loipen

Private Loipen-Übersicht für das Tegernseer Tal, Bayrischzell, Fischbachau und Sachrang.
Läuft mit Docker Compose auf dem Synology-NAS und zieht ohne Umbau auf einen Server um.

## Aufbau

| Container | Aufgabe |
| --- | --- |
| `db` | PostgreSQL 16, Daten in `./data/postgres` |
| `migrate` | spielt beim Start die Datenbank-Migrationen ein und beendet sich |
| `web` | FastAPI, Port `WEB_PORT` (Standard 8000) |
| `worker` | gleicht `config/sources.yaml` ab und ruft die Quellen nach Zeitplan ab |

Neue Orte kommen in `config/sources.yaml`, nicht in den Code.

## Starten auf dem NAS

```bash
cp .env.example .env      # Passwort und Kontaktadresse eintragen
docker compose up -d --build
```

Danach zeigt `http://<NAS-IP>:8000/health` den Status `ok`.

## Entwickeln

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
pytest
```

Schemaänderungen: Modell in `loipen/models.py` ändern, dann
`alembic revision --autogenerate -m "..."` und die erzeugte Datei prüfen.

## Umzug auf einen Server

Repository klonen, `.env` übernehmen, Datenbank mit `pg_dump` sichern und einspielen,
Reverse Proxy mit HTTPS vor `web` setzen.

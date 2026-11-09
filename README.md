# Loipenblick

Loipen-Übersicht für das Tegernseer Tal, Bayrischzell, Fischbachau, Sachrang und später den Chiemgau.
Version 1 läuft nur lokal auf dem Synology-NAS: Der Worker parst die Quellen, speichert alles mit
Historie in PostgreSQL und erzeugt eine statische Website. Online geht sie später ohne Umbau,
indem der Ordner `site/` auf einen Webspace hochgeladen wird (Entscheidungen E-10, E-11).

Die Anforderungen stehen als ReqSeq-Workspace in [`spec/`](spec/README.md).

## Aufbau

| Container | Aufgabe |
| --- | --- |
| `db` | PostgreSQL 16, Daten in `./data/postgres` |
| `migrate` | spielt beim Start die Datenbank-Migrationen ein und beendet sich |
| `worker` | liest `config/`, ruft die Quellen nach Zeitplan ab (Saison 7, 12, 17 Uhr) und erzeugt `site/` |
| `vorschau` | nginx, zeigt `site/` im Heimnetz unter `http://<NAS-IP>:8080` |

Neue Orte kommen in `config/sources.yaml`, Handdaten (Parkplätze, Gebühren, Haltestellen,
Wetterstation) in `config/gebiete.yaml`. Beide Dateien liest der Worker bei jedem Lauf neu.

## Starten auf dem NAS

```bash
cp .env.example .env      # Passwort und Kontaktadresse eintragen
docker compose up -d --build
```

Danach zeigt `http://<NAS-IP>:8080` die Vorschau. Einen Lauf sofort anstoßen:

```bash
docker compose exec worker python -m loipen.worker lauf
```

## Entwickeln und testen

Die Tests brauchen eine PostgreSQL mit einer Datenbank, deren Name auf `_test` endet
(die Tests leeren sie). Am einfachsten per Docker:

```bash
docker run -d --name loipen-test -p 5432:5432 \
  -e POSTGRES_USER=loipen -e POSTGRES_PASSWORD=loipen -e POSTGRES_DB=loipen_test postgres:16-alpine
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

Die Oberflächen-Tests laufen in Chromium (`playwright install chromium`); ohne Browser werden sie übersprungen.
Jeder Test nennt die Anforderung, die er prüft, z. B. `@pytest.mark.req("D4", ak=1)`.
Die CI verknüpft die Ergebnisse mit ReqSeq (`reqseq evidence enrich-junit`); was noch keinen
Nachweis hat, zeigt `reqseq evidence coverage --workspace spec --filter version-1`.
Das ganze Vorgehen steht im [Testkonzept](https://claude.ai/artifact/T3imWKeVz2SvRSbKS8nPP8).

Schemaänderungen: Modell in `loipen/models.py` ändern, dann
`alembic revision --autogenerate -m "..."` und die erzeugte Datei prüfen.

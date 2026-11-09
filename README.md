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

## Betrieb

**Zeitplan (B3).** Den Zeitplan führt der Worker-Container selbst aus (APScheduler, zur vollen Stunde
werden die fälligen Quellen abgerufen). Es braucht keinen Eintrag im DSM-Taskplaner, nur
`restart: unless-stopped`, das Compose schon setzt.

**Überwachung (B2).** Je Quelle stehen letzter Lauf, Dauer, Anzahl Loipen und Fehler in der Datenbank
(`quellen`) und im Abschnitt `quellen` der `daten.json`. Liefert eine Quelle 0 Loipen oder fällt aus,
steht das im Log und, wenn ntfy eingerichtet ist, als Push (einmal beim Wechsel, nicht bei jedem Lauf).

**Push (N1, N4).** In `.env` `LOIPEN_NTFY_URL=https://ntfy.sh/<geheimes-thema>` setzen (Thema wie ein
Passwort wählen, in der ntfy-App abonnieren). Wer wofür benachrichtigt wird, steht in `config/abos.yaml`:
Abos auf Loipen, Gebiete oder Regionen mit den Ereignissen `oeffnet`, `frisch_gespurt`, `schliesst`.
Ein Abo meldet sich nur bei seinen Zielen und seinen Ereignissen. Der erste Abruf einer Loipe löst nichts aus.

**Sicherung (B14).** Täglich um 3:30 Uhr schreibt der Worker `loipen-JJJJMMTT-HHMM.dump` in `BACKUP_DIR`
und löscht Dumps, die älter als 30 Tage sind. `BACKUP_DIR` muss in einem Ordner liegen, den das
NAS-Backup erfasst (z. B. `/volume1/backup/loipenblick`). Sofort sichern:

```bash
docker compose exec worker python -m loipen.worker sicherung
```

Wiederherstellen (zuerst Worker stoppen, dann in die leere Datenbank zurückspielen):

```bash
docker compose stop worker
docker compose exec -T db dropdb -U loipen --if-exists loipen
docker compose exec -T db createdb -U loipen loipen
docker compose exec -T db pg_restore -U loipen -d loipen < backup/loipen-20261109-0330.dump
docker compose up -d worker
```

Der Ablauf Dump, Restore in eine frische Datenbank und Vergleich der Daten ist als Test
(`test_b14_wiederherstellung_aus_dump`) automatisch geprüft; auf dem NAS bitte einmal von Hand wiederholen.

**Kosten (B9).** `config/kosten.yaml` listet die Posten, die Summe darf 60 € im Jahr nicht übersteigen
(ein Test prüft das). V1 auf dem NAS kostet nichts extra; Webspace und Domain kommen erst mit der Veröffentlichung.

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

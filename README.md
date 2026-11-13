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
Wetterstation) in `config/gebiete.yaml`. Beide Dateien liest der Worker bei jedem Lauf neu (sie stecken im Image; Änderungen kommen mit dem nächsten Image).

## Starten auf dem NAS

Das fertige Image baut GitHub (Workflow `Image`, Registry `ghcr.io/elron27/loipenblick`). Auf dem NAS
brauchst du nur zwei Dateien in einem Ordner: `docker-compose.yml` und `.env` (Vorlage `.env.example`).

```bash
docker compose pull       # holt die neueste Version
docker compose up -d
```

Ein Update ist genauso: `docker compose pull && docker compose up -d`. Die Datenbank bleibt in `./data`.
Einmalig muss das Paket in GitHub unter *Packages, loipenblick, Package settings* auf "public" stehen,
sonst braucht das NAS ein `docker login ghcr.io`. Selbst bauen geht weiter mit `docker compose up -d --build`.
Die Konfiguration (`config/`) steckt im Image; eigene Änderungen siehe Kommentar in der `docker-compose.yml`.

Danach zeigt `http://<NAS-IP>:8080` die Vorschau. Einen Lauf sofort anstoßen:

```bash
docker compose exec worker python -m loipen.worker lauf
```

## Betrieb

**Standort (U35).** Die Seite fragt beim ersten Besuch einmal nach dem Standort des Geräts. Browser
geben ihn nur auf sicheren Seiten frei (https oder localhost); unter `http://<NAS-IP>:8080` bleibt
deshalb nur die Ortssuche (bekannte Orte sofort, andere Orte und Postleitzahlen online über
photon.komoot.io). Über https, etwa mit `tailscale serve` oder später auf dem Webspace, klappt beides.

**Zeitplan (B3).** Den Zeitplan führt der Worker-Container selbst aus (APScheduler, zur vollen Stunde
werden die fälligen Quellen abgerufen). Es braucht keinen Eintrag im DSM-Taskplaner, nur
`restart: unless-stopped`, das Compose schon setzt.

**Überwachung (B2).** Je Quelle stehen letzter Lauf, Dauer, Anzahl Loipen und Fehler in der Datenbank
(`quellen`) und im Abschnitt `quellen` der `daten.json`. Jeder Abruf steht zusätzlich in der Tabelle
`abrufprotokoll`.

**Quellen-Wächter (B26).** Bricht eine Quelle ab, liefert sie 0 Loipen oder weniger als die Hälfte ihres
üblichen Werts, meist weil sich die Webseite geändert hat, meldet der Worker das per Push (ntfy) und per
Mail an `LOIPEN_WAECHTER_MAIL` (leer = Impressum-Adresse, Versand über den SMTP-Zugang des Mail-Abos).
Ein einzelner Aussetzer bleibt still, gemeldet wird erst nach zwei auffälligen Abrufen hintereinander.
Danach höchstens eine Erinnerung am Tag und eine Entwarnung, sobald die Quelle wieder normal liefert.
Liefert eine Quelle eine Woche lang stabil weniger, gilt das als neuer Normalwert. Schwellen stehen im
Block `waechter` in `config/sources.yaml`, je Quelle überschreibbar, z. B. `waechter: {aus: true}`.
Die Mail sagt auch, was zu tun ist: Schnappschuss holen, Fixture-Test, dann Adapter reparieren.

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
(`test_b14_wiederherstellung_aus_dump`) und im Teststack mit dem echten Container automatisch geprüft;
ob der Backup-Ordner im NAS-Backup liegt, bleibt eine Handprüfung.

**Kosten (B9).** `config/kosten.yaml` listet die Posten, die Summe darf 60 € im Jahr nicht übersteigen
(ein Test prüft das). V1 auf dem NAS kostet nichts extra; Webspace und Domain kommen erst mit der Veröffentlichung.

**Karten.** Die Karten nutzen Leaflet (liegt im Ordner `vendor/` der Seite, kein CDN) und die Kacheln von
OpenStreetMap. Der Browser lädt die Kacheln direkt von `tile.openstreetmap.org`; die Quellenangabe steht in
der Karte. Für eine öffentliche Seite mit vielen Besuchern sollte ein eigener Kachel-Anbieter gewählt werden
(Nutzungsregeln von OpenStreetMap).

## Online stellen (Livegang)

Hintergrund und Abwägung: [docs/livegang.md](docs/livegang.md), was du selbst tun musst:
[docs/livegang-checkliste-stefan.md](docs/livegang-checkliste-stefan.md).

Sobald `LOIPEN_UPLOAD_URL` in der `.env` steht, lädt der Worker nach jedem Lauf die Seite hoch (B8):
zuerst die Daten-Dateien mit Inhalts-Hash, zuletzt `daten.json` und `index.html` (B21). Bricht der
Upload ab, bleibt online der alte Stand vollständig. Nach drei Fehlversuchen kommt ein Push über ntfy,
einmal beim Wechsel. Ohne vollständiges Impressum (`LOIPEN_IMPRESSUM_NAME`, `_ANSCHRIFT`, `_EMAIL`)
lädt das NAS nichts hoch (B6).

1. Ordner `geheim/` neben die `docker-compose.yml` legen. Für SFTP den Fingerabdruck des Servers
   holen und mit dem Kundenmenü des Hosters vergleichen:
   `ssh-keyscan -p 22 <host> > geheim/known_hosts`
2. In der `.env` die Werte unter „Livegang“ aus `.env.example` eintragen. Zuerst auf eine Testadresse
   hochladen, `LOIPEN_OEFFENTLICH=false` lässt Suchmaschinen draußen.
3. `docker compose up -d`, dann `docker compose exec worker python -m loipen.worker lauf` und die
   Testadresse auf Handy und PC prüfen.
4. Erst nach der Freigabe: Ziel auf die Hauptadresse umstellen und `LOIPEN_OEFFENTLICH=true`.

Die Seite bringt `.htaccess` (HTTPS-Umleitung, Sicherheits- und Cache-Header), `404.html`,
`robots.txt`, Impressum, Datenschutz (Vorlage, eigener Text über `LOIPEN_DATENSCHUTZ_DATEI`) und
die Seite „Hinweise und Betreiber“ mit. Die Karte lädt die Kacheln von OpenStreetMap erst nach
einem Klick (B23). Eine Quelle schaltest du mit `enabled: false` in `config/sources.yaml` ab, ihre
Loipen verschwinden mit dem nächsten Lauf (B16).

### E-Mail-Abo und Fehlermeldungen (E-18)

Besucher können sich bei jeder Loipe und jedem Gebiet per E-Mail benachrichtigen lassen und bei jeder
Loipe falsche Angaben melden. Dafür liegen im Ordner `abo/` fünf kleine PHP-Skripte; der Rest der
Seite bleibt statisch. Der Webspace verschickt die Bestätigungsmail (Double-Opt-In) sofort und hält
bestätigte Abos, Abmeldungen und Meldungen in einer Warteschlange. Das NAS holt sie bei jedem Lauf
über `abo/export.php` ab, speichert die Abonnenten in der Datenbank (im täglichen Dump enthalten) und
verschickt die Alarme per SMTP, höchstens eine Mail je Abonnent und Lauf. Meldungen kommen sofort per
Mail an `LOIPEN_ABO_MELDUNGEN_AN` und beim nächsten Lauf als Push; sie ändern nie einen Status.

1. Beim Hoster ein Postfach für den Absender anlegen, z. B. `abo@<domain>`.
2. In der `.env` die Werte unter „E-Mail-Abo“ aus `.env.example` eintragen, den Schlüssel einmal mit
   `openssl rand -hex 32` erzeugen. Ohne `LOIPEN_OEFFENTLICHE_URL`, Schlüssel und Absender gibt es
   weder Formulare noch den Ordner `abo/`.
3. Nach dem nächsten Lauf auf der Testadresse ein Abo anlegen, die Mail bestätigen und mit
   `docker compose exec worker python -m loipen.worker lauf` den Abgleich prüfen (Log: „Abo: 1 neu“).

Voraussetzung ist ein Webspace mit PHP und `mail()`, bei netcup Webhosting gegeben. Mit Cloudflare
Pages ginge das Abo nur mit einem eigenen Worker.

### Als App aufs Handy (U40, U41)

Die Seite ist eine installierbare Web-App. Auf Android zeigt die Startseite einen Knopf „Installieren“,
sobald Chrome die Installation anbietet. Auf dem iPhone steht dort die Anleitung: in Safari auf
„Teilen“, dann „Zum Home-Bildschirm“. Die installierte App startet ohne Browserleiste, hat Kurzbefehle
für Heute, Karte und Loipen und zeigt ohne Netz den zuletzt geladenen Stand mit Datum. Installieren
geht nur über HTTPS, also erst nach dem Livegang; im Heimnetz über `http://` zeigt der Browser den Knopf
nicht. Die App lädt sich nur neu, wenn sich die App selbst ändert, nicht bei jedem neuen Datenstand.

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

**Ohne NAS testen.** `python scripts/teststack.py` startet den ganzen Compose-Stack mit einer Attrappe
statt der echten Quellen und einem lokalen ntfy und prüft Lauf, Seite, Push, Sicherung/Wiederherstellung
und Neustart (läuft auch in der CI). Der Workflow `Live-Pruefung` ruft die echten Quellen und Wetterdienste ab.
Details und was weiterhin nur am NAS geht: [docs/testumgebung.md](docs/testumgebung.md).

Schemaänderungen: Modell in `loipen/models.py` ändern, dann
`alembic revision --autogenerate -m "..."` und die erzeugte Datei prüfen.

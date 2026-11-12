# Testumgebung ohne NAS

Fast alles, was bisher erst auf dem NAS sichtbar war, prüfen jetzt drei Ebenen automatisch.
Das NAS bleibt für wenige Dinge nötig (Liste unten).

| Ebene | Wo | Wann | Was |
| --- | --- | --- | --- |
| `pytest` | CI-Job `pytest`, lokal | jeder Push/PR | Einheiten, Parser mit Fixtures, Datenbank, Oberfläche im Browser |
| Teststack | CI-Job `stack`, lokal mit Docker | jeder Push/PR | der echte Compose-Stack wie auf dem NAS, Quellen aus einer Attrappe |
| Live-Prüfung | Workflow `Live-Pruefung` | täglich Nov bis Apr, von Hand | echte Quellen und echte Wetterdienste |

## Teststack

`docker-compose.test.yml` ergänzt die NAS-Datei `docker-compose.yml`, ohne sie zu ändern. Gestartet werden
dieselben Container (`db`, `migrate`, `worker`, `vorschau`) aus demselben Image, dazu:

- `attrappe` (`tests/stack/attrappe.py`): beantwortet alle Abrufe aus `tests/fixtures/`. Der Worker läuft mit
  `LOIPEN_UMLEITUNG=http://attrappe:8080`, dann wird aus `https://www.tegernsee.com/langlaufen`
  `http://attrappe:8080/www.tegernsee.com/langlaufen`. Wetter (DWD-ZIP, Bright Sky) erzeugt die Attrappe
  passend zum heutigen Tag im dokumentierten Format. Szenarien: alle Loipen „geöffnet“, Ausfall einer Quelle.
- `ntfy`: lokaler ntfy-Server statt ntfy.sh; der Test liest die Push-Nachrichten über die ntfy-API.
- Datenbank im Docker-Volume, Seite und Dumps unter `.teststack/`, Abos aus `tests/stack/abos.yaml`.

Start (Linux, macOS, Windows; braucht Docker mit Compose 2.24 oder neuer und `pip install -r requirements-dev.txt`):

```bash
python scripts/teststack.py             # bauen, starten, prüfen, abbauen
python scripts/teststack.py --behalten  # danach weiterlaufen lassen: http://localhost:18080
python scripts/teststack.py --abbauen
```

`tests/stack/test_stack.py` prüft der Reihe nach:

1. Migrationen laufen auf leerer Datenbank (`migrate` endet mit 0).
2. Der Worker holt beim Start alle 5 Quellen (115 Loipen) und startet den Zeitplan (B3).
3. nginx liefert `daten.json`, alle Regionsdateien und die App aus.
4. Schneehöhe für jedes Gebiet mit Wetterstation, Vorhersage für jedes Gebiet mit Position (D11).
5. Jeder Abruf trägt den User-Agent, robots.txt wird gelesen (P7).
6. Push über ntfy: Loipe öffnet (nur das passende Abo meldet sich), Quelle fällt aus, Quelle läuft wieder, Loipe schließt (N1, N4, B2).
7. `python -m loipen.worker sicherung` im Container, Dump in eine frische Datenbank zurückspielen, alle Tabellen gleich (B14).
8. Container neu erzeugen wie bei `docker compose pull && up -d`: Daten bleiben, keine doppelten Loipen (B4).
9. Bildschirmfotos der Vorschau (Desktop und Handy) ohne JavaScript-Fehler.

In der CI liegen Fotos, Logs, JUnit und die erzeugte Seite im Artefakt `teststack`.

## Live-Prüfung

`.github/workflows/live.yml` läuft auf einem GitHub-Runner, der anders als die Cloud-Umgebung ins Netz darf.
`scripts/live_pruefung.py` macht einen Lauf wie der Worker (mit robots.txt und 5 s Abstand) gegen eine eigene
Datenbank und schreibt einen Bericht in die Job-Zusammenfassung: Loipen je Quelle, Fehler, unbekannte Begriffe,
geparste DWD- und Bright-Sky-Werte. Der Job wird rot, wenn eine Quelle ausfällt, 0 Loipen liefert oder das
Wetter nicht geparst werden kann. So fällt ein geändertes Seitenlayout auf, bevor das NAS es merkt.

Artefakte: `live-aufnahme` (alle Antworten, als neuer Fixture-Schnappschuss `fixtures-JJJJ-MM-TT/` nutzbar;
DWD-ZIPs unter `wetter/dwd/`, die nach `tests/fixtures/wetter/dwd/` kopiert die Attrappe statt der erzeugten
Werte ausliefert) und `live-seite` (die echte Seite zum Anschauen ohne NAS).

Kontaktangabe im User-Agent: in GitHub unter *Settings, Secrets and variables, Actions, Variables* die Variable
`LOIPEN_USER_AGENT` anlegen, z. B. `LoipenBot/0.1 (privat; deine-mail@example.com)`. Ohne sie steht der Repo-Link drin.

## Was weiterhin nur am NAS geht

- **Backup-Ordner im Hyper Backup** (B14:2): ob `BACKUP_DIR` wirklich in der NAS-Sicherung liegt, sieht nur DSM.
- **Echte `.env`**: Passwort, ntfy-Thema und Pfade auf dem NAS; der Teststack nutzt eigene Werte.
- **Push aufs Handy**: der Teststack prüft, dass ntfy die Nachricht annimmt; ob sie in der App ankommt, zeigt nur ein echtes Abo.
- **Synology-Eigenheiten**: Container-Manager-Version, Volume-Rechte unter `/volume1`, Neustart nach DSM-Update, Uhrzeit/Zeitzone des NAS.
- **Dauerbetrieb über Tage**: Zeitplan um 7, 12, 17 Uhr und Dump um 3:30 über echte Uhrzeit; der Teststack stößt Läufe von Hand an.
- **Erreichbarkeit im Heimnetz** (`http://<NAS-IP>:8080`).
- **Echte Quellen vom NAS aus**: ob eine Quelle die IP des NAS anders behandelt als die eines GitHub-Runners.
